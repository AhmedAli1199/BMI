"""Xero - read-only link to BMI's accounting.

Connecting: an admin clicks "Connect Xero" (Settings › Integrations),
signs in to Xero (e.g. with the integration@bmipublishing.co.uk login BMI
set up) and picks the organisation. That's standard OAuth 2.0
authorization-code flow for a Xero "Web app"; we keep only an encrypted
refresh token. Xero rotates the refresh token on every use and expires it
after 60 days unused, so the hourly sync also keeps the connection alive.

Alternatively (webhook mode): when XERO_TOKEN_WEBHOOK_URL and XERO_TENANT_ID
are set, an n8n workflow keeps the Xero grant alive and the app just asks
it for a fresh access token (cached until it expires). No sign-in, client
id or secret is needed here in that mode.

Syncing: every sales invoice (Type ACCREC) changed since the last sync is
fetched page by page and upserted into xero_invoices, then matched to the
order register by invoice number. Nothing is ever written to Xero.
"""
from __future__ import annotations

import base64
import logging
import re
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import XeroConnection, XeroInvoice
from app.sales.invoice_numbers import canonical, canonical_sql, find_invoice
from app.services.outlook import decrypt, encrypt

logger = logging.getLogger("app.services.xero")

AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL = "https://identity.xero.com/connect/token"
CONNECTIONS_URL = "https://api.xero.com/connections"
API = "https://api.xero.com/api.xro/2.0"
PAGE_SIZE = 100  # Xero returns 100 per page when line items are included


class XeroNotConfigured(Exception):
    pass


class XeroAuthError(Exception):
    """The stored grant no longer works - an admin has to reconnect."""


def webhook_mode() -> bool:
    """True when tokens come from the n8n workflow instead of an in-app sign-in."""
    return bool(settings.xero_token_webhook_url.strip() and settings.xero_tenant_id.strip())


def is_configured() -> bool:
    return webhook_mode() or bool(settings.xero_client_id and settings.xero_client_secret)


def redirect_uri() -> str:
    return settings.xero_redirect_uri or f"{settings.app_base_url.rstrip('/')}/api/xero/callback"


def authorize_url(state: str) -> str:
    if webhook_mode():
        raise XeroNotConfigured("Xero is linked through the n8n token workflow, so there's nothing to sign in to here.")
    if not (settings.xero_client_id and settings.xero_client_secret):
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


def _webhook_token() -> dict:
    """Asks the n8n workflow for a fresh access token. Error messages never
    include the address or the token."""
    url = settings.xero_token_webhook_url.strip()
    if not url.lower().startswith("https://"):
        raise XeroAuthError("The Xero token webhook address must start with https://.")
    headers = {}
    if settings.xero_token_webhook_secret:
        headers[settings.xero_token_webhook_header or "Authorization"] = settings.xero_token_webhook_secret
    try:
        resp = httpx.get(url, headers=headers, timeout=60)
    except httpx.HTTPError as exc:
        raise XeroAuthError(f"Couldn't reach the n8n token workflow ({exc.__class__.__name__}).") from None
    if resp.status_code >= 300:
        raise XeroAuthError(f"The n8n token workflow answered {resp.status_code} - check that it is active and that the production address (not the test one) is used.")
    try:
        body = resp.json()
    except ValueError:
        body = None
    if isinstance(body, list):
        body = body[0] if body else None
    token = body.get("access_token") if isinstance(body, dict) else None
    if not token:
        raise XeroAuthError("The n8n token workflow didn't return an access token - check its last run in n8n.")
    try:
        expires_in = int(body.get("expires_in") or 1800)
    except (TypeError, ValueError):
        expires_in = 1800
    return {"access_token": token, "expires_in": expires_in}


def ensure_webhook_connection(db: Session) -> XeroConnection:
    """In webhook mode there is no sign-in to create the connection row, so
    make sure one exists for the configured organisation (it also holds the
    sync cursor, last sync time and last error)."""
    tenant = settings.xero_tenant_id.strip()
    conn = connection(db)
    if conn is None:
        conn = XeroConnection(id=uuid.uuid4(), tenant_id=tenant, tenant_name=settings.xero_tenant_name or None, refresh_token_enc="")
        db.add(conn)
    else:
        if conn.tenant_id != tenant:  # pointed at a different organisation: start its history afresh
            conn.tenant_id, conn.synced_until, conn.access_token_enc, conn.access_expires_at = tenant, None, None, None
        conn.refresh_token_enc = ""
        conn.tenant_name = settings.xero_tenant_name or conn.tenant_name
    db.commit()
    return conn


def connection(db: Session) -> XeroConnection | None:
    return db.scalars(select(XeroConnection).order_by(XeroConnection.connected_at.desc())).first()


def _access_token(db: Session, conn: XeroConnection) -> str:
    if conn.access_token_enc and conn.access_expires_at and conn.access_expires_at > datetime.now(timezone.utc):
        return decrypt(conn.access_token_enc)
    if webhook_mode():
        try:
            body = _webhook_token()
        except XeroAuthError as exc:
            conn.last_error = str(exc)[:500]
            db.commit()
            raise
        _store(conn, body)
        db.commit()
        return body["access_token"]
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
    """How invoice numbers are compared - see app/sales/invoice_numbers.py."""
    return canonical(n)


