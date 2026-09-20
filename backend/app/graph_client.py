"""Thin Microsoft Graph client-credentials wrapper - app-only auth, no
per-user login, per CONTEXT.md's plan. Covers getting a (cached,
auto-refreshing) token, checking whether a given mailbox is actually
readable, and reading messages out of one for the real mailbox-scanning
jobs (CS-001/002/003 - see app/automations/bounce_handling.py).

Token handling, deliberately boring/standard: the access token is an
opaque bearer credential for our own app-only identity (not tied to any
one person), so - per standard OAuth client-credentials practice - it's
kept in-process memory only (never logged, never written to the DB or
disk), reused across calls until it's close to expiry, and refreshed
automatically rather than fetched fresh on every request (fetching a new
token per message read would be needless load on Azure AD and slower for
no benefit). It never survives a container restart by design - re-fetched
lazily on first use after every restart/deploy, same as any other
in-memory cache.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger("app.graph_client")

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Refresh this many seconds before the token's real expiry, so a slow
# request started just before expiry doesn't get rejected mid-flight -
# standard practice for any cached bearer token, not Graph-specific.
_REFRESH_BUFFER_SECONDS = 120


class GraphNotConfigured(Exception):
    pass


def _require_config() -> None:
    if not (settings.graph_tenant_id and settings.graph_client_id and settings.graph_client_secret):
        raise GraphNotConfigured(
            "GRAPH_TENANT_ID / GRAPH_CLIENT_ID / GRAPH_CLIENT_SECRET are not all set"
        )


def _fetch_token() -> tuple[str, float]:
    """One real network call to Azure AD. Returns (token, expires_in_seconds).
    Never called directly outside this module - everything else goes
    through the cache below."""
    _require_config()
    url = f"https://login.microsoftonline.com/{settings.graph_tenant_id}/oauth2/v2.0/token"
    resp = httpx.post(
        url,
        data={
            "client_id": settings.graph_client_id,
            "client_secret": settings.graph_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    return body["access_token"], float(body.get("expires_in", 3600))


class _TokenCache:
    """Process-wide, thread-safe cache for the single app-only Graph token.
    A lock guards it because the scheduler and any concurrent API request
    (e.g. the diagnostics route) share one process and could both try to
    refresh at once - without the lock, both would fire a redundant token
    request and there'd be a small window where two threads read/write
    `_token`/`_expires_at` inconsistently."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0.0  # time.monotonic() timestamp

    def get(self) -> str:
        with self._lock:
            if self._token and time.monotonic() < self._expires_at - _REFRESH_BUFFER_SECONDS:
                return self._token
            logger.info("Fetching a new Microsoft Graph app token (none cached, or close to expiry).")
            token, expires_in = _fetch_token()
            self._token = token
            self._expires_at = time.monotonic() + expires_in
            return token

    def invalidate(self) -> None:
        """Drops the cached token so the next get() fetches a fresh one -
        used after a 401, in case Azure AD revoked it early (e.g. a secret
        rotation) even though our local clock thought it was still valid."""
        with self._lock:
            self._token = None
            self._expires_at = 0.0


_token_cache = _TokenCache()


def get_app_token() -> str:
    """Client-credentials token for application permissions (e.g.
    Mail.Read) - cached and auto-refreshed, see _TokenCache above. Raises
    GraphNotConfigured if the three env vars aren't set, or
    httpx.HTTPStatusError if Azure AD rejects the credentials - both are
    caught and reported per-mailbox by the diagnostics route rather than
    surfacing as a 500."""
    return _token_cache.get()


