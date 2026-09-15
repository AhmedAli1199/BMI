"""Thin Microsoft Graph client-credentials wrapper - app-only auth, no
per-user login, per CONTEXT.md's plan. Only what's needed today: getting a
token and checking whether a given mailbox is actually readable. The real
mailbox-scanning logic (reading bounces/OOO replies for CS-001/002/003)
is a separate, later piece - this exists first so
/api/diagnostics/graph-mailboxes can answer "is this address a real,
readable mailbox" before anything is built on top of it.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphNotConfigured(Exception):
    pass


def _require_config() -> None:
    if not (settings.graph_tenant_id and settings.graph_client_id and settings.graph_client_secret):
        raise GraphNotConfigured(
            "GRAPH_TENANT_ID / GRAPH_CLIENT_ID / GRAPH_CLIENT_SECRET are not all set"
        )


def get_app_token() -> str:
    """Client-credentials token for application permissions (e.g.
    Mail.Read). Raises GraphNotConfigured if the three env vars aren't
    set, or httpx.HTTPStatusError if Azure AD rejects the credentials -
    both are caught and reported per-mailbox by the diagnostics route
    rather than surfacing as a 500."""
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
    return resp.json()["access_token"]


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
        return MailboxCheckResult(
            email, "access_denied",
            "Mailbox exists but the app registration isn't permitted to read it "
            "(check the Exchange Application Access Policy covers this address)",
        )
    if resp.status_code == 401:
        return MailboxCheckResult(email, "auth_error", "Token rejected - check Mail.Read admin consent")
    return MailboxCheckResult(email, "error", f"Unexpected Graph response: {resp.status_code} {resp.text[:200]}")
