from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class EmbeddingResult:
    def __init__(self, embedding: list[float], model: str):
        self.embedding = embedding
        self.model = model


class EmbedderInterface:
    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        raise NotImplementedError


class StubEmbedder(EmbedderInterface):
    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        logger.warning("using_stub_embedder", count=len(texts))

        dimension = settings.embedding_dimension
        return [
            EmbeddingResult(
                embedding=[0.0] * dimension,
                model="stub",
            )
            for _ in texts
        ]


class OpenAIEmbedder(EmbedderInterface):
    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.base_url = base_url or settings.openai_base_url

    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "input": texts,
                "model": self.model,
            }

            response = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error("embedding_failed", status=response.status_code)
                raise RuntimeError(f"Embedding API error: {response.status_code}")

            data = response.json()
            return [
                EmbeddingResult(
                    embedding=item["embedding"],
                    model=self.model,
                )
                for item in data["data"]
            ]


def get_embedder() -> EmbedderInterface:
    embedder_type = settings.embedding_model

    if embedder_type == "text-embedding-ada-002":
        return OpenAIEmbedder()
    else:
        return StubEmbedder()
