"""Zoom's OAuth and the calls the notetaker makes for each connected person (README "Zoom").

The notetaker holds each person's Zoom sign-in itself (refresh token, encrypted), using the app's own Zoom keys:
- connect: swap the code Zoom sent back for tokens, check the scopes, read who it is (GET /v2/users/me);
- before each Zoom call: get a fresh "on behalf of" token for that meeting (GET /v2/users/me/token?type=onbehalf),
  which the meeting bot asks us for (callback_settings.zoom_tokens_url);
- disconnect: revoke the token at Zoom (POST /oauth/revoke), then forget it;
- Zoom's own "app removed" notice (app_deauthorized) arrives at /hooks/zoom/<app>, checked with x-zm-signature.

Zoom rotates the refresh token on every refresh, so the new one is saved each time.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time

import httpx

log = logging.getLogger(__name__)

OAUTH = "https://zoom.us/oauth"
API = "https://api.zoom.us/v2"
SCOPES = {"user:read:user", "user:read:token"}


class ZoomAuthError(Exception):
    """The person's Zoom sign-in no longer works (they removed the app, or it was revoked) - plain words."""


class ZoomCallError(Exception):
    """Zoom couldn't be reached, or refused for another reason - plain words."""


def _http() -> httpx.Client:
    return httpx.Client(timeout=20)


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """-> {"access_token", "refresh_token", "scope", ...}"""
    try:
        with _http() as h:
            r = h.post(f"{OAUTH}/token", auth=(client_id, client_secret),
                       data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri})
    except httpx.HTTPError:
        raise ZoomCallError("Zoom couldn't be reached just now. Please try connecting again in a minute.")
    if r.status_code != 200:
        log.warning("Zoom code exchange refused: %s %s", r.status_code, r.text[:300])
        raise ZoomCallError("Zoom didn't accept the sign-in. Please try connecting again.")
    tokens = r.json()
    missing = SCOPES - set((tokens.get("scope") or "").split())
    if missing:
        raise ZoomCallError("The Zoom app is missing a permission. It needs 'View a user' and 'View a user's token' "
                            "under Scopes - ask whoever set up the Zoom app.")
    return tokens


def me(access_token: str) -> dict:
    try:
        with _http() as h:
            r = h.get(f"{API}/users/me", headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError:
        raise ZoomCallError("Zoom couldn't be reached just now. Please try again in a minute.")
    if r.status_code != 200:
        raise ZoomCallError("Zoom didn't say who the account belongs to. Please try connecting again.")
    u = r.json()
    if u.get("status") and u["status"] != "active":
        raise ZoomCallError("That Zoom account isn't active. Sign in to Zoom once to activate it, then try again.")
    return u


def refresh(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """-> new tokens (with a new refresh token). ZoomAuthError if the sign-in no longer works."""
    try:
        with _http() as h:
            r = h.post(f"{OAUTH}/token", auth=(client_id, client_secret),
                       data={"grant_type": "refresh_token", "refresh_token": refresh_token})
    except httpx.HTTPError:
        raise ZoomCallError("Zoom couldn't be reached just now.")
    if r.status_code in (400, 401):
        raise ZoomAuthError("Zoom says this person's sign-in no longer works. They need to press Connect Zoom again.")
    if r.status_code != 200:
        raise ZoomCallError("Zoom refused to refresh the sign-in just now.")
    return r.json()


def meeting_id_from(url: str) -> str | None:
    """The numeric meeting ID in a Zoom join link (…/j/81234567890?pwd=…, or /w/, /s/)."""
    m = re.search(r"/(?:j|w|s|wc/join)/(\d{9,12})", url or "")
    return m.group(1) if m else None


def onbehalf_token(access_token: str, meeting_id: str) -> str:
    try:
        with _http() as h:
            r = h.get(f"{API}/users/me/token", params={"type": "onbehalf", "meeting_id": meeting_id},
                      headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError:
        raise ZoomCallError("Zoom couldn't be reached just now.")
    if r.status_code in (401, 403):
        raise ZoomAuthError("Zoom refused the sign-in for this meeting.")
    if r.status_code != 200 or not r.json().get("token"):
        raise ZoomCallError(f"Zoom didn't give a token for this meeting ({r.status_code}).")
    return r.json()["token"]


def revoke(client_id: str, client_secret: str, token: str) -> None:
    """Revoke at Zoom (the access and refresh tokens both stop working). Never raises - disconnecting goes ahead."""
    try:
        with _http() as h:
            r = h.post(f"{OAUTH}/revoke", auth=(client_id, client_secret), params={"token": token})
        if r.status_code >= 400:
            log.warning("Zoom revoke refused: %s %s", r.status_code, r.text[:200])
    except httpx.HTTPError:
        log.warning("Couldn't reach Zoom to revoke a token", exc_info=True)


# ---- Zoom's webhooks (app_deauthorized) ---------------------------------------------------------------

def signature_ok(secret_token: str, body: bytes, timestamp: str, signature: str, max_age: int = 300) -> bool:
    """x-zm-signature = "v0=" + HMAC-SHA256(secret token, "v0:{timestamp}:{body}")."""
    if not (secret_token and timestamp and signature):
        return False
    try:
        if abs(time.time() - int(timestamp)) > max_age:
            return False
    except ValueError:
        return False
    expected = "v0=" + hmac.new(secret_token.encode(), f"v0:{timestamp}:".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def url_validation(secret_token: str, plain_token: str) -> dict:
    """Zoom's check when the event address is saved (endpoint.url_validation)."""
    return {"plainToken": plain_token,
            "encryptedToken": hmac.new(secret_token.encode(), plain_token.encode(), hashlib.sha256).hexdigest()}
