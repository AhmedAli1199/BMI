"""Reminders, in-app notifications, connected Outlook mailboxes, mail-merge
templates and mail merges.

- Reminder: "remind me about this contact on <date>" - fires an in-app
  notification (and an email from the automation mailbox) when due.
- Notification: the bell in the top bar. Anything can create one (a due
  reminder, a finished mail merge); email delivery is a separate,
  retryable step (email_status) so a mail hiccup never loses the in-app
  notification.
- MailAccount: a user's own Outlook mailbox, connected with "Sign in with
  Microsoft" (delegated OAuth). Tokens are stored encrypted, never shown.
- MailTemplate / MailMerge / MailMergeRecipient / MailAttachment: Act!'s
  Write > Mail Merge - one row per merge, one per recipient (so a send
  can be paused, resumed after a restart, and audited per person).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class Reminder(Base, UUIDPk):
    __tablename__ = "reminders"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    email_me: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)  # open | done | cancelled
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base, UUIDPk):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)  # reminder | mail_merge | ...
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # None = no email wanted; pending -> sent | failed | skipped (no mailbox configured / user opted out)
    email_status: Mapped[str | None] = mapped_column(String(16), index=True)
    email_error: Mapped[str | None] = mapped_column(Text)


class MailAccount(Base, UUIDPk):
    __tablename__ = "mail_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    refresh_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_error: Mapped[str | None] = mapped_column(Text)


class MailTemplate(Base, UUIDPk):
    __tablename__ = "mail_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # What it's for, so a salesperson finds the right one: brand (obh | tbtm | stm), the title, and the kind of email
    # (pitch | follow_up | event | launch | renewal | general).
    brand: Mapped[str | None] = mapped_column(String(10), index=True)
    title_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_titles.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(12), nullable=False, default="general")
    description: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[str | None] = mapped_column(String(20))         # "act" = brought over from ACT!
    needs_check: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)   # loaded, not yet read through by a person
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MailMerge(Base, UUIDPk):
    __tablename__ = "mail_merges"

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    output: Mapped[str] = mapped_column(String(16), nullable=False)  # email | word | labels | data
    source_label: Mapped[str | None] = mapped_column(String(300))  # "Group: Freelance writers", "Current lookup"
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    from_email: Mapped[str | None] = mapped_column(String(255))
    cc: Mapped[str | None] = mapped_column(String(500))
    bcc: Mapped[str | None] = mapped_column(String(500))
    # email_full (subject + message) | subject_only | none - Act!'s "Record history type"
    record_history: Mapped[str] = mapped_column(String(16), nullable=False, default="email_full")
    history_regarding: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)  # queued|sending|done|cancelled|failed
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MailMergeRecipient(Base, UUIDPk):
    __tablename__ = "mail_merge_recipients"

    merge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mail_merges.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)  # queued|sent|failed|skipped
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MailAttachment(Base, UUIDPk):
    __tablename__ = "mail_attachments"

    merge_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("mail_merges.id", ondelete="CASCADE"), index=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


