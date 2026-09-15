from __future__ import annotations

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.graph_client import GraphNotConfigured, check_mailbox, decode_app_roles, get_app_token

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

# The five addresses from Clare's WhatsApp message - three sender/noreply
# mailboxes (where bounces land) and two personal reply-to mailboxes
# (where OOO/human replies land). Hardcoded here deliberately: this route
# exists to answer one specific, one-time question, not to be a general
# mailbox-probing tool.
CANDIDATE_MAILBOXES = [
    "noreply@onboardhospitality.com",
    "noreply@thebusinesstravelmag.com",
    "online-editor@sellingtravel.co.uk",
    "kay.fisher@bmipublishing.co.uk",
    "shani.kunar@bmipublishing.co.uk",
]


class MailboxCheckOut(BaseModel):
    email: str
    status: str
    detail: str


class GraphMailboxesOut(BaseModel):
    configured: bool
    granted_app_roles: list[str] = []
    results: list[MailboxCheckOut]


@router.post("/graph-mailboxes", response_model=GraphMailboxesOut)
def check_graph_mailboxes() -> GraphMailboxesOut:
    """Checks whether each of CANDIDATE_MAILBOXES is a real, readable
    mailbox via the Graph app registration's client-credentials
    (GRAPH_TENANT_ID/GRAPH_CLIENT_ID/GRAPH_CLIENT_SECRET env vars). Never
    returns or logs the credentials themselves - only a per-mailbox
    ok/no_mailbox/access_denied/auth_error/error verdict, so this is safe
    to call and share the response of."""
    try:
        token = get_app_token()
    except GraphNotConfigured as exc:
        detail = str(exc)
        return GraphMailboxesOut(
            configured=False,
            results=[MailboxCheckOut(email=addr, status="not_configured", detail=detail) for addr in CANDIDATE_MAILBOXES],
        )
    except httpx.HTTPStatusError as exc:
        detail = f"Azure AD rejected the app credentials: {exc.response.status_code} {exc.response.text[:200]}"
        return GraphMailboxesOut(
            configured=True,
            results=[MailboxCheckOut(email=addr, status="auth_error", detail=detail) for addr in CANDIDATE_MAILBOXES],
        )

    results = [check_mailbox(token, email) for email in CANDIDATE_MAILBOXES]
    return GraphMailboxesOut(
        configured=True,
        granted_app_roles=decode_app_roles(token),
        results=[MailboxCheckOut(email=r.email, status=r.status, detail=r.detail) for r in results],
    )
