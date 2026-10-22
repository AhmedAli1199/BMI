"""The meeting-bot adapter. Anything that can join a call and hand back a transcript plugs in here
(Attendee today; Recall, Vexa or a desktop-upload source later) without the rest of the service changing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class BotRequest:
    meeting_id: str
    meeting_url: str
    bot_name: str
    join_at: datetime | None = None
    chat_message: str | None = None
    dedupe_key: str | None = None
    zoom_user_id: str | None = None   # Zoom: join on behalf of this connected person


class ZoomConnectError(Exception):
    """A plain-language reason Zoom couldn't be connected."""


@dataclass
class BotUpdate:
    """A provider's webhook, turned into our terms."""
    bot_id: str
    status: str | None            # one of notetaker.states, or None when the event doesn't change it
    detail: str | None = None
    ready: bool = False           # the transcript can now be collected
    dedupe_key: str | None = None


@dataclass
class Utterance:
    speaker: str
    start_ms: int
    end_ms: int
    text: str


@dataclass
class BotResult:
    transcript: list[Utterance] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)


class MeetingBot(Protocol):
    name: str

    def create(self, req: BotRequest) -> str: ...
    def cancel(self, bot_id: str) -> None: ...
    def parse_webhook(self, body: bytes, headers: dict[str, str]) -> BotUpdate | None: ...
    def fetch_result(self, bot_id: str) -> BotResult: ...
    def poll(self, bot_id: str) -> BotUpdate | None: ...
    # Zoom sign-ins ("Connect Zoom"): returns {"id": the bot's id for it, "zoom_user_id", "state"}
    def connect_zoom(self, authorization_code: str, redirect_uri: str, metadata: dict) -> dict: ...
    def zoom_state(self, bot_connection_id: str) -> str | None: ...
    def disconnect_zoom(self, bot_connection_id: str) -> None: ...
