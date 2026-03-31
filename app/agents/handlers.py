from typing import Any
from uuid import UUID

from app.agents.types import AgentType, SessionContext
from app.rag.pipeline import RetrievalBundle
from app.schemas.query import QueryResponse, Citation, StateUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseAgent:
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type

    async def handle(
        self,
        user_input: str,
        context: SessionContext,
        evidence_bundle: RetrievalBundle | None,
    ) -> QueryResponse:
        raise NotImplementedError

    def _build_response(
        self,
        answer: str,
        used_agent: str,
        confidence: float,
        citations: list[Citation],
        state_updates: list[StateUpdate] | None = None,
        needs_clarification: bool = False,
        clarification_question: str | None = None,
    ) -> QueryResponse:
        return QueryResponse(
            answer=answer,
            used_agent=used_agent,
            confidence=confidence,
            citations=citations,
            state_updates=state_updates or [],
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
        )

    def _extract_snippet(self, text: str, max_length: int = 200) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."


class RulesAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.RULES)

    async def handle(
        self,
        user_input: str,
        context: SessionContext,
        evidence_bundle: RetrievalBundle | None,
    ) -> QueryResponse:
        if not evidence_bundle or not evidence_bundle.chunks:
            return self._build_response(
                answer="I couldn't find any relevant rules information to answer your question. Please try rephrasing or providing more context.",
                used_agent=self.agent_type.value,
                confidence=0.0,
                citations=[],
                needs_clarification=True,
                clarification_question="Could you clarify what specific rules or game mechanics you're asking about?",
            )

        top_chunks = evidence_bundle.get_top_chunks(5)

        citations = []
        for chunk in top_chunks:
            citations.append(
                Citation(
                    chunk_id=UUID(chunk["chunk_id"]),
                    source_doc_id=UUID(chunk["source_doc_id"]),
                    title=chunk.get("source_title", "Unknown Source"),
                    uri=chunk.get("source_uri"),
                    snippet=self._extract_snippet(chunk["chunk_text"]),
                )
            )

        answer = self._format_rules_answer(user_input, top_chunks)

        confidence = self._calculate_confidence(evidence_bundle)

        return self._build_response(
            answer=answer,
            used_agent=self.agent_type.value,
            confidence=confidence,
            citations=citations,
        )

    def _format_rules_answer(self, question: str, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "No relevant rules found."

        relevant_texts = [c["chunk_text"] for c in chunks[:3]]

        answer = "Based on the rules:\n\n"
        for i, text in enumerate(relevant_texts, 1):
            snippet = text[:500] + "..." if len(text) > 500 else text
            answer += f"{i}. {snippet}\n\n"

        return answer

    def _calculate_confidence(self, evidence_bundle: RetrievalBundle) -> float:
        if not evidence_bundle.chunks:
            return 0.0

        scores = list(evidence_bundle.rerank_scores.values())
        if not scores:
            return 0.5

        avg_score = sum(scores) / len(scores)
        return min(max(avg_score, 0.0), 1.0)


class NarrativeAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.NARRATIVE)

    async def handle(
        self,
        user_input: str,
        context: SessionContext,
        evidence_bundle: RetrievalBundle | None,
    ) -> QueryResponse:
        if not evidence_bundle or not evidence_bundle.chunks:
            return self._build_response(
                answer="I don't have enough narrative context to describe that scene. Consider enabling relevant lore modules for your campaign.",
                used_agent=self.agent_type.value,
                confidence=0.0,
                citations=[],
            )

        top_chunks = evidence_bundle.get_top_chunks(3)

        citations = []
        for chunk in top_chunks:
            citations.append(
                Citation(
                    chunk_id=UUID(chunk["chunk_id"]),
                    source_doc_id=UUID(chunk["source_doc_id"]),
                    title=chunk.get("source_title", "Unknown Source"),
                    uri=chunk.get("source_uri"),
                    snippet=self._extract_snippet(chunk["chunk_text"]),
                )
            )

        narrative = self._format_narrative(top_chunks)

        return self._build_response(
            answer=narrative,
            used_agent=self.agent_type.value,
            confidence=0.6,
            citations=citations,
        )

    def _format_narrative(self, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "The scene unfolds according to the GM's direction."

        descriptions = [c["chunk_text"][:300] for c in chunks]
        return " ".join(descriptions) + "..."


class StateAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.STATE)

    async def handle(
        self,
        user_input: str,
        context: SessionContext,
        evidence_bundle: RetrievalBundle | None,
    ) -> QueryResponse:
        user_lower = user_input.lower()

        state_updates = []

        if "mark" in user_lower and ("quest" in user_lower or "complete" in user_lower):
            path = self._extract_path_from_text(user_lower)
            if path:
                state_updates.append(
                    StateUpdate(
                        op="set",
                        path=path,
                        value="completed",
                        reason="Quest marked complete by GM",
                    )
                )

        answer = "State update processed."
        if state_updates:
            answer += f" Proposed changes: {[u.path for u in state_updates]}"

        return self._build_response(
            answer=answer,
            used_agent=self.agent_type.value,
            confidence=0.8,
            citations=[],
            state_updates=state_updates,
        )

    def _extract_path_from_text(self, text: str) -> str | None:
        words = text.lower().split()
        for i, word in enumerate(words):
            if word in ["quest", "objective"] and i + 1 < len(words):
                return f"quests.{words[i + 1]}.status"
        return None


class EncounterAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.ENCOUNTER)

    async def handle(
        self,
        user_input: str,
        context: SessionContext,
        evidence_bundle: RetrievalBundle | None,
    ) -> QueryResponse:
        if not evidence_bundle or not evidence_bundle.chunks:
            return self._build_response(
                answer="No encounter-related information is currently available. Consider enabling relevant monster or combat modules.",
                used_agent=self.agent_type.value,
                confidence=0.0,
                citations=[],
            )

        top_chunks = evidence_bundle.get_top_chunks(3)

        citations = []
        for chunk in top_chunks:
            citations.append(
                Citation(
                    chunk_id=UUID(chunk["chunk_id"]),
                    source_doc_id=UUID(chunk["source_doc_id"]),
                    title=chunk.get("source_title", "Unknown Source"),
                    uri=chunk.get("source_uri"),
                    snippet=self._extract_snippet(chunk["chunk_text"]),
                )
            )

        encounter_info = self._format_encounter_info(top_chunks)

        return self._build_response(
            answer=encounter_info,
            used_agent=self.agent_type.value,
            confidence=0.7,
            citations=citations,
        )

    def _format_encounter_info(self, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "Encounter guidance not available."

        return " ".join([c["chunk_text"][:300] for c in chunks]) + "..."
