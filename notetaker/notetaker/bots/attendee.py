"""Attendee (github.com/attendee-labs/attendee), self-hosted and used unchanged through its REST API."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging

import httpx

from notetaker import states
from notetaker.bots.base import BotRequest, BotResult, BotUpdate, Utterance
from notetaker.config import settings

log = logging.getLogger(__name__)

# Attendee's bot states -> ours
STATE_MAP = {
    "ready": states.SCHEDULED, "scheduled": states.SCHEDULED, "staged": states.SCHEDULED,
    "joining": states.JOINING, "waiting_room": states.WAITING_ROOM,
    "joined_not_recording": states.RECORDING, "joined_recording": states.RECORDING,
    "joined_recording_paused": states.RECORDING, "joined_recording_permission_denied": states.RECORDING,
    "joining_breakout_room": states.RECORDING, "leaving_breakout_room": states.RECORDING,
    "leaving": states.PROCESSING, "post_processing": states.PROCESSING, "ended": states.PROCESSING,
    "fatal_error": states.FAILED,
}
NOT_ADMITTED_SUBTYPES = {"request_to_join_denied", "waiting_room_timeout_exceeded", "meeting_not_started_waiting_for_host"}
FRIENDLY = {
    "request_to_join_denied": "Someone in the call turned the notetaker away.",
    "waiting_room_timeout_exceeded": "Nobody let the notetaker in from the waiting room in time.",
    "meeting_not_started_waiting_for_host": "The host never started the meeting.",
    "meeting_not_found": "The meeting link didn't work.",
    "login_required": "This meeting only lets in signed-in accounts.",
    "unable_to_connect_to_meeting": "The notetaker couldn't connect - the link or its password may be wrong.",
    "auto_leave_silence": "Left after a long silence.",
    "auto_leave_only_participant_in_meeting": "Left once everyone else had gone.",
    "user_requested": "Asked to leave.",
}


def sign(payload: dict, secret_b64: str) -> str:
    """Attendee's signature: HMAC-SHA256 of the canonical JSON, base64."""
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return base64.b64encode(hmac.new(base64.b64decode(secret_b64), body.encode(), hashlib.sha256).digest()).decode()


class AttendeeBot:
    name = "attendee"

    def __init__(self, base_url: str | None = None, api_key: str | None = None, webhook_secret: str | None = None,
                 http: httpx.Client | None = None):
        self.base = (base_url or settings.attendee_url).rstrip("/")
        self.secret = webhook_secret if webhook_secret is not None else settings.attendee_webhook_secret
        self.http = http or httpx.Client(timeout=30, headers={"Authorization": f"Token {api_key or settings.attendee_api_key}",
                                                              "Content-Type": "application/json"})

    def _transcription(self) -> dict:
        if settings.transcription_mode == "gemini":
            # Attendee posts each speaker's audio to us; we transcribe it with Gemini (see api/app.py).
            return {"custom_async_v2": {"headers": {"X-Internal-Token": settings.internal_token}, "form_data": {}}}
        return {"meeting_closed_captions": {"google_meet_language": "en-US", "teams_language": "en-gb"}}

    def create(self, req: BotRequest) -> str:
        body = {
            "meeting_url": req.meeting_url,
            "bot_name": req.bot_name,
            "metadata": {"notetaker_meeting_id": req.meeting_id},
            "transcription_settings": self._transcription(),
            "recording_settings": {"format": "mp3"},
            "webhooks": [{"url": f"{settings.public_url}/hooks/attendee",
                          "triggers": ["bot.state_change", "participant_events.join_leave"]}],
            "automatic_leave_settings": {"waiting_room_timeout_seconds": 600, "silence_timeout_seconds": 600,
                                         "only_participant_in_meeting_timeout_seconds": 60},
        }
        if req.join_at:
            body["join_at"] = req.join_at.isoformat().replace("+00:00", "Z")
        if req.chat_message:
            body["bot_chat_message"] = {"message": req.chat_message}
        if req.dedupe_key:
            body["deduplication_key"] = req.dedupe_key
        r = self.http.post(f"{self.base}/api/v1/bots", json=body)
        r.raise_for_status()
        return r.json()["id"]

    def cancel(self, bot_id: str) -> None:
        r = self.http.get(f"{self.base}/api/v1/bots/{bot_id}")
        state = r.json().get("state") if r.status_code == 200 else None
        if state in ("scheduled", "staged", "ready"):
            self.http.delete(f"{self.base}/api/v1/bots/{bot_id}")
        elif state and state not in ("ended", "fatal_error", "data_deleted"):
            self.http.post(f"{self.base}/api/v1/bots/{bot_id}/leave")

    def parse_webhook(self, body: bytes, headers: dict[str, str]) -> BotUpdate | None:
        payload = json.loads(body)
        if self.secret:
            given = headers.get("x-webhook-signature", "")
            if not hmac.compare_digest(given, sign(payload, self.secret)):
                raise PermissionError("bad signature")
        bot_id = payload.get("bot_id")
        if not bot_id:
            return None
        trigger, data = payload.get("trigger"), payload.get("data") or {}
        key = payload.get("idempotency_key")
        if trigger != "bot.state_change":
            return BotUpdate(bot_id=bot_id, status=None, dedupe_key=key)
        new_state, sub = data.get("new_state"), data.get("event_sub_type")
        status = STATE_MAP.get(new_state)
        if new_state == "fatal_error" or data.get("event_type") == "could_not_join_meeting":
            status = states.NOT_ADMITTED if sub in NOT_ADMITTED_SUBTYPES else states.FAILED
        detail = FRIENDLY.get(sub or "") or (None if status not in (states.FAILED,) else "The notetaker ran into a problem in the call.")
        ready = new_state == "ended" and data.get("event_type") == "post_processing_completed"
        return BotUpdate(bot_id=bot_id, status=status, detail=detail, ready=ready, dedupe_key=key)

    def fetch_result(self, bot_id: str) -> BotResult:
        r = self.http.get(f"{self.base}/api/v1/bots/{bot_id}/transcript")
        r.raise_for_status()
        out: list[Utterance] = []
        for u in r.json():
            text = ((u.get("transcription") or {}).get("transcript") or "").strip()
            if not text:
                continue
            start = int(u.get("timestamp_ms") or 0)
            out.append(Utterance(speaker=u.get("speaker_name") or "Unknown", start_ms=start,
                                 end_ms=start + int(u.get("duration_ms") or 0), text=text))
        out.sort(key=lambda x: x.start_ms)
        people: list[str] = []
        try:
            p = self.http.get(f"{self.base}/api/v1/bots/{bot_id}/participants")
            if p.status_code == 200:
                rows = p.json()
                rows = rows.get("results", rows) if isinstance(rows, dict) else rows
                people = sorted({x.get("name") for x in rows if x.get("name") and not x.get("is_the_bot")})
        except Exception:   # participants are a nice-to-have
            log.warning("Couldn't fetch participants for %s", bot_id)
        if not people:
            people = sorted({u.speaker for u in out})
        return BotResult(transcript=out, participants=people)
