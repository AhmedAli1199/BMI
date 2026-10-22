"""Attendee (github.com/attendee-labs/attendee), self-hosted and used unchanged through its REST API."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging

import httpx

from notetaker import engine, states
from notetaker.bots.base import BotRequest, BotResult, BotUpdate, Utterance, ZoomConnectError
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
    "authorized_user_not_in_meeting_timeout_exceeded": "Zoom only lets the notetaker in once the person it joins for is in the call, and they didn't join in time.",
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
        self._secret, self._key = webhook_secret, api_key
        self.http = http or httpx.Client(timeout=30, headers={"Content-Type": "application/json"},
                                         event_hooks={"request": [self._auth]})

    @property
    def secret(self) -> str:
        return self._secret if self._secret is not None else engine.webhook_secret()

    def _auth(self, request: httpx.Request) -> None:
        # read on every call, so new credentials from the bootstrap are picked up without a restart. A call for an
        # app with its own project (Zoom keys of its own, see deploy/attendee_sync.py) brings that project's key.
        if "authorization" not in request.headers:
            request.headers["Authorization"] = f"Token {self._key or engine.api_key()}"

    @staticmethod
    def _h(key: str | None) -> dict:
        return {"Authorization": f"Token {key}"} if key else {}

    def check(self) -> tuple[bool, str]:
        """Is the bot engine reachable and accepting our key? For the console's set-up checklist."""
        try:
            r = self.http.get(f"{self.base}/api/v1/bots", params={"page_size": 1})
        except httpx.HTTPError:
            return False, "The meeting bot isn't reachable yet. If you've just deployed, give it a minute."
        if r.status_code in (401, 403):
            return False, "The meeting bot refused our key. Redeploy so the set-up step runs again."
        return (r.status_code < 400), ("Connected" if r.status_code < 400 else "The meeting bot answered with an error.")

    def _transcription(self, meeting_id: str) -> dict:
        if settings.transcription_mode == "gemini":
            # Attendee posts each speaker's audio to us; we transcribe it with that app's own Gemini key (api/app.py).
            return {"custom_async_v2": {"headers": {"X-Internal-Token": settings.internal_token}, "form_data": {"meeting_id": meeting_id}}}
        return {"meeting_closed_captions": {"google_meet_language": "en-US", "teams_language": "en-gb", "zoom_language": "English"}}

    def create(self, req: BotRequest) -> str:
        body = {
            "meeting_url": req.meeting_url,
            "bot_name": req.bot_name,
            "metadata": {"notetaker_meeting_id": req.meeting_id},
            "transcription_settings": self._transcription(req.meeting_id),
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
        if req.zoom_user_id:
            # Zoom lets a notetaker in only "on behalf of" a signed-in person who's in the call; it waits up to
            # 10 minutes for them to join.
            body["zoom_settings"] = {"onbehalf_token": {"zoom_oauth_connection_user_id": req.zoom_user_id}}
            body["automatic_leave_settings"]["authorized_user_not_in_meeting_timeout_seconds"] = 600
        r = self.http.post(f"{self.base}/api/v1/bots", json=body, headers=self._h(req.bot_key))
        r.raise_for_status()
        return r.json()["id"]

    def cancel(self, bot_id: str, key: str | None = None) -> None:
        h = self._h(key)
        r = self.http.get(f"{self.base}/api/v1/bots/{bot_id}", headers=h)
        state = r.json().get("state") if r.status_code == 200 else None
        if state in ("scheduled", "staged", "ready"):
            self.http.delete(f"{self.base}/api/v1/bots/{bot_id}", headers=h)
        elif state and state not in ("ended", "fatal_error", "data_deleted"):
            self.http.post(f"{self.base}/api/v1/bots/{bot_id}/leave", headers=h)

    def parse_webhook(self, body: bytes, headers: dict[str, str], secrets: list[str] | None = None) -> BotUpdate | None:
        """secrets: the webhook secrets of apps with their own project, tried after the main one."""
        payload = json.loads(body)
        candidates = [x for x in [self.secret, *(secrets or [])] if x]
        if candidates:
            given = headers.get("x-webhook-signature", "")
            if not any(hmac.compare_digest(given, sign(payload, sec)) for sec in candidates):
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

    def poll(self, bot_id: str, key: str | None = None) -> BotUpdate | None:
        """Ask Attendee where the bot is now - the safety net if one of its webhooks never arrived."""
        r = self.http.get(f"{self.base}/api/v1/bots/{bot_id}", headers=self._h(key))
        if r.status_code != 200:
            return None
        bot = r.json()
        state = bot.get("state")
        last = (bot.get("events") or [{}])[-1] if bot.get("events") else {}
        sub = last.get("sub_type")
        status = STATE_MAP.get(state)
        if state == "fatal_error" or last.get("type") == "could_not_join_meeting":
            status = states.NOT_ADMITTED if sub in NOT_ADMITTED_SUBTYPES else states.FAILED
        detail = FRIENDLY.get(sub or "") or ("The notetaker ran into a problem in the call." if status == states.FAILED else None)
        return BotUpdate(bot_id=bot_id, status=status, detail=detail, ready=state == "ended")

    # ---- Zoom sign-ins ---------------------------------------------------------------------------------

    def connect_zoom(self, authorization_code: str, redirect_uri: str, metadata: dict, key: str | None = None) -> dict:
        try:
            r = self.http.post(f"{self.base}/api/v1/zoom_oauth_connections", headers=self._h(key), json={
                "authorization_code": authorization_code, "redirect_uri": redirect_uri, "metadata": metadata,
                "is_local_recording_token_supported": False, "is_onbehalf_token_supported": True})
        except httpx.HTTPError:
            raise ZoomConnectError("The notetaker couldn't reach Zoom just now. Please try again in a minute.")
        if r.status_code >= 400:
            text = r.text or ""
            log.warning("Connecting Zoom failed: %s %s", r.status_code, text[:300])
            if "missing the following required scopes" in text:
                raise ZoomConnectError("The Zoom app is missing a permission. The Zoom app needs 'View a user' and "
                                       "'View a user's token' under Scopes - ask whoever set up the Zoom app.")
            if "No Zoom OAuth App" in text:
                raise ZoomConnectError("Zoom isn't set up for this app yet. Ask whoever runs the notetaker to add its Zoom keys (Apps, Edit).")
            if "not active" in text:
                raise ZoomConnectError("That Zoom account isn't active. Sign in to Zoom once to activate it, then try again.")
            raise ZoomConnectError("Zoom didn't accept the sign-in. Please try connecting again.")
        c = r.json()
        return {"id": c["id"], "zoom_user_id": c["user_id"], "state": c.get("state") or "connected"}

    def zoom_state(self, bot_connection_id: str, key: str | None = None) -> str | None:
        r = self.http.get(f"{self.base}/api/v1/zoom_oauth_connections/{bot_connection_id}", headers=self._h(key))
        if r.status_code == 404:
            return "disconnected"
        return r.json().get("state") if r.status_code == 200 else None

    def disconnect_zoom(self, bot_connection_id: str, key: str | None = None) -> None:
        r = self.http.delete(f"{self.base}/api/v1/zoom_oauth_connections/{bot_connection_id}", headers=self._h(key))
        if r.status_code >= 400 and r.status_code != 404:
            log.warning("Disconnecting Zoom failed: %s %s", r.status_code, (r.text or "")[:300])

    def fetch_result(self, bot_id: str, key: str | None = None) -> BotResult:
        h = self._h(key)
        r = self.http.get(f"{self.base}/api/v1/bots/{bot_id}/transcript", headers=h)
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
            p = self.http.get(f"{self.base}/api/v1/bots/{bot_id}/participants", headers=h)
            if p.status_code == 200:
                rows = p.json()
                rows = rows.get("results", rows) if isinstance(rows, dict) else rows
                people = sorted({x.get("name") for x in rows if x.get("name") and not x.get("is_the_bot")})
        except Exception:   # participants are a nice-to-have
            log.warning("Couldn't fetch participants for %s", bot_id)
        if not people:
            people = sorted({u.speaker for u in out})
        return BotResult(transcript=out, participants=people)
