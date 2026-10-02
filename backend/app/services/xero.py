"""Xero - read-only link to BMI's accounting.

Connecting: an admin clicks "Connect Xero" (Settings › Integrations),
signs in to Xero (e.g. with the integration@bmipublishing.co.uk login BMI
set up) and picks the organisation. That's standard OAuth 2.0
authorization-code flow for a Xero "Web app"; we keep only an encrypted
refresh token. Xero rotates the refresh token on every use and expires it
after 60 days unused, so the hourly sync also keeps the connection alive.

Syncing: every sales invoice (Type ACCREC) changed since the last sync is
fetched page by page and upserted into xero_invoices, then matched to the
order register by invoice number. Nothing is ever written to Xero.
"""
from __future__ import annotations

import base64
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import XeroConnection, XeroInvoice
from app.services.outlook import decrypt, encrypt

logger = logging.getLogger("app.services.xero")

AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL = "https://identity.xero.com/connect/token"
CONNECTIONS_URL = "https://api.xero.com/connections"
API = "https://api.xero.com/api.xro/2.0"
PAGE_SIZE = 500


class XeroNotConfigured(Exception):
    pass


class XeroAuthError(Exception):
    """The stored grant no longer works - an admin has to reconnect."""


def is_configured() -> bool:
    return bool(settings.xero_client_id and settings.xero_client_secret)


def redirect_uri() -> str:
    return settings.xero_redirect_uri or f"{settings.app_base_url.rstrip('/')}/api/xero/callback"


def authorize_url(state: str) -> str:
    if not is_configured():
        raise XeroNotConfigured("Xero isn't set up yet - XERO_CLIENT_ID and XERO_CLIENT_SECRET are missing on the server.")
    return str(httpx.URL(AUTHORIZE_URL, params={
        "response_type": "code", "client_id": settings.xero_client_id, "redirect_uri": redirect_uri(),
        "scope": settings.xero_scopes, "state": state,
    }))


def _token(data: dict) -> dict:
    basic = base64.b64encode(f"{settings.xero_client_id}:{settings.xero_client_secret}".encode()).decode()
    resp = httpx.post(TOKEN_URL, data=data, headers={"Authorization": f"Basic {basic}"}, timeout=20)
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code >= 300:
        raise XeroAuthError(body.get("error_description") or body.get("error") or f"Xero sign-in failed ({resp.status_code}).")
    return body


def _store(conn: XeroConnection, body: dict) -> None:
    conn.access_token_enc = encrypt(body["access_token"])
    conn.access_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(body.get("expires_in", 1800)) - 60)
    if body.get("refresh_token"):
        conn.refresh_token_enc = encrypt(body["refresh_token"])
    conn.last_error = None


def complete_sign_in(db: Session, code: str, user_id: uuid.UUID | None) -> XeroConnection:
    """Exchanges the code, picks the organisation that was just authorised
    and replaces any previous connection (one Xero org per app)."""
    body = _token({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri()})
    resp = httpx.get(CONNECTIONS_URL, headers={"Authorization": f"Bearer {body['access_token']}"}, timeout=20)
    resp.raise_for_status()
    tenants = [t for t in resp.json() if t.get("tenantType") == "ORGANISATION"]
    if not tenants:
        raise XeroAuthError("That Xero login has no organisation connected - pick BMI's organisation when Xero asks.")
    # The most recently authorised organisation is the one just chosen.
    tenant = max(tenants, key=lambda t: t.get("updatedDateUtc") or "")
    for old in db.scalars(select(XeroConnection)):
        db.delete(old)
    conn = XeroConnection(id=uuid.uuid4(), tenant_id=tenant["tenantId"], tenant_name=tenant.get("tenantName"),
                          refresh_token_enc="", connected_by_user_id=user_id)
    _store(conn, body)
    db.add(conn)
    db.commit()
    return conn


def connection(db: Session) -> XeroConnection | None:
    return db.scalars(select(XeroConnection).order_by(XeroConnection.connected_at.desc())).first()


