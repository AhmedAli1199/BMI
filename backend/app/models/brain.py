"""The AI Hub chat ("the Brain", app/brain): each person's conversations and every message in them.

An assistant message keeps its trace - which tools ran, how long each took, tokens in/out and how many came
from the cache - so admins can see what it did and what it cost. Screenshots sent with a question are kept
on the user message (BrainImage) so a conversation can be looked back at, and turned into feedback."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPk


class BrainConversation(Base, UUIDPk, TimestampMixin):
    __tablename__ = "brain_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New chat")
    started_on: Mapped[str | None] = mapped_column(String(500))   # page path it was started from


class BrainMessage(Base, UUIDPk):
    __tablename__ = "brain_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brain_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(12), nullable=False)          # user | assistant
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")    # what the person typed / the answer shown
    # User: the exact text the model saw (question + context block) so later turns replay it unchanged (keeps the
    # prompt cache warm). Assistant: unused.
    model_text: Mapped[str | None] = mapped_column(Text)
    # User: {page_path, page_title, record, elements, errors, mode}. Assistant: {show: [...], links: [...], suggestions: [...]}
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Assistant: {route, model, thinking, steps: [{tool, label, args, ms, ok}], input_tokens, cached_tokens, output_tokens, ms, error}
    trace: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rating: Mapped[int | None] = mapped_column(SmallInteger)                # 1 helpful, -1 not
    rating_note: Mapped[str | None] = mapped_column(Text)
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class BrainImage(Base, UUIDPk):
    __tablename__ = "brain_images"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brain_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    mime: Mapped[str] = mapped_column(String(40), nullable=False, default="image/png")
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    label: Mapped[str | None] = mapped_column(String(200))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)


class BrainAction(Base, UUIDPk):
    """Something the Brain offered to do (Phase 4). The Brain only ever *proposes*: the tool checks the request and
    saves it here as "pending", the chat shows it as a card, and it runs only when the person presses Confirm
    (app/brain/actions.py) - as them, with their permissions checked again. Cards expire after a day."""
    __tablename__ = "brain_actions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("brain_conversations.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))   # the answer that shows the card
    kind: Mapped[str] = mapped_column(String(40), nullable=False)               # reminder | log | email | booking | review | automation
    args: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)      # what runs on Confirm (already checked)
    # What the card shows: {title, lines: [[label, value]], links: [{label, href}], confirm: "Set the reminder"}
    preview: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")   # pending | done | cancelled | failed | expired
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)    # {text, links} after it ran (or why not)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
