from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Module
from app.schemas.module import ModuleIngest, ModuleIngestResponse, ModuleResponse
from app.ingestion import IngestionService, ModuleAlreadyExistsError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=list[ModuleResponse])
async def list_modules(
    db: AsyncSession = Depends(get_db),
) -> list[Module]:
    stmt = select(Module)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/ingest", response_model=ModuleIngestResponse)
async def ingest_module(
    request: ModuleIngest,
    db: AsyncSession = Depends(get_db),
) -> ModuleIngestResponse:
    service = IngestionService(db)

    try:
        module, report = await service.ingest_module(request.package_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ModuleAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("module_ingestion_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Module ingestion failed: {str(e)}")

    return ModuleIngestResponse(
        module_id=module.id,
        version=module.version,
        ingestion_report=report,
    )
