import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, UUIDPk


class Activity(Base, UUIDPk, ProvenanceMixin):
    """Scheduled/completed tasks and calendar items, migrated as-is from
    Act!'s TBL_ACTIVITY - kept per explicit instruction (2026-09-11), not
    redesigned from scratch, since real data exists (2,131 rows total
    across the three databases, concentrated in Prospects). Link to a
    contact where Act!'s data made that unambiguous; otherwise left
    unlinked rather than guessed.
    """

    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("source_db", "source_act_id", name="uq_activities_source"),
        CheckConstraint("contact_id IS NULL OR company_id IS NULL", name="ck_activities_one_owner"),
    )

    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True)

    activity_type: Mapped[str | None] = mapped_column(String(128))  # decoded via TBL_ACTIVITYTYPE
    subject: Mapped[str | None] = mapped_column(String(512))  # Act! "REGARDING"
    details: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(256))

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_timeless: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # was it marked done in Act!
