"""Add automation_job_runs (scanner run history) and the two review_queue
indexes the workstream stats query leans on.

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", sa.String(64), nullable=False),
        sa.Column("trigger", sa.String(16), nullable=False, server_default="scheduled"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("items_queued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_automation_job_runs_job_id", "automation_job_runs", ["job_id"])
    op.create_index("ix_automation_job_runs_started_at", "automation_job_runs", ["started_at"])
    # "Latest N runs for this job" is the only read pattern.
    op.create_index("ix_automation_job_runs_job_started", "automation_job_runs", ["job_id", "started_at"])

    # Workstream stats group by kind and a day bucket of created_at (new)
    # or reviewed_at (resolved).
    op.create_index("ix_review_queue_kind_created", "review_queue", ["kind", "created_at"])
    op.create_index("ix_review_queue_kind_reviewed", "review_queue", ["kind", "reviewed_at"])


def downgrade() -> None:
    op.drop_index("ix_review_queue_kind_reviewed", table_name="review_queue")
    op.drop_index("ix_review_queue_kind_created", table_name="review_queue")
    op.drop_index("ix_automation_job_runs_job_started", table_name="automation_job_runs")
    op.drop_index("ix_automation_job_runs_started_at", table_name="automation_job_runs")
    op.drop_index("ix_automation_job_runs_job_id", table_name="automation_job_runs")
    op.drop_table("automation_job_runs")
