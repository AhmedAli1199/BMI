"""Talks to the separate Notetaker service (see its README on the notetaker branch)."""
from __future__ import annotations

import hashlib
import hmac
import time

import httpx

from app.core.config import settings


class NotetakerError(Exception):
    """A plain-language reason the notetaker couldn't be reached or refused."""


def configured() -> bool:
    return bool(settings.notetaker_url and settings.notetaker_api_key)


def _client() -> httpx.Client:
    return httpx.Client(base_url=settings.notetaker_url.rstrip("/"), timeout=20,
                        headers={"Authorization": f"Bearer {settings.notetaker_api_key}"})


def _detail(r: httpx.Response, fallback: str) -> str:
    try:
        d = r.json().get("detail")
        return d if isinstance(d, str) and r.status_code == 422 else fallback
    except Exception:
        return fallback


def send_bot(*, meeting_url: str, external_id: str, title: str | None, metadata: dict) -> dict:
    try:
        with _client() as c:
            r = c.post("/v1/meetings", json={"meeting_url": meeting_url, "external_id": external_id, "title": title, "metadata": metadata})
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