def _access_token(db: Session, conn: XeroConnection) -> str:
    if conn.access_token_enc and conn.access_expires_at and conn.access_expires_at > datetime.now(timezone.utc):
        return decrypt(conn.access_token_enc)
    try:
        body = _token({"grant_type": "refresh_token", "refresh_token": decrypt(conn.refresh_token_enc)})
    except XeroAuthError as exc:
        conn.last_error = f"Reconnect needed: {exc}"
        db.commit()
        raise
    _store(conn, body)
    db.commit()
    return body["access_token"]


_MS_DATE = re.compile(r"/Date\((-?\d+)")


def _when(v) -> datetime | None:
    """Xero dates: "/Date(1518685950940+0000)/" or ISO "2026-01-27T00:00:00"."""
    if not v:
        return None
    m = _MS_DATE.search(str(v))
    if m:
        return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _day(v) -> date | None:
    d = _when(v)
    return d.date() if d else None


def number_key(n: str | None) -> str | None:
    return re.sub(r"\s+", "", n).upper() if n and n.strip() else None


def _upsert(db: Session, inv: dict) -> None:
    row = db.scalar(select(XeroInvoice).where(XeroInvoice.xero_id == inv["InvoiceID"]))
    if not row:
        row = XeroInvoice(id=uuid.uuid4(), xero_id=inv["InvoiceID"], status=inv.get("Status", ""))
        db.add(row)
    row.invoice_number = inv.get("InvoiceNumber")
    row.number_key = number_key(inv.get("InvoiceNumber"))
    row.contact_name = (inv.get("Contact") or {}).get("Name")
    row.reference = inv.get("Reference")
    row.status = inv.get("Status", "")
    row.currency = inv.get("CurrencyCode")
    row.issued_on = _day(inv.get("DateString") or inv.get("Date"))
    row.due_on = _day(inv.get("DueDateString") or inv.get("DueDate"))
    row.paid_on = _day(inv.get("FullyPaidOnDate"))
    for attr, key in (("sub_total", "SubTotal"), ("total_tax", "TotalTax"), ("total", "Total"),
                      ("amount_paid", "AmountPaid"), ("amount_due", "AmountDue"), ("amount_credited", "AmountCredited")):
        setattr(row, attr, inv.get(key))
    row.updated_at_xero = _when(inv.get("UpdatedDateUTC"))


def fetch_invoices(token: str, tenant_id: str, since: datetime | None, page: int) -> list[dict]:
    """One page of sales invoices (ACCREC). Separate so tests can stub it."""
    headers = {"Authorization": f"Bearer {token}", "xero-tenant-id": tenant_id, "Accept": "application/json"}
    if since:
        headers["If-Modified-Since"] = since.strftime("%Y-%m-%dT%H:%M:%S")
    start = settings.xero_sync_from
    y, m, d = (int(x) for x in start.split("-"))
    params = {"where": f'Type=="ACCREC" AND Date>=DateTime({y},{m},{d})', "page": page, "pageSize": PAGE_SIZE,
              "summaryOnly": "true"}
    resp = httpx.get(f"{API}/Invoices", headers=headers, params=params, timeout=60)
    if resp.status_code == 401:
        raise XeroAuthError("Xero rejected the connection - reconnect Xero.")
    if resp.status_code == 429:
        raise RuntimeError("Xero rate limit reached - the next hourly sync will carry on.")
    resp.raise_for_status()
    return resp.json().get("Invoices", [])


def sync(db: Session) -> dict:
    """Pulls every sales invoice changed since the last sync. Safe to run
    any time; returns {"invoices": n} or {"skipped": reason}."""
    conn = connection(db)
    if not conn:
        return {"skipped": "Xero isn't connected"}
    started = datetime.now(timezone.utc)
    try:
        token = _access_token(db, conn)
        n, page = 0, 1
        while True:
            batch = fetch_invoices(token, conn.tenant_id, conn.synced_until, page)
            for inv in batch:
                _upsert(db, inv)
            n += len(batch)
            db.commit()
            if len(batch) < PAGE_SIZE:
                break
            page += 1
    except Exception as exc:
        db.rollback()
        conn = connection(db)
        if conn:
            conn.last_error = str(exc)[:500]
            conn.last_sync_at = started
            db.commit()
        logger.warning("xero sync failed: %s", exc)
        raise
    conn.synced_until = started - timedelta(minutes=5)  # overlap so nothing changed mid-sync is missed
    conn.last_sync_at = started
    conn.last_error = None
    db.commit()
    return {"invoices": n}
