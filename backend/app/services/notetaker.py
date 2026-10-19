"""Talks to the separate Notetaker service (see its README on the notetaker branch)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time

import httpx

from app.core.config import settings


class NotetakerError(Exception):
    """A plain-language reason the notetaker couldn't be reached or refused."""


logger = logging.getLogger("app.services.notetaker")

def configured() -> bool:
    return bool(settings.notetaker_url and settings.notetaker_api_key)


def _client() -> httpx.Client:
    return httpx.Client(base_url=settings.notetaker_url.rstrip("/"), timeout=20,
                        headers={"Authorization": f"Bearer {settings.notetaker_api_key}"})


def _detail(r: httpx.Response, fallback: str) -> str:
    """A plain reason for a refused request. The notetaker's own messages are written for people, so its
    "can't book that" answers are passed on; anything else gets the plain fallback (and goes in the log)."""
    if r.status_code == 401:
        return "The notetaker didn't accept BMI Brain's key. An administrator needs to make a new one on the notetaker's admin page (Apps, New key)."
    if r.status_code == 403:
        return "BMI Brain is switched off on the notetaker's admin page. An administrator needs to switch it back on."
    try:
        d = r.json().get("detail")
    except Exception:
        d = None
    if isinstance(d, str) and r.status_code in (409, 422, 429):
        return d
    logger.warning("notetaker refused a request: %s %s", r.status_code, (r.text or "")[:300])
    return fallback


def send_bot(*, meeting_url: str, external_id: str, title: str | None, metadata: dict, join_at=None, end_at=None) -> dict:
    body = {"meeting_url": meeting_url, "external_id": external_id, "title": title, "metadata": metadata}
    if join_at:
        body["join_at"] = join_at.isoformat()
    if end_at:   # holds the notetaker's slot until the meeting ends, so other bookings can't take it
        body["end_at"] = end_at.isoformat()
    try:
        with _client() as c:
            r = c.post("/v1/meetings", json=body)
    except httpx.HTTPError:
        raise NotetakerError("The notetaker can't be reached just now. Please try again in a minute.")
    if r.status_code >= 400:
        raise NotetakerError(_detail(r, "The notetaker couldn't be sent just now. Please try again in a minute."))
    return r.json()


def stop_bot(notetaker_id: str) -> None:
    try:
        with _client() as c:
            c.delete(f"/v1/meetings/{notetaker_id}")
    except httpx.HTTPError:
        raise NotetakerError("The notetaker can't be reached just now. Please try again in a minute.")


def verify(body: bytes, timestamp: str, signature: str, max_age: int = 600) -> bool:
    secret = settings.notetaker_webhook_secret
    if not (secret and timestamp and signature):
        return False
    try:
        if abs(time.time() - int(timestamp)) > max_age:
            return False
    except ValueError:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def check() -> tuple[bool, str]:
    """Can BMI Brain reach the notetaker with its key? Plain words either way (for the Notetaker check)."""
    if not configured():
        return False, "Not connected: the notetaker's address and key haven't been added on the server yet. Ask whoever runs BMI Brain to add them."
    try:
        with _client() as c:
            r = c.get("/v1/capacity")
    except httpx.HTTPError:
        return False, "BMI Brain can't reach the notetaker. Ask whoever runs BMI Brain to check the notetaker's address on the server and that the notetaker is running."
    if r.status_code >= 400:
        return False, _detail(r, "The notetaker answered with a problem. Ask whoever runs the notetaker to look at what went wrong.")
    try:
        free = r.json().get("free")
    except Exception:
        free = None
    if free == 0:
        return False, "Connected, but it's already in as many calls as it can join at once, so new meetings can't be booked right now."
    return True, "Connected and answering" + (f" - room for {free} more call{'s' if free != 1 else ''} right now" if isinstance(free, int) else "")