def _upsert(db: Session, inv: dict) -> None:
    row = db.scalar(select(XeroInvoice).where(XeroInvoice.xero_id == inv["InvoiceID"]))
    if not row:
        row = XeroInvoice(id=uuid.uuid4(), xero_id=inv["InvoiceID"], status=inv.get("Status", ""))
        db.add(row)
    row.invoice_number = inv.get("InvoiceNumber")
    row.number_key = number_key(inv.get("InvoiceNumber"))
    row.contact_name = (inv.get("Contact") or {}).get("Name")
    row.reference = inv.get("Reference")
    lines = [" ".join((li.get("Description") or "").split()) for li in inv.get("LineItems") or []]
    row.line_text = " | ".join(t for t in lines if t)[:4000] or row.line_text
    rate = inv.get("CurrencyRate")
    row.currency_rate = rate if rate else row.currency_rate
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
    params = {"where": f'Type=="ACCREC" AND Date>=DateTime({y},{m},{d})', "page": page, "pageSize": PAGE_SIZE}
    resp = httpx.get(f"{API}/Invoices", headers=headers, params=params, timeout=60)
    if resp.status_code == 401:
        raise XeroAuthError("Xero rejected the access token - " + ("check the n8n token workflow." if webhook_mode() else "reconnect Xero."))
    if resp.status_code == 429:
        raise RuntimeError("Xero rate limit reached - the next hourly sync will carry on.")
    resp.raise_for_status()
    return resp.json().get("Invoices", [])


def link_typed_numbers(db: Session) -> int:
    """Bookings whose typed invoice number means a Xero invoice (however it
    was written - case, dashes, spaces, leading zeros, digits only) get a real
    link to it (xero_link_source "typed"). Returns how many were linked."""
    from app.models import SalesOrder

    x = (select(XeroInvoice.id, XeroInvoice.number_key).where(XeroInvoice.number_key.isnot(None))
         .distinct(XeroInvoice.number_key)
         .order_by(XeroInvoice.number_key, XeroInvoice.updated_at_xero.desc().nulls_last()).subquery("x"))
    res = db.execute(update(SalesOrder).where(
        SalesOrder.xero_invoice_id.is_(None), SalesOrder.invoice_number.isnot(None),
        canonical_sql(SalesOrder.invoice_number) == x.c.number_key,
    ).values(xero_invoice_id=x.c.id, xero_link_source="typed", xero_linked_at=func.now()))
    n = res.rowcount or 0
    # The rest: only the digits typed, or only the digits in Xero (needs exactly one invoice to fit).
    for o in db.scalars(select(SalesOrder).where(SalesOrder.xero_invoice_id.is_(None), SalesOrder.invoice_number.isnot(None))):
        inv = find_invoice(db, o.invoice_number)
        if inv:
            o.xero_invoice_id, o.xero_link_source, o.xero_linked_at = inv.id, "typed", datetime.now(timezone.utc)
            n += 1
    db.flush()
    from app.sales.invoice_match import refresh_figures

    # A linked booking with no invoiced amount recorded takes Xero's; recorded amounts are left alone.
    db.execute(update(SalesOrder).where(SalesOrder.xero_invoice_id.isnot(None), SalesOrder.invoice_value_gbp.is_(None))
               .values(invoice_from_xero=True))

    refresh_figures(db)  # invoiced amount and date as Xero has them, for every linked booking
    db.commit()
    return n


def sync(db: Session, full: bool = False) -> dict:
    """Pulls every sales invoice changed since the last sync (or all of them
    again when full=True). Safe to run any time; returns {"invoices": n} or
    {"skipped": reason}."""
    conn = ensure_webhook_connection(db) if webhook_mode() else connection(db)
    if not conn:
        return {"skipped": "Xero isn't connected"}
    started = datetime.now(timezone.utc)
    try:
        token = _access_token(db, conn)
        n, page = 0, 1
        while True:
            batch = fetch_invoices(token, conn.tenant_id, None if full else conn.synced_until, page)
            for inv in batch:
                _upsert(db, inv)
            n += len(batch)
            db.commit()
            if len(batch) < PAGE_SIZE:
                break
            page += 1
            time.sleep(1.1)  # stay under Xero's 60-calls-a-minute limit
    except Exception as exc:
        db.rollback()
        conn = connection(db)
        if conn:
            if webhook_mode():
                conn.access_expires_at = None  # don't reuse a token Xero just refused; ask n8n again next time
            conn.last_error = str(exc)[:500]
            conn.last_sync_at = started
            db.commit()
        logger.warning("xero sync failed: %s", exc)
        raise
    conn.synced_until = started - timedelta(minutes=5)  # overlap so nothing changed mid-sync is missed
    conn.last_sync_at = started
    conn.last_error = None
    db.commit()
    link_typed_numbers(db)
    return {"invoices": n}
