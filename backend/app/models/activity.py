import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, UUIDPk

RECURRENCE_VALUES = ("never", "daily", "weekly", "monthly")


class Activity(Base, UUIDPk, ProvenanceMixin):
    """Scheduled/completed tasks and calendar items, migrated as-is from
    Act!'s TBL_ACTIVITY - kept per explicit instruction (2026-09-11), not
    redesigned from scratch, since real data exists (2,131 rows total
    across the three databases, concentrated in Prospects).

    `contact_id`/`company_id` here are the SINGLE primary link, used by our
    own "Log or schedule" UI (always exactly one target by design) and
    backfilled on migrated rows only when Act!'s association data resolves
    to exactly one contact or one company with no ambiguity. Act!'s real
    association data is many-to-many (one activity can list several
    contacts, or both a contact and their employer) - that full picture
    lives in ActivityContact/ActivityCompany/ActivityGroup
    (app/models/activity_link.py), not squeezed into these two columns.
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
    # Act!'s own DURATION column (minutes) - a real, separately-stored
    # value, not always derivable from start_at/end_at (e.g. timeless
    # to-dos, or recurring activities where end_at is the series end).
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    # Denormalized display names, resolved via a join to Act!'s
    # TBL_ACCESSOR at migration time - NOT a FK to our own `users` table.
    # Act!'s accessor accounts (its own users) have no established mapping
    # to our CRM's user accounts; building that mapping is a human decision
    # parked for the final cutover migration (see BACKLOG.md). Storing the
    # plain name now means "organized by Clare Hunter" renders correctly
    # immediately, without waiting on that mapping - created_by_user_id
    # below can be backfilled with a real FK once it exists, independent of
    # this column.
    organized_by_name: Mapped[str | None] = mapped_column(String(256))

    # Everything below is new as of the CRM's own scheduling UI - always
    # null/false/"never" on migrated rows, since Act! didn't carry a
    # concept of "which of our users" beyond its own separate user table.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence: Mapped[str] = mapped_column(String(20), nullable=False, default="never")
