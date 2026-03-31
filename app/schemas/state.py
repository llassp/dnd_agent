from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StatePatch(BaseModel):
    op: str = Field(..., pattern="^(set|inc|append)$")
    path: str = Field(..., min_length=1)
    value: Any


class StateApplyRequest(BaseModel):
    campaign_id: UUID
    patches: list[StatePatch] = Field(..., min_length=1)


class WorldStateResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    key: str
    value_json: dict[str, Any]
    updated_at: datetime

    class Config:
        from_attributes = True


class StateApplyResponse(BaseModel):
    applied: list[StatePatch]
    world_state: list[WorldStateResponse]
