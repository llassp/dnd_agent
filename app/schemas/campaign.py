from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    edition: str = Field(..., min_length=1, max_length=50)


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    edition: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignModuleEnable(BaseModel):
    module_id: UUID
    priority: int = Field(default=50, ge=1, le=100)


class CampaignModuleResponse(BaseModel):
    campaign_id: UUID
    module_id: UUID
    enabled_at: datetime
    priority: int

    class Config:
        from_attributes = True
