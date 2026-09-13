import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk

# Generic "system drafts, human approves" queue, reused by every automation
# (bounce handling, AI follow-up drafts, contact hygiene fixes, etc. - see
# docs/build-spec.txt). One row = one thing an automation wants to do but
# won't do on its own.
REVIEW_QUEUE_STATUSES = ("pending", "approved", "rejected")


class ReviewQueueItem(Base, UUIDPk):
    __tablename__ = "review_queue"
    __table_args__ = (CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_review_queue_status"),)

    # Which automation created this, e.g. "bounce_handling", "ai_followup_draft".
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # What the automation proposes to do, and to what - kept generic (jsonb)
    # since every automation's payload shape is different (a draft email
    # body vs. a proposed contact-field correction vs. a bounce action).
    # entity_type/entity_id give a consistent way to link back to the
    # contact/company/etc. this item is about, same pattern as Note/History.
    entity_type: Mapped[str | None] = mapped_column(String(20), index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    # The specific action a human clicked (e.g. "confirm_hard_bounce",
    # "use_fallback") - see app/automations/registry.py. `status` is the
    # coarse approved/rejected bucket every action declares itself into
    # (for simple counts/filters); resolved_action is the precise thing
    # that actually happened, which is what a reviewer or auditor actually
    # wants to read back later ("what did we do about this one?").
    resolved_action: Mapped[str | None] = mapped_column(String(64))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
