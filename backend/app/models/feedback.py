"""Feedback from people testing BMI Brain: what they said, what they pointed at on the page, screenshots,
and what the app saw at the time (page, browser, recent errors). Everyone sees everyone's, so nobody reports
the same thing twice; each one can also become a GitHub issue."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPk

FEEDBACK_KINDS = ("broken", "confusing", "idea", "looks_wrong")
FEEDBACK_STATUSES = ("new", "looking", "fixed", "wont_do")


class Feedback(Base, UUIDPk, TimestampMixin):
    __tablename__ = "feedback"

    number: Mapped[int] = mapped_column(Integer, Identity(), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    user_role: Mapped[str | None] = mapped_column(String(50))
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="broken")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    page_path: Mapped[str] = mapped_column(String(500), nullable=False, default="/", index=True)
    page_title: Mapped[str | None] = mapped_column(String(300))
    page_url: Mapped[str | None] = mapped_column(String(1000))
    # [{label, role, text, selector, path, heading, source: ["file.tsx:12", ...], rect: {x,y,w,h}, viewport: {w,h}}]
    elements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # {browser, viewport, screen, zoom, theme, errors: [{at, kind, message}], app_version, time_zone}
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
    status_note: Mapped[str | None] = mapped_column(Text)
    status_by: Mapped[str | None] = mapped_column(String(255))
    status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    me_too: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)   # [{user_id, name, at}]
    comments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{id, user_id, name, text, at}]
    github_number: Mapped[int | None] = mapped_column(Integer)
    github_url: Mapped[str | None] = mapped_column(String(500))
    github_error: Mapped[str | None] = mapped_column(Text)
    github_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FeedbackImage(Base, UUIDPk):
    __tablename__ = "feedback_images"

    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label: Mapped[str | None] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, default="image/png")
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    github_url: Mapped[str | None] = mapped_column(String(500))
