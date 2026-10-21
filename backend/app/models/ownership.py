import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class ClientOwner(Base, UUIDPk):
    """Who looks after a client on one magazine (app/sales/ownership.py has the rules and the list of "areas").
    One row per company per area. Rows the rules wrote are worked out again every night; a row a person chose
    (changed it on the company page, or answered the Review Queue question) is kept as it is - `chosen_by` set."""

    __tablename__ = "client_owners"
    __table_args__ = (UniqueConstraint("company_id", "area", name="uq_client_owners_company_area"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    # None = nobody yet ("first to take it") or waiting for someone to answer the question
    rep_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="SET NULL"), index=True)
    # product | last_contact | last_booking | region | new_business | first_to_take | chosen | not_sure | nobody
    rule: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(400), nullable=False)   # plain words, shown on the company page
    evidence_on: Mapped[date | None] = mapped_column(Date)            # the note, booking or answer it rests on
    regions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # Selling Travel regions spotted
    chosen_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    chosen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
