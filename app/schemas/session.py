from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SessionEventCreate(BaseModel):
    campaign_id: UUID
    event_type: str = Field(..., min_length=1)
    payload_json: dict[str, Any] = Field(default_factory=dict)


class SessionEventResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    session_id: UUID
    event_type: str
    event_time: datetime
    payload_json: dict[str, Any]

    class Config:
        from_attributes = True


class TimelineResponse(BaseModel):
    events: list[SessionEventResponse]
    total: int
    page: int
    page_size: int
