from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModuleIngest(BaseModel):
    package_path: str = Field(..., min_length=1)


class ModuleManifest(BaseModel):
    name: str
    version: str
    edition: str
    priority: int = Field(default=50, ge=1, le=100)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    hooks: dict[str, list[str]] = Field(default_factory=dict)
    compatibility: dict[str, str] = Field(default_factory=dict)


class IngestionReport(BaseModel):
    chunks_created: int = 0
    entities_created: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ModuleIngestResponse(BaseModel):
    module_id: UUID
    version: str
    ingestion_report: IngestionReport


class ModuleResponse(BaseModel):
    id: UUID
    name: str
    version: str
    edition: str
    manifest_json: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class SourceDocResponse(BaseModel):
    id: UUID
    module_id: UUID
    title: str
    source_type: str
    uri: str | None
    checksum: str
    version: str
    metadata_json: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
