"""create jobs table

Revision ID: 20260514_01
Revises:
Create Date: 2026-05-14
"""

from __future__ import annotations

# pyright: reportGeneralTypeIssues=false, reportAttributeAccessIssue=false
import importlib
from typing import Any

import sqlalchemy as sa
from qdrant_loader.core.state.models import UTCDateTime

op: Any = importlib.import_module("alembic.op")

revision = "20260514_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use checkfirst=True / if_not_exists=True so this migration is idempotent.
    # This handles databases that already have the jobs table created directly
    # by SQLAlchemy (create_all) before Alembic was introduced.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "jobs" not in existing_tables:
        op.create_table(
            "jobs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("enqueued_at", UTCDateTime(timezone=True), nullable=False),
            sa.Column("started_at", UTCDateTime(timezone=True), nullable=True),
            sa.Column("finished_at", UTCDateTime(timezone=True), nullable=True),
            sa.Column(
                "attempts", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("visibility_deadline", UTCDateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = (
        {idx["name"] for idx in inspector.get_indexes("jobs")}
        if "jobs" in existing_tables
        else set()
    )
    if "ix_jobs_status_enqueued_at" not in existing_indexes:
        op.create_index(
            "ix_jobs_status_enqueued_at",
            "jobs",
            ["status", "enqueued_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_jobs_status_enqueued_at", table_name="jobs")
    op.drop_table("jobs")
