"""Brevo, where BMI's newsletters are sent from - the few calls BMI Brain makes (Brevo API v3).

The key is the BREVO_API_KEY environment variable on the server, never a screen setting: it gives full control of
BMI's Brevo account. Every error is a BrevoError with a plain sentence, so callers can show it as it is.
"""
from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote

import httpx

from app.core.config import settings

logger = logging.getLogger("app.services.brevo")

BASE = "https://api.brevo.com/v3"
MAX_PAGES = 50


class BrevoError(Exception):
    """Brevo couldn't be reached or refused - the message is a plain sentence."""


def configured() -> bool:
    return bool((settings.brevo_api_key or "").strip())


def _call(method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> httpx.Response:
    if not configured():
        raise BrevoError("Brevo isn't connected yet: its key needs adding on the server.")
    try:
        r = httpx.request(method, BASE + path, params=params, json=json, timeout=30,
                          headers={"api-key": settings.brevo_api_key.strip(), "accept": "application/json"})
    except httpx.HTTPError as exc:
        logger.warning("brevo: %s %s failed (%s)", method, path, type(exc).__name__)
        raise BrevoError("Brevo couldn't be reached just now. It will be tried again later.") from exc
    if r.status_code in (401, 403):
        raise BrevoError("Brevo didn't accept BMI Brain's key. Check the key on the server, and that the server is on Brevo's authorised IP list.")
    if r.status_code == 429:
        raise BrevoError("Brevo is asking us to slow down. It will be tried again later.")
    return r


def _iso(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%S.") + f"{when.microsecond // 1000:03d}Z"


def update_contact(email: str, *, blacklist: bool = False, remove_from: list[int] | None = None) -> bool:
    """Unsubscribes someone from every Brevo email (blacklist) or takes them off some lists. False when Brevo doesn't
    have them at all - nothing to do there."""
    body: dict = {}
    if blacklist:
        body["emailBlacklisted"] = True
    if remove_from:
        body["unlinkListIds"] = [int(x) for x in remove_from]
    if not body:
        return True
    r = _call("PUT", f"/contacts/{quote(email.strip(), safe='')}", json=body)
    if r.status_code == 404:
        return False
    if r.status_code >= 400:
        logger.warning("brevo: update of a contact refused (%s)", r.status_code)
        raise BrevoError("Brevo didn't accept the change, so they're not unsubscribed there yet.")
    return True


def contacts_changed_since(since: datetime, *, offset: int = 0) -> tuple[list[dict], int]:
    """(contacts changed since, the offset to carry on from next time - 0 when all were read)."""
    out: list[dict] = []
    for _ in range(MAX_PAGES):
        r = _call("GET", "/contacts", params={"modifiedSince": _iso(since), "limit": 1000, "offset": offset, "sort": "asc"})
        if r.status_code >= 400:
            raise BrevoError("Brevo didn't send the list of changed contacts.")
        page = r.json().get("contacts") or []
        out += page
        offset += len(page)
        if len(page) < 1000:
            return out, 0
    return out, offset


def sent_campaigns(start: datetime, end: datetime) -> list[dict]:
    """Email campaigns sent between start and end, with their HTML."""
    out: list[dict] = []
    offset = 0
    for _ in range(MAX_PAGES):
        r = _call("GET", "/emailCampaigns", params={"status": "sent", "startDate": _iso(start), "endDate": _iso(end),
                                                    "limit": 50, "offset": offset})
        if r.status_code >= 400:
            raise BrevoError("Brevo didn't send the list of newsletters.")
        page = r.json().get("campaigns") or []
        out += page
        offset += len(page)
        if len(page) < 50:
            break
    return out


def lists() -> list[dict]:
    """BMI's Brevo lists: {id, name, folder, people}."""
    out: list[dict] = []
    offset = 0
    for _ in range(MAX_PAGES):
        r = _call("GET", "/contacts/lists", params={"limit": 50, "offset": offset})
        if r.status_code >= 400:
            raise BrevoError("Brevo didn't send its lists.")
        page = r.json().get("lists") or []
        out += [{"id": x.get("id"), "name": x.get("name"), "folder": x.get("folderId"), "people": x.get("uniqueSubscribers")} for x in page]
        offset += len(page)
        if len(page) < 50:
            break
    return out
