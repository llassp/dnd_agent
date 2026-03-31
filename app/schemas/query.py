from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    campaign_id: UUID
    session_id: str
    user_input: str = Field(..., min_length=1)
    mode: str = Field(default="auto", pattern="^(rules|narrative|state|encounter|auto)$")


class Citation(BaseModel):
    chunk_id: UUID
    source_doc_id: UUID
    title: str
    uri: str | None
    snippet: str = Field(..., max_length=200)


class StateUpdate(BaseModel):
    op: str = Field(..., pattern="^(set|inc|append)$")
    path: str
    value: Any
    reason: str


class QueryResponse(BaseModel):
    answer: str
    used_agent: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)
    state_updates: list[StateUpdate] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


class ChatTurnCreate(BaseModel):
    campaign_id: UUID
    session_id: str
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)
    trace_json: dict[str, Any] | None = None


class ChatTurnResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    session_id: str
    role: str
    content: str
    created_at: datetime
    trace_json: dict[str, Any] | None

    class Config:
        from_attributes = True
