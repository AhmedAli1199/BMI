"""Commission: what Matt's answers and past statements added (Oct 2026).

- PAYE/NIC holdback (35%) and advances on statements; cheque amount.
- First deal = everything on the first invoice.
- £ per attendance bonus (Selling Travel Connect) and rules limited to some issues
  (Sally's Canada Hub at 5.5%).

Revision ID: 0040
Revises: 0039
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def _stamps() -> list:
    return [sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now())]


def upgrade() -> None:
    op.add_column("commission_rules", sa.Column("attendance_bonus_gbp", sa.Numeric(10, 2)))
    op.add_column("commission_rules", sa.Column("edition_includes", postgresql.JSONB()))
    op.add_column("commission_rules", sa.Column("edition_excludes", postgresql.JSONB()))
    op.add_column("commission_settings", sa.Column("first_deal_rule", sa.String(8), nullable=False, server_default="invoice"))
    op.add_column("commission_settings", sa.Column("retention_rate", sa.Numeric(6, 4), nullable=False, server_default="0.35"))
    op.create_table(
        "commission_months",
        sa.Column("id", U, primary_key=True),
        sa.Column("rep_id", U, sa.ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("advances_gbp", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("advances_note", sa.Text()),
        *_stamps(),
        sa.UniqueConstraint("rep_id", "period", name="uq_commission_month_rep_period"),
    )
    op.create_table(
        "commission_attendance",
        sa.Column("id", U, primary_key=True),
        sa.Column("rep_id", U, sa.ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("edition_id", U, sa.ForeignKey("sales_editions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        *_stamps(),
        sa.UniqueConstraint("rep_id", "edition_id", name="uq_commission_attendance_rep_edition"),
    )
    conn = op.get_bind()
    # Plans already loaded: Steve's Connect events pay £75 per attendance; Sally's Canada Hub is at 5.5%.
    conn.execute(sa.text(
        "UPDATE commission_rules r SET attendance_bonus_gbp = 75 FROM sales_reps s "
        "WHERE r.rep_id = s.id AND s.code = 'ST' AND r.title_slugs ? 'stm-connect-events' AND r.attendance_bonus_gbp IS NULL"))
    conn.execute(sa.text(
        "INSERT INTO commission_rules (id, rep_id, name, title_slugs, base_rate, new_business_rate, edition_includes, notes, sort_order, created_at, updated_at) "
        "SELECT gen_random_uuid(), s.id, 'Canada Hub', '[\"selling-canada\", \"selling-travel-guides\"]'::jsonb, 0.055, 0.02, '[\"hub\"]'::jsonb, "
        "'Issues with \"Hub\" in their name, at 5.5% (from Sally''s August 2026 statement). Please check.', -1, now(), now() "
        "FROM sales_reps s WHERE s.code = 'SP' AND EXISTS (SELECT 1 FROM commission_rules r WHERE r.rep_id = s.id) "
        "AND NOT EXISTS (SELECT 1 FROM commission_rules r WHERE r.rep_id = s.id AND r.name = 'Canada Hub')"))


def downgrade() -> None:
    op.drop_table("commission_attendance")
    op.drop_table("commission_months")
    op.drop_column("commission_settings", "retention_rate")
    op.drop_column("commission_settings", "first_deal_rule")
    for c in ("edition_excludes", "edition_includes", "attendance_bonus_gbp"):
        op.drop_column("commission_rules", c)
