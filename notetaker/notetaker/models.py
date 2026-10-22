"""Tables. Each client app (BMI Brain, or any other project) has its own key and webhook; every
meeting belongs to one client."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from notetaker.db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    webhook_url: Mapped[str | None] = mapped_column(Text)
    webhook_secret: Mapped[str] = mapped_column(String(128))
    bot_name: Mapped[str | None] = mapped_column(String(100))
    chat_message: Mapped[str | None] = mapped_column(Text)        # what the bot posts in the meeting chat when it joins
    summary_instructions: Mapped[str | None] = mapped_column(Text)  # extra guidance for this client's summaries
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    notes_style: Mapped[str] = mapped_column(String(20), default="general")   # see notetaker/styles.py
    key_hint: Mapped[str | None] = mapped_column(String(20))                   # first characters of the key, to recognise it
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Each app brings its own Gemini key (encrypted; see security.encrypt). No key = transcripts only.
    gemini_key_enc: Mapped[str | None] = mapped_column(Text)
    gemini_key_hint: Mapped[str | None] = mapped_column(String(12))
    max_concurrent: Mapped[int | None] = mapped_column(Integer)   # this app's own limit (None = only the overall one)
    # Zoom, per app: its own Zoom app's keys (pasted in the console). The meeting bot holds one set of Zoom keys per
    # "project", so an app with Zoom gets its own project there - set up by the attendee-sync container
    # (deploy/attendee_sync.py), which reports back the project's key and webhook secret.
    zoom_client_id: Mapped[str | None] = mapped_column(String(100))
    zoom_secret_enc: Mapped[str | None] = mapped_column(Text)
    zoom_secret_hint: Mapped[str | None] = mapped_column(String(12))
    zoom_webhook_secret_enc: Mapped[str | None] = mapped_column(Text)   # the Zoom app's Secret Token (Features > Access), for its events
    zoom_status: Mapped[str | None] = mapped_column(String(20))   # None (off) | pending | ready | error
    zoom_error: Mapped[str | None] = mapped_column(Text)
    bot_project_id: Mapped[str | None] = mapped_column(String(64))
    bot_key_enc: Mapped[str | None] = mapped_column(Text)
    bot_webhook_secret_enc: Mapped[str | None] = mapped_column(Text)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ServiceState(Base):
    """Small key/value facts about the service itself, e.g. when the worker last ran."""
    __tablename__ = "service_state"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (UniqueConstraint("client_id", "external_id", name="uq_meeting_client_external"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(200))   # the client's own id (e.g. a calendar event) - makes scheduling idempotent
    meeting_url: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(Text)
    join_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))   # expected end, for booking the slot
    bot_name: Mapped[str] = mapped_column(String(100))
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", index=True)
    status_detail: Mapped[str | None] = mapped_column(Text)
    bot_provider: Mapped[str] = mapped_column(String(20))
    bot_id: Mapped[str | None] = mapped_column(String(100), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    participants: Mapped[list] = mapped_column(JSON, default=list)
    transcript: Mapped[list] = mapped_column(JSON, default=list)     # [{speaker, start_ms, end_ms, text}]
    summary: Mapped[dict | None] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, default=0)       # finalising attempts
    ai_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    ai_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    client: Mapped[Client] = relationship()
    events: Mapped[list["MeetingEvent"]] = relationship(order_by="MeetingEvent.created_at", cascade="all, delete-orphan")


class MeetingEvent(Base):
    """Every status change, for the timeline and for debugging."""
    __tablename__ = "meeting_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProcessedHook(Base):
    """Incoming webhook ids already handled, so a retried delivery is ignored."""
    __tablename__ = "processed_hooks"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OutboxMessage(Base):
    """Webhooks waiting to go to a client app. Saved first, then delivered with retries."""
    __tablename__ = "outbox"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    meeting_id: Mapped[str | None] = mapped_column(String(32), index=True)
    event: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)   # pending | delivered | dead
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ZoomConnection(Base):
    """Someone's Zoom, connected from a client app ("Connect Zoom"). The notetaker holds the sign-in itself
    (notetaker/zoomapi.py): the refresh token, encrypted, made with the app's own Zoom keys - so an app can only send
    bots on behalf of its own people, and disconnecting revokes it at Zoom."""
    __tablename__ = "zoom_connections"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    zoom_user_id: Mapped[str] = mapped_column(String(100), index=True)
    account_id: Mapped[str | None] = mapped_column(String(100))
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    bot_connection_id: Mapped[str] = mapped_column(String(100), default="")   # no longer used (the meeting bot held it before)
    external_user: Mapped[str | None] = mapped_column(String(200))   # the app's own id for the person
    state: Mapped[str] = mapped_column(String(20), default="connected")   # connected | disconnected
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
