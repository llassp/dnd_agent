from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.tracing import setup_tracing
from app.db import init_db, close_db, engine

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("application_starting")

    try:
        setup_tracing(app=app, engine=engine)
    except Exception as e:
        logger.warning("tracing_setup_failed", error=str(e))

    await init_db()
    logger.info("database_initialized")

    yield

    await close_db()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="DnD GM assistant platform powered by RAG",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/health/live")
    async def liveness_probe() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready")
    async def readiness_probe() -> dict[str, str]:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ready", "database": "connected"}
        except Exception as e:
            logger.error("readiness_check_failed", error=str(e))
            return {"status": "not ready", "database": "disconnected"}

    return app


app = create_app()
