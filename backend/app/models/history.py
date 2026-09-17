import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, UUIDPk

# History rows this pipeline actually migrates. Act!'s TBL_HISTORY is
# dominated by its own audit/sync noise (Access Changed, Contact Deleted,
# Field Changed, Contact Linked/Unlinked, Received Sync, Data Moved) -
# across all three databases that noise is 60-90%+ of the rows and carries
# no sales-relevant information. migration/etl.py drops any history type
# NOT in this list; everything else (the actual calls/emails/meetings/
# letters/to-dos BMI's sales team logged) is kept. See docs/act-schema/*.md
# "Observations" sections for the exact per-database noise breakdown.
HISTORY_TYPES_KEPT = {
    "Call Attempted",
    "Call Completed",
    "Call Received",
    "Call Left Message",
    "Meeting Held",
    "Letter Sent",
    "Fax Sent",
    "E-mail Sent",
    "E-mail Not Sent",
    "E-mail Attachment",
    "E-mail Auto Attached",
    "To-do Done",
    "Personal Activity Completed",
    "Appointment Completed",
    "New Opportunity",
    "Attachment",
}

HISTORY_ENTITY_TYPES = ("contact", "company", "group", "opportunity")


class HistoryEntry(Base, UUIDPk, ProvenanceMixin):
    """Flattened from TBL_CONTACT_HISTORY / TBL_COMPANY_HISTORY /
    TBL_GROUP_HISTORY / TBL_OPPORTUNITY_HISTORY, same reasoning and same
    simplification as Note (see note.py) - group/opportunity added since
    they're real data the original migration dropped, not Act! plumbing.
    """

    __tablename__ = "history_entries"
    __table_args__ = (
        UniqueConstraint("source_db", "source_act_id", name="uq_history_entries_source"),
        CheckConstraint(
            "entity_type IN ('contact', 'company', 'group', 'opportunity')", name="ck_history_entity_type"
        ),
    )

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    history_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(512))  # Act! "REGARDING"
    details: Mapped[str | None] = mapped_column(Text)  # can be raw HTML/RTF from Outlook - kept verbatim
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # New as of the CRM's own "Log History" UI - null/false on migrated rows.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
