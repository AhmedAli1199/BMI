"""Commission plans and statements (BMI's commission structure, Oct 2026).

A salesperson's plan is a set of rules, one per product group ("Selling Travel
Magazine", "Guides and supplements"...). Each rule says which titles it covers,
the base rate on the salesperson's own revenue, the extra rate on new business,
and any bonuses or event profit share. Statements are worked out from the
order register (app/sales/commission.py) and frozen when a manager approves them.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPk


class CommissionRule(Base, UUIDPk, TimestampMixin):
    __tablename__ = "commission_rules"

    rep_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)          # "Selling Travel Magazine (print and digital)"
    title_slugs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    base_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)       # 0.055 = 5.5%
    new_business_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    # A temporary new-business rate: from this publication date on, new_business_rate_after applies instead.
    new_business_rate_change_on: Mapped[date | None] = mapped_column(Date)
    new_business_rate_after: Mapped[float | None] = mapped_column(Numeric(6, 4))
    new_guide_bonus_gbp: Mapped[float | None] = mapped_column(Numeric(10, 2))     # per new contract-publishing guide
    threshold_bonus_gbp: Mapped[float | None] = mapped_column(Numeric(10, 2))     # once a title's own revenue in a calendar year passes...
    threshold_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))           # ...this much (checked per title)
    new_client_bonus_gbp: Mapped[float | None] = mapped_column(Numeric(10, 2))    # once per new customer
    event_profit_rate: Mapped[float | None] = mapped_column(Numeric(6, 4))        # share of each signed-off event's gross profit
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CommissionSettings(Base):
    """One row: how the structure is applied (the answers to BMI's open questions live here, so changing one is a setting)."""
    __tablename__ = "commission_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    earned_on: Mapped[str] = mapped_column(String(16), nullable=False, default="publication")   # publication | booked
    lookback_months: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    first_deal_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # 0 = bookings made the same day as the first one
    event_profit_basis: Mapped[str] = mapped_column(String(8), nullable=False, default="all")  # all (whole event) | own
    fallback_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CommissionStatement(Base, UUIDPk, TimestampMixin):
    """An approved month for one salesperson: the lines as they were paid, so later edits can't change them."""
    __tablename__ = "commission_statements"
    __table_args__ = (UniqueConstraint("rep_id", "period", name="uq_commission_statement_rep_period"),)

    rep_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="CASCADE"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)   # "2026-10"
    total_gbp: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
