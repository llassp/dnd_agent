import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, SessionEvent as SessionEventModel, WorldState as WorldStateModel, Campaign
from app.db.models import SessionEvent, WorldState
from app.schemas.session import SessionEventCreate, SessionEventResponse, TimelineResponse
from app.schemas.state import StateApplyRequest, StatePatch, StateApplyResponse, WorldStateResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

session_router = APIRouter(prefix="/sessions", tags=["sessions"])
state_router = APIRouter(prefix="/state", tags=["state"])


@session_router.post("/{session_id}/events", response_model=SessionEventResponse)
async def create_session_event(
    session_id: uuid.UUID,
    request: SessionEventCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionEvent:
    campaign_stmt = select(Campaign).where(Campaign.id == request.campaign_id)
    campaign_result = await db.execute(campaign_stmt)
    campaign = campaign_result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    event = SessionEvent(
        campaign_id=request.campaign_id,
        session_id=session_id,
        event_type=request.event_type,
        payload_json=request.payload_json,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info("session_event_created", event_id=str(event.id), campaign_id=str(request.campaign_id))

    return event


@session_router.get("/{session_id}/events", response_model=TimelineResponse)
async def get_timeline(
    session_id: uuid.UUID,
    campaign_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    offset = (page - 1) * page_size

    count_stmt = select(func.count()).where(
        SessionEvent.campaign_id == campaign_id,
        SessionEvent.session_id == session_id,
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    events_stmt = (
        select(SessionEvent)
        .where(
            SessionEvent.campaign_id == campaign_id,
            SessionEvent.session_id == session_id,
        )
        .order_by(SessionEvent.event_time)
        .offset(offset)
        .limit(page_size)
    )
    events_result = await db.execute(events_stmt)
    events = list(events_result.scalars().all())

    return TimelineResponse(
        events=[SessionEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@state_router.post("/apply", response_model=StateApplyResponse)
async def apply_state_patches(
    request: StateApplyRequest,
    db: AsyncSession = Depends(get_db),
) -> StateApplyResponse:
    campaign_stmt = select(Campaign).where(Campaign.id == request.campaign_id)
    campaign_result = await db.execute(campaign_stmt)
    campaign = campaign_result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    applied_patches = []
    updated_states = []

    for patch in request.patches:
        existing_stmt = select(WorldState).where(
            WorldState.campaign_id == request.campaign_id,
            WorldState.key == patch.path,
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            if patch.op == "set":
                existing.value_json = patch.value
            elif patch.op == "inc":
                current = existing.value_json.get("value", 0)
                existing.value_json = {"value": current + patch.value}
            elif patch.op == "append":
                if not isinstance(existing.value_json.get("list"), list):
                    existing.value_json = {"list": []}
                existing.value_json["list"].append(patch.value)
            updated_states.append(existing)
        else:
            if patch.op == "set":
                value = patch.value
            elif patch.op == "inc":
                value = {"value": patch.value}
            elif patch.op == "append":
                value = {"list": [patch.value]}
            else:
                value = patch.value

            new_state = WorldState(
                campaign_id=request.campaign_id,
                key=patch.path,
                value_json=value,
            )
            db.add(new_state)
            updated_states.append(new_state)

        applied_patches.append(patch)

    await db.commit()

    for state in updated_states:
        await db.refresh(state)

    logger.info(
        "state_patches_applied",
        campaign_id=str(request.campaign_id),
        patch_count=len(applied_patches),
    )

    return StateApplyResponse(
        applied=applied_patches,
        world_state=[WorldStateResponse.model_validate(s) for s in updated_states],
    )


@state_router.get("/campaign/{campaign_id}", response_model=list[WorldStateResponse])
async def get_world_state(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[WorldState]:
    stmt = select(WorldState).where(WorldState.campaign_id == campaign_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
