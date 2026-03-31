import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY, JSON
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    edition: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    modules: Mapped[list["CampaignModule"]] = relationship(
        "CampaignModule", back_populates="campaign", cascade="all, delete-orphan"
    )
    lore_entities: Mapped[list["LoreEntity"]] = relationship(
        "LoreEntity", back_populates="campaign", cascade="all, delete-orphan"
    )
    session_events: Mapped[list["SessionEvent"]] = relationship(
        "SessionEvent", back_populates="campaign", cascade="all, delete-orphan"
    )
    world_state: Mapped[list["WorldState"]] = relationship(
        "WorldState", back_populates="campaign", cascade="all, delete-orphan"
    )
    chat_turns: Mapped[list["ChatTurn"]] = relationship(
        "ChatTurn", back_populates="campaign", cascade="all, delete-orphan"
    )


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    edition: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("name", "version", name="uq_module_name_version"),)

    campaigns: Mapped[list["CampaignModule"]] = relationship(
        "CampaignModule", back_populates="module"
    )
    source_docs: Mapped[list["SourceDoc"]] = relationship(
        "SourceDoc", back_populates="module", cascade="all, delete-orphan"
    )
    rule_entities: Mapped[list["RuleEntity"]] = relationship(
        "RuleEntity", back_populates="module", cascade="all, delete-orphan"
    )
    lore_entities: Mapped[list["LoreEntity"]] = relationship(
        "LoreEntity", back_populates="module", cascade="all, delete-orphan"
    )


class CampaignModule(Base):
    __tablename__ = "campaign_modules"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modules.id"), primary_key=True
    )
    enabled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="modules")
    module: Mapped["Module"] = relationship("Module", back_populates="campaigns")


class SourceDoc(Base):
    __tablename__ = "source_docs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modules.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    module: Mapped["Module"] = relationship("Module", back_populates="source_docs")
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="source_doc", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_doc_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("source_docs.id", ondelete="CASCADE"), nullable=False
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source_doc: Mapped["SourceDoc"] = relationship("SourceDoc", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_metadata", "metadata_json", postgresql_using="gin"),
    )


class RuleEntity(Base):
    __tablename__ = "rule_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modules.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    module: Mapped["Module"] = relationship("Module", back_populates="rule_entities")

    __table_args__ = (
        UniqueConstraint(
            "module_id", "entity_type", "normalized_name", name="uq_rule_entity_module_type_name"
        ),
    )


class LoreEntity(Base):
    __tablename__ = "lore_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True
    )
    module_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modules.id"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    data_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="lore_entities")
    module: Mapped["Module"] = relationship("Module", back_populates="lore_entities")


class SessionEvent(Base):
    __tablename__ = "session_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="session_events")

    __table_args__ = (
        Index("idx_session_events_campaign_session", "campaign_id", "session_id", "event_time"),
    )


class WorldState(Base):
    __tablename__ = "world_state"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="world_state")

    __table_args__ = (UniqueConstraint("campaign_id", "key", name="uq_world_state_campaign_key"),)


class ChatTurn(Base):
    __tablename__ = "chat_turns"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    trace_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="chat_turns")
