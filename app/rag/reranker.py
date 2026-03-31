from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class RerankResult:
    def __init__(
        self,
        chunk_id: UUID,
        rerank_score: float,
        original_score: float | None = None,
    ):
        self.chunk_id = chunk_id
        self.rerank_score = rerank_score
        self.original_score = original_score


class RerankerInterface:
    async def rerank(
        self,
        chunks: list[dict[str, Any]],
        query: str,
        top_n: int,
    ) -> list[RerankResult]:
        raise NotImplementedError


class StubReranker(RerankerInterface):
    async def rerank(
        self,
        chunks: list[dict[str, Any]],
        query: str,
        top_n: int,
    ) -> list[RerankResult]:
        logger.warning("using_stub_reranker", chunk_count=len(chunks))

        results = []
        for i, chunk in enumerate(chunks):
            chunk_id = UUID(chunk["chunk_id"]) if isinstance(chunk["chunk_id"], str) else chunk["chunk_id"]
            results.append(
                RerankResult(
                    chunk_id=chunk_id,
                    rerank_score=1.0 - (i * 0.1),
                    original_score=chunk.get("score"),
                )
            )

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        return results[:top_n]


class CrossEncoderReranker(RerankerInterface):
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"):
        self.model_name = model_name
        self._model = None

    async def rerank(
        self,
        chunks: list[dict[str, Any]],
        query: str,
        top_n: int,
    ) -> list[RerankResult]:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            logger.warning("sentence_transformers_not_available_using_stub")
            stub = StubReranker()
            return await stub.rerank(chunks, query, top_n)

        if self._model is None:
            self._model = CrossEncoder(self.model_name)

        pairs = [(query, chunk["chunk_text"]) for chunk in chunks]
        scores = self._model.predict(pairs)

        results = []
        for chunk, score in zip(chunks, scores):
            chunk_id = UUID(chunk["chunk_id"]) if isinstance(chunk["chunk_id"], str) else chunk["chunk_id"]
            results.append(
                RerankResult(
                    chunk_id=chunk_id,
                    rerank_score=float(score),
                    original_score=chunk.get("score"),
                )
            )

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        return results[:top_n]


def get_reranker() -> RerankerInterface:
    return StubReranker()
