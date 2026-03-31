from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Campaign, CampaignModule, Module
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignModuleEnable,
    CampaignModuleResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
) -> list[Campaign]:
    stmt = select(Campaign)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    campaign = Campaign(
        name=campaign_data.name,
        edition=campaign_data.edition,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    logger.info("campaign_created", campaign_id=str(campaign.id))

    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign


@router.post("/{campaign_id}/enable-module", response_model=CampaignModuleResponse)
async def enable_module(
    campaign_id: UUID,
    request: CampaignModuleEnable,
    db: AsyncSession = Depends(get_db),
) -> CampaignModule:
    campaign_stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign_result = await db.execute(campaign_stmt)
    campaign = campaign_result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    module_stmt = select(Module).where(Module.id == request.module_id)
    module_result = await db.execute(module_stmt)
    module = module_result.scalar_one_or_none()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    existing_stmt = select(CampaignModule).where(
        CampaignModule.campaign_id == campaign_id,
        CampaignModule.module_id == request.module_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.priority = request.priority
        await db.commit()
        await db.refresh(existing)
        logger.info("module_priority_updated", campaign_id=str(campaign_id), module_id=str(request.module_id))
        return existing

    campaign_module = CampaignModule(
        campaign_id=campaign_id,
        module_id=request.module_id,
        priority=request.priority,
    )
    db.add(campaign_module)
    await db.commit()
    await db.refresh(campaign_module)

    logger.info("module_enabled", campaign_id=str(campaign_id), module_id=str(request.module_id))

    return campaign_module


@router.get("/{campaign_id}/modules", response_model=list[CampaignModuleResponse])
async def get_campaign_modules(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CampaignModule]:
    stmt = select(CampaignModule).where(CampaignModule.campaign_id == campaign_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
