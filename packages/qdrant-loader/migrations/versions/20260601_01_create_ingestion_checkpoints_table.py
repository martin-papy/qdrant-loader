"""Create ingestion_checkpoints table for WS-2 checkpoint & resume feature

Revision ID: 20260601_01
Revises: 20260514_01
Create Date: 2026-06-01
"""

from __future__ import annotations

# pyright: reportGeneralTypeIssues=false, reportAttributeAccessIssue=false
import importlib
from typing import Any

import sqlalchemy as sa

op: Any = importlib.import_module("alembic.op")

revision = "20260601_01"
down_revision = "20260514_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ingestion_checkpoints table for storing pagination cursors."""
    # Use checkfirst=True so this migration is idempotent
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "ingestion_checkpoints" not in existing_tables:
        op.create_table(
            "ingestion_checkpoints",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("cursor_kind", sa.String(), nullable=False),
            sa.Column("cursor_value", sa.Text(), nullable=False),
            sa.Column("batch_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "project_id", "source_type", "source", name="uq_checkpoint_source"
            ),
        )

    # Create indexes for efficient lookups
    existing_indexes = (
        {idx["name"] for idx in inspector.get_indexes("ingestion_checkpoints")}
        if "ingestion_checkpoints" in existing_tables
        else set()
    )
    
    if "ix_ingestion_checkpoints_project_source" not in existing_indexes:
        op.create_index(
            "ix_ingestion_checkpoints_project_source",
            "ingestion_checkpoints",
            ["project_id", "source_type", "source"],
            unique=False,
        )

    if "ix_ingestion_checkpoints_updated_at" not in existing_indexes:
        op.create_index(
            "ix_ingestion_checkpoints_updated_at",
            "ingestion_checkpoints",
            ["updated_at"],
            unique=False,
        )


def downgrade() -> None:
    """Drop ingestion_checkpoints table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "ingestion_checkpoints" in existing_tables:
        op.drop_table("ingestion_checkpoints")
