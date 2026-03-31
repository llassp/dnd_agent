import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Campaign, Chunk, ChatTurn
from app.schemas.query import QueryRequest, QueryResponse
from app.agents import Router, AgentType, SessionContext
from app.ingestion import get_embedder
from app.rag import RetrievalFilters, RetrievalService, get_reranker, QueryRewriter
from app.llm import LLMProviderFactory, CitationContext, EvidenceBundle
from app.core.logging import get_logger
from app.core.config import get_settings

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    campaign_stmt = select(Campaign).where(Campaign.id == request.campaign_id)
    campaign_result = await db.execute(campaign_stmt)
    campaign = campaign_result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    agent_router = Router()
    agent_type = agent_router.route(request.user_input, SessionContext(
        campaign_id=str(request.campaign_id),
        session_id=str(request.session_id),
        user_input=request.user_input,
        mode=AgentType(request.mode) if request.mode != "auto" else AgentType.AUTO,
    ))

    retrieval_service = RetrievalService(db)
    filters = RetrievalFilters(campaign_id=request.campaign_id)

    embedder = get_embedder()

    rewrite_result = QueryRewriter().rewrite(request.user_input)

    query_embedding = (await embedder.embed([rewrite_result.rewritten_query]))[0].embedding

    retrieved_chunks = await retrieval_service.retrieve(
        filters=filters,
        query_embedding=query_embedding,
        query_text=request.user_input,
    )

    reranker = get_reranker()
    chunks_for_rerank = [c.to_dict() for c in retrieved_chunks]
    rerank_results = await reranker.rerank(
        chunks=chunks_for_rerank,
        query=rewrite_result.rewritten_query,
        top_n=settings.rerank_top_n,
    )

    rerank_scores = {str(r.chunk_id): r.rerank_score for r in rerank_results}

    citation_contexts = [
        CitationContext(
            chunk_id=c["chunk_id"],
            source_title=c.get("source_title", "Unknown"),
            snippet=c["chunk_text"],
            score=rerank_scores.get(c["chunk_id"]),
        )
        for c in chunks_for_rerank
    ]

    evidence_bundle = EvidenceBundle(
        query=request.user_input,
        citations=citation_contexts,
        agent_type=agent_type.value,
    )

    llm_provider = LLMProviderFactory.from_env()

    try:
        llm_result = await llm_provider.generate_with_citations(
            evidence_bundle=evidence_bundle,
            task_prompt=request.user_input,
            mode=agent_type.value,
        )

        answer = llm_result.content

        if evidence_bundle.citations:
            answer = _ensure_citation_format(answer, evidence_bundle)

    except Exception as e:
        logger.error("llm_generation_failed_using_fallback", error=str(e))
        answer = _generate_fallback_answer(request.user_input, agent_type.value, chunks_for_rerank)

    confidence = _calculate_confidence(rerank_scores, chunks_for_rerank)

    citations = [
        {
            "chunk_id": c["chunk_id"],
            "source_doc_id": c["source_doc_id"],
            "title": c.get("source_title", "Unknown"),
            "uri": c.get("source_uri"),
            "snippet": c["chunk_text"][:200],
        }
        for c in chunks_for_rerank[:5]
    ]

    state_updates = _extract_state_updates(request.user_input, agent_type.value)

    trace_json = {
        "retrieval": {
            "filters": filters.to_dict(),
            "chunks_retrieved": len(retrieved_chunks),
            "chunks_reranked": len(rerank_results),
        },
        "agent": agent_type.value,
        "confidence": confidence,
        "llm_model": llm_result.model if "llm_result" in dir() else "none",
    }

    chat_turn = ChatTurn(
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        role="user",
        content=request.user_input,
        trace_json=trace_json,
    )
    db.add(chat_turn)

    response_turn = ChatTurn(
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        role="assistant",
        content=answer,
        trace_json={
            **trace_json,
            "citations": citations,
        },
    )
    db.add(response_turn)

    await db.commit()

    logger.info(
        "query_processed",
        campaign_id=str(request.campaign_id),
        session_id=str(request.session_id),
        agent=agent_type.value,
        citations_count=len(citations),
    )

    return QueryResponse(
        answer=answer,
        used_agent=agent_type.value,
        confidence=confidence,
        citations=citations,
        state_updates=state_updates,
        needs_clarification=False,
        clarification_question=None,
    )


def _ensure_citation_format(answer: str, evidence: EvidenceBundle) -> str:
    if not evidence.citations:
        return answer

    if "**Conclusion**:" not in answer and "**Evidence**:" not in answer:
        citation_lines = []
        for i, c in enumerate(evidence.citations[:3], 1):
            citation_lines.append(f"{i}. {c.source_title}: \"{c.snippet[:100]}...\"")
        citations_text = "\n".join(citation_lines)

        return f"""**Conclusion**: {answer}

**Evidence**:
{citations_text}

**DM Adjudication Note**: Based on available evidence. Use your judgment as DM."""

    return answer


def _generate_fallback_answer(question: str, mode: str, chunks: list[dict]) -> str:
    if not chunks:
        return f"I don't have enough information to answer your question about '{question}'. Please try rephrasing or enable relevant modules."

    relevant_texts = [c["chunk_text"][:300] for c in chunks[:3]]

    if mode == "rules":
        return f"""**Conclusion**: Based on the available rules:

{"".join(f"- {text}\n" for text in relevant_texts)}

**DM Adjudication Note**: Use your judgment as DM."""
    elif mode == "narrative":
        return f"""{" ".join(relevant_texts)}..."""
    elif mode == "encounter":
        return f"""**Encounter Guidance**:
{"".join(f"- {text}\n" for text in relevant_texts)}"""
    else:
        return f"""**Answer**:
{"".join(f"- {text}\n" for text in relevant_texts)}"""


def _calculate_confidence(rerank_scores: dict[str, float], chunks: list[dict]) -> float:
    if not rerank_scores or not chunks:
        return 0.0

    scores = [rerank_scores.get(c["chunk_id"], 0.0) for c in chunks[:5]]
    if not scores:
        return 0.0

    avg_score = sum(scores) / len(scores)
    return min(max(avg_score, 0.0), 1.0)


def _extract_state_updates(question: str, mode: str) -> list[dict]:
    updates = []

    if mode != "state":
        return updates

    question_lower = question.lower()

    if "mark" in question_lower and ("quest" in question_lower or "complete" in question_lower):
        path_match = re.search(r"(?:mark|set)\s+(?:quest\s+)?(\w+)\s+(?:as\s+)?complete", question_lower)
        if path_match:
            updates.append({
                "op": "set",
                "path": f"quests.{path_match.group(1)}.status",
                "value": "completed",
                "reason": "Marked complete by DM",
            })

    return updates
