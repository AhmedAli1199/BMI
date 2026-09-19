from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
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


def _latest_local_revision() -> str | None:
    """The newest migration file that ships with the currently-running
    code (by filename, e.g. "0013" from "0013_automation_state.py") - not
    a query, just what's on disk in this deployment's own image. Comparing
    this to what's actually applied in the DB (below) answers "did the
    migration I expect actually run" without needing to trust deploy logs,
    which may have already scrolled out of whatever log retention window
    the hosting platform keeps."""
    versions_dir = Path(__file__).resolve().parents[3] / "alembic" / "versions"
    revisions = sorted(p.stem.split("_")[0] for p in versions_dir.glob("*.py") if p.stem[0].isdigit())
    return revisions[-1] if revisions else None


class DbMigrationOut(BaseModel):
    applied_revision: str | None  # what alembic_version actually says in this DB right now
    latest_local_revision: str | None  # the newest migration file shipped in this running image
    up_to_date: bool
    pg_trgm_installed: bool  # needed by CS-004's dedupe scan (migration 0012)
    automation_state_table_exists: bool  # needed by the bounce/OOO scan's cursor (migration 0013)


@router.get("/db-migration", response_model=DbMigrationOut)
def check_db_migration(db: Session = Depends(get_db)) -> DbMigrationOut:
    """Answers "is the database actually on the migration this code
    expects" by reading the DB directly - alembic_version, whether the
    pg_trgm extension is installed, and whether the automation_state table
    exists - rather than relying on deploy-time logs, which may have
    already rolled off whatever retention the hosting platform keeps. Safe
    to call anytime: read-only, no writes, no mutation of anything."""
    applied = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    pg_trgm_installed = bool(
        db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")).scalar()
    )
    automation_state_exists = bool(
        db.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name = 'automation_state'")
        ).scalar()
    )
    latest_local = _latest_local_revision()
    return DbMigrationOut(
        applied_revision=applied,
        latest_local_revision=latest_local,
        up_to_date=applied == latest_local,
        pg_trgm_installed=pg_trgm_installed,
        automation_state_table_exists=automation_state_exists,
    )
