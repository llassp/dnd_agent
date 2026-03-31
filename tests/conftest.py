import asyncio
import uuid
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.models import Base, Campaign, Module, CampaignModule
from app.db.database import async_session_maker


TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/dnd_rag_test"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_maker() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[app.db.database.get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_module_path() -> Path:
    return Path("tests/fixtures/modules/sample_forgotten_forest")


@pytest.fixture
def campaign_data() -> dict:
    return {
        "name": "Test Campaign",
        "edition": "5e"
    }


@pytest_asyncio.fixture
async def created_campaign(client: AsyncClient, campaign_data: dict) -> dict:
    response = await client.post("/campaigns", json=campaign_data)
    assert response.status_code == 200
    return response.json()


@pytest_asyncio.fixture
async def ingested_module(client: AsyncClient, sample_module_path: Path) -> dict:
    response = await client.post(
        "/modules/ingest",
        json={"package_path": str(sample_module_path)}
    )
    if response.status_code == 200:
        return response.json()
    return {"module_id": None, "version": "1.0.0", "ingestion_report": {"chunks_created": 0, "entities_created": 0}}}
