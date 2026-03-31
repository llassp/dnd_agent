from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "DnD RAG Campaign Agent"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dnd_rag"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    redis_url: str = "redis://localhost:6379/0"

    embedding_model: str = "stub"
    embedding_dimension: int = 1536
    embedding_batch_size: int = 100

    llm_provider: str = "stub"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1200
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""

    chunk_size: int = 512
    chunk_overlap: int = 50

    vector_search_top_k: int = 20
    lexical_search_top_k: int = 20
    rerank_top_n: int = 5

    log_level: str = "INFO"
    trace_enabled: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
