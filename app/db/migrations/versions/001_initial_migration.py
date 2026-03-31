"""Initial migration with pgvector extension

Revision ID: 001
Revises:
Create Date: 2026-03-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('edition', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'modules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('edition', sa.Text(), nullable=False),
        sa.Column('manifest_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('name', 'version', name='uq_module_name_version'),
    )

    op.create_table(
        'campaign_modules',
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('module_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('modules.id'), primary_key=True),
        sa.Column('enabled_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='50'),
    )

    op.create_table(
        'source_docs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('module_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('modules.id'), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('uri', sa.Text(), nullable=True),
        sa.Column('checksum', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_doc_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_docs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding', postgresql.JSONB(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    op.create_index('idx_chunks_metadata', 'chunks', ['metadata_json'], postgresql_using='gin')
    op.create_index('idx_chunks_fts', 'chunks', [sa.text("to_tsvector('english', chunk_text)")], postgresql_using='gin')

    op.create_table(
        'rule_entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('module_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('modules.id'), nullable=False),
        sa.Column('entity_type', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('normalized_name', sa.Text(), nullable=False),
        sa.Column('data_json', postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint('module_id', 'entity_type', 'normalized_name', name='uq_rule_entity_module_type_name'),
    )

    op.create_table(
        'lore_entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=True),
        sa.Column('module_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('modules.id'), nullable=True),
        sa.Column('entity_type', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('aliases', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('data_json', postgresql.JSONB(), nullable=False),
    )

    op.create_table(
        'session_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('payload_json', postgresql.JSONB(), nullable=False),
    )

    op.create_index('idx_session_events_campaign_session', 'session_events', ['campaign_id', 'session_id', 'event_time'])

    op.create_table(
        'world_state',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value_json', postgresql.JSONB(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('campaign_id', 'key', name='uq_world_state_campaign_key'),
    )

    op.create_index('idx_world_state_campaign_key', 'world_state', ['campaign_id', 'key'])

    op.create_table(
        'chat_turns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('trace_json', postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('chat_turns')
    op.drop_table('world_state')
    op.drop_table('session_events')
    op.drop_table('lore_entities')
    op.drop_table('rule_entities')
    op.drop_index('idx_chunks_fts', 'chunks')
    op.drop_index('idx_chunks_metadata', 'chunks')
    op.drop_index('idx_chunks_embedding', 'chunks')
    op.drop_table('chunks')
    op.drop_table('source_docs')
    op.drop_table('campaign_modules')
    op.drop_table('modules')
    op.drop_table('campaigns')
