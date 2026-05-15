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

op: Any = importlib.import_module("alembic.op")

revision = "20260514_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("visibility_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_jobs_status_enqueued_at", "jobs", ["status", "enqueued_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_status_enqueued_at", table_name="jobs")
    op.drop_table("jobs")