def decode_app_roles(token: str) -> list[str]:
    """Reads the "roles" claim out of the access token's payload - the
    application permissions (e.g. "Mail.Read") Azure AD actually put on
    this token, as granted (with admin consent) on the app registration.
    No signature verification - we don't need to trust the token's
    integrity for this, only to read what Azure AD itself already put in
    it moments ago; this is purely diagnostic, never used for auth
    decisions. An empty list here (not an absent "Mail.Read") means the
    app has NO application permissions at all - the most common reason
    every single mailbox comes back access_denied at once, as opposed to
    a per-mailbox Application Access Policy problem."""
    try:
        payload_segment = token.split(".")[1]
        padded = payload_segment + "=" * (-len(payload_segment) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload.get("roles", [])
    except Exception:
        return []


@dataclass(frozen=True)
class MailboxCheckResult:
    email: str
    status: str  # "ok" | "no_mailbox" | "access_denied" | "auth_error" | "not_configured" | "error"
    detail: str


def check_mailbox(token: str, email: str) -> MailboxCheckResult:
    """Reads a single message from the mailbox's inbox - the actual
    operation CS-001/002's real scan needs, so a pass here means the scan
    would genuinely work, not just that the address exists."""
    try:
        resp = httpx.get(
            f"{GRAPH_BASE}/users/{email}/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"$top": "1", "$select": "id"},
            timeout=15,
        )
    except httpx.HTTPError as e:
        return MailboxCheckResult(email, "error", f"Request failed: {e}")

    if resp.status_code == 200:
        return MailboxCheckResult(email, "ok", "Inbox read succeeded")
    if resp.status_code == 404:
        return MailboxCheckResult(email, "no_mailbox", "Graph reports no mailbox at this address")
    if resp.status_code == 403:
        graph_code = None
        graph_message = None
        try:
            err = resp.json().get("error", {})
            graph_code = err.get("code")
            graph_message = err.get("message")
        except Exception:
            pass
        return MailboxCheckResult(
            email, "access_denied",
            f"Mailbox exists but the app isn't permitted to read it - Graph says "
            f"{graph_code!r}: {graph_message!r}",
        )
    if resp.status_code == 401:
        return MailboxCheckResult(email, "auth_error", "Token rejected - check Mail.Read admin consent")
    return MailboxCheckResult(email, "error", f"Unexpected Graph response: {resp.status_code} {resp.text[:200]}")


# Fields the bounce/OOO scan and the email-summary scan actually read (see
# mail_parsing.py) - kept minimal rather than the default "everything",
# since a mailbox can easily hold large HTML bodies and there's no reason
# to pull attachments, categories, etc. over the wire for a job that never
# opens one. ccRecipients is here so email_summary.py can drop anything
# with too many people on a thread (a group thread, not a 1:1 conversation)
# without a second round trip.
_MESSAGE_SELECT = (
    "id,internetMessageId,subject,from,toRecipients,ccRecipients,receivedDateTime,"
    "bodyPreview,body,internetMessageHeaders,conversationId"
)

# Plain-text bodies are dramatically easier (and safer) to run heuristics
# and an LLM prompt over than Graph's default HTML - no tag-stripping, no
# risk of the classification prompt choking on markup.
_TEXT_BODY_PREFERENCE = 'outlook.body-content-type="text"'


class GraphRequestError(Exception):
    """Raised for any non-2xx Graph response that isn't the "expected"
    auth failure handled by the retry-once logic below - callers (the scan
    job) catch this per-mailbox so one bad mailbox can't abort the whole
    run."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _graph_get(url: str, params: dict | None = None, *, extra_headers: dict | None = None) -> httpx.Response:
    """One Graph GET with the current cached token, transparently retried
    exactly once after invalidating the token cache on a 401 - this is
    what "get a new one when it expires" actually means in practice: the
    cache's own expiry math should always refresh in time, but this is the
    cheap, standard belt-and-braces fallback for a token that Azure AD
    rejects early (secret rotated, app disabled, clock drift) rather than
    silently failing the whole scan until the next restart."""
    def _headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}", **(extra_headers or {})}

    token = get_app_token()
    try:
        resp = httpx.get(url, headers=_headers(token), params=params, timeout=30)
        if resp.status_code == 401:
            logger.warning("Graph returned 401 on a cached token - invalidating and retrying once.")
            _token_cache.invalidate()
            token = get_app_token()
            resp = httpx.get(url, headers=_headers(token), params=params, timeout=30)
    except httpx.HTTPError as exc:
        raise GraphRequestError(0, f"Request failed: {exc}") from exc
    if resp.status_code >= 400:
        detail = resp.text[:500]
        try:
            err = resp.json().get("error", {})
            detail = f"{err.get('code')}: {err.get('message')}"
        except Exception:
            pass
        raise GraphRequestError(resp.status_code, detail)
    return resp


def list_messages_since(mailbox: str, since_iso: str, *, top: int = 50, max_pages: int = 10) -> list[dict]:
    """Every message in `mailbox`'s inbox received at or after `since_iso`
    (an ISO-8601 UTC timestamp), oldest first, plain-text bodies. Follows
    Graph's @odata.nextLink for pagination, capped at `max_pages` (each up
    to `top` messages) so one very backed-up mailbox can't turn a single
    scan run into an unbounded loop - if a mailbox is that far behind, the
    next run's cursor picks up where this one left off.

    Raises GraphRequestError (never httpx's own exception types) on
    failure, so callers only need to catch one thing."""
    url = f"{GRAPH_BASE}/users/{mailbox}/mailFolders/inbox/messages"
    params = {
        "$filter": f"receivedDateTime ge {since_iso}",
        "$select": _MESSAGE_SELECT,
        "$orderby": "receivedDateTime asc",
        "$top": str(top),
    }

    messages: list[dict] = []
    for _ in range(max_pages):
        resp = _graph_get(url, params, extra_headers={"Prefer": _TEXT_BODY_PREFERENCE})
        body = resp.json()
        messages.extend(body.get("value", []))

        next_link = body.get("@odata.nextLink")
        if not next_link:
            break
        url, params = next_link, None  # nextLink already carries the query string

    return messages
