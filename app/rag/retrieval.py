import uuid
from typing import Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, SourceDoc, CampaignModule, Module
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RetrievalFilters:
    def __init__(
        self,
        campaign_id: uuid.UUID,
        module_ids: list[uuid.UUID] | None = None,
        source_types: list[str] | None = None,
        canon_levels: list[str] | None = None,
    ):
        self.campaign_id = campaign_id
        self.module_ids = module_ids
        self.source_types = source_types
        self.canon_levels = canon_levels

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": str(self.campaign_id),
            "module_ids": [str(m) for m in (self.module_ids or [])],
            "source_types": self.source_types or [],
            "canon_levels": self.canon_levels or [],
        }


class RetrievedChunk:
    def __init__(
        self,
        chunk_id: uuid.UUID,
        source_doc_id: uuid.UUID,
        chunk_text: str,
        score: float,
        metadata: dict[str, Any],
        source_title: str | None = None,
        source_uri: str | None = None,
    ):
        self.chunk_id = chunk_id
        self.source_doc_id = source_doc_id
        self.chunk_text = chunk_text
        self.score = score
        self.metadata = metadata
        self.source_title = source_title
        self.source_uri = source_uri

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": str(self.chunk_id),
            "source_doc_id": str(self.source_doc_id),
            "chunk_text": self.chunk_text,
            "score": self.score,
            "metadata": self.metadata,
            "source_title": self.source_title,
            "source_uri": self.source_uri,
        }


class RetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.is_sqlite = str(settings.database_url).startswith("sqlite")

    async def get_enabled_module_ids(self, campaign_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(CampaignModule.module_id).where(
            CampaignModule.campaign_id == campaign_id
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def retrieve(
        self,
        filters: RetrievalFilters,
        query_embedding: list[float],
        query_text: str,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.vector_search_top_k

        enabled_modules = await self.get_enabled_module_ids(filters.campaign_id)

        if self.is_sqlite:
            lexical_results = await self._simple_text_search(
                campaign_id=filters.campaign_id,
                enabled_modules=enabled_modules,
                query_text=query_text,
                top_k=top_k,
            )
            return lexical_results[:top_k]
        else:
            vector_results = await self._vector_search(
                campaign_id=filters.campaign_id,
                enabled_modules=enabled_modules,
                query_embedding=query_embedding,
                top_k=top_k,
            )

            lexical_results = await self._lexical_search(
                campaign_id=filters.campaign_id,
                enabled_modules=enabled_modules,
                query_text=query_text,
                top_k=top_k,
            )

            merged = self._merge_results(vector_results, lexical_results)
            return merged[:top_k]

    async def _simple_text_search(
        self,
        campaign_id: uuid.UUID,
        enabled_modules: list[uuid.UUID],
        query_text: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not enabled_modules:
            return []

        search_terms = query_text.lower().split()
        if not search_terms:
            return []

        stmt = (
            select(Chunk, SourceDoc)
            .join(SourceDoc, Chunk.source_doc_id == SourceDoc.id)
            .where(Chunk.metadata_json["module_id"].astext.in_([str(m) for m in enabled_modules]))
            .limit(top_k * 2)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        scored_chunks = []
        for chunk, source_doc in rows:
            text_lower = chunk.chunk_text.lower()
            match_count = sum(1 for term in search_terms if term in text_lower)
            if match_count > 0:
                score = match_count / len(search_terms)
                scored_chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk.id,
                        source_doc_id=chunk.source_doc_id,
                        chunk_text=chunk.chunk_text,
                        score=score,
                        metadata=chunk.metadata_json,
                        source_title=source_doc.title,
                        source_uri=source_doc.uri,
                    )
                )

        scored_chunks.sort(key=lambda x: x.score, reverse=True)
        return scored_chunks[:top_k]

    async def _vector_search(
        self,
        campaign_id: uuid.UUID,
        enabled_modules: list[uuid.UUID],
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not enabled_modules:
            return []

        campaign_filter = or_(
            Chunk.metadata_json["campaign_id"].astext == str(campaign_id),
            Chunk.metadata_json["campaign_id"].is_(None),
        )

        module_filter = Chunk.metadata_json["module_id"].astext.in_(
            [str(m) for m in enabled_modules]
        )

        stmt = (
            select(Chunk, SourceDoc)
            .join(SourceDoc, Chunk.source_doc_id == SourceDoc.id)
            .where(and_(campaign_filter, module_filter))
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        chunks = []
        for chunk, source_doc in rows:
            score = 1.0 - self._cosine_similarity(query_embedding, chunk.embedding or [])
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    source_doc_id=chunk.source_doc_id,
                    chunk_text=chunk.chunk_text,
                    score=score,
                    metadata=chunk.metadata_json,
                    source_title=source_doc.title,
                    source_uri=source_doc.uri,
                )
            )

        return chunks

    async def _lexical_search(
        self,
        campaign_id: uuid.UUID,
        enabled_modules: list[uuid.UUID],
        query_text: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not enabled_modules:
            return []

        campaign_filter = or_(
            Chunk.metadata_json["campaign_id"].astext == str(campaign_id),
            Chunk.metadata_json["campaign_id"].is_(None),
        )

        module_filter = Chunk.metadata_json["module_id"].astext.in_(
            [str(m) for m in enabled_modules]
        )

        fts_query = self._build_fts_query(query_text)

        stmt = (
            select(Chunk, SourceDoc)
            .join(SourceDoc, Chunk.source_doc_id == SourceDoc.id)
            .where(and_(campaign_filter, module_filter))
            .where(Chunk.chunk_text.match(fts_query, postgresql_regconfig="english"))
            .order_by(Chunk.chunk_text.match(fts_query, postgresql_regconfig="english"))
            .limit(top_k)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        chunks = []
        for chunk, source_doc in rows:
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    source_doc_id=chunk.source_doc_id,
                    chunk_text=chunk.chunk_text,
                    score=1.0,
                    metadata=chunk.metadata_json,
                    source_title=source_doc.title,
                    source_uri=source_doc.uri,
                )
            )

        return chunks

    @staticmethod
    def _build_fts_query(query: str) -> str:
        words = query.split()
        return " & ".join(words)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @staticmethod
    def _merge_results(
        vector_results: list[RetrievedChunk],
        lexical_results: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        seen: dict[str, RetrievedChunk] = {}

        for chunk in vector_results:
            key = str(chunk.chunk_id)
            if key not in seen:
                seen[key] = chunk

        for chunk in lexical_results:
            key = str(chunk.chunk_id)
            if key in seen:
                seen[key].score = (seen[key].score + chunk.score) / 2.0
            else:
                seen[key] = chunk

        merged = list(seen.values())
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged
