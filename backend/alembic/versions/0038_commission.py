"""Commission structure: per-salesperson plans, settings, approved statements; new-business decisions on
bookings; new contract-publishing guide flag and event cost sign-off on editions.

Revision ID: 0038
Revises: 0037
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "commission_rules",
        sa.Column("id", U, primary_key=True),
        sa.Column("rep_id", U, sa.ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("title_slugs", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("base_rate", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("new_business_rate", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("new_business_rate_change_on", sa.Date()),
        sa.Column("new_business_rate_after", sa.Numeric(6, 4)),
        sa.Column("new_guide_bonus_gbp", sa.Numeric(10, 2)),
        sa.Column("threshold_bonus_gbp", sa.Numeric(10, 2)),
        sa.Column("threshold_gbp", sa.Numeric(12, 2)),
        sa.Column("new_client_bonus_gbp", sa.Numeric(10, 2)),
        sa.Column("event_profit_rate", sa.Numeric(6, 4)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_until", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "commission_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("earned_on", sa.String(16), nullable=False, server_default="publication"),
        sa.Column("lookback_months", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("first_deal_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("event_profit_basis", sa.String(8), nullable=False, server_default="all"),
        sa.Column("fallback_flag", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", TS),
    )
    op.create_table(
        "commission_statements",
        sa.Column("id", U, primary_key=True),
        sa.Column("rep_id", U, sa.ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("total_gbp", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("approved_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", TS),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("rep_id", "period", name="uq_commission_statement_rep_period"),
    )
    for name, typ in (("new_business_override", sa.Boolean()), ("new_business_reason", sa.String(300)),
                      ("new_business_set_by_user_id", U), ("new_business_set_at", TS)):
        op.add_column("sales_orders", sa.Column(name, typ, sa.ForeignKey("users.id", ondelete="SET NULL")) if name.endswith("user_id")
                      else sa.Column(name, typ))
    op.add_column("sales_editions", sa.Column("new_contract_guide", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("sales_editions", sa.Column("new_contract_rep_id", U, sa.ForeignKey("sales_reps.id", ondelete="SET NULL")))
    for name in ("costs_final", "costs_signed_off"):
        op.add_column("sales_editions", sa.Column(f"{name}_at", TS))
        op.add_column("sales_editions", sa.Column(f"{name}_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL")))


def downgrade() -> None:
    for name in ("costs_final", "costs_signed_off"):
        op.drop_column("sales_editions", f"{name}_by_user_id")
        op.drop_column("sales_editions", f"{name}_at")
    op.drop_column("sales_editions", "new_contract_rep_id")
    op.drop_column("sales_editions", "new_contract_guide")
    for name in ("new_business_set_at", "new_business_set_by_user_id", "new_business_reason", "new_business_override"):
        op.drop_column("sales_orders", name)
    op.drop_table("commission_statements")
    op.drop_table("commission_settings")
    op.drop_table("commission_rules")
