"""Settings › Integrations - connecting Xero (admins only)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import SalesOrder, User, XeroInvoice
from app.roles import CAN_USE_AUTOMATIONS
from app.services import outlook, xero

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _staff(user: User = Depends(current_user)) -> User:
    if user.role not in CAN_USE_AUTOMATIONS:
        raise HTTPException(status_code=403, detail="Only admins and data managers can manage integrations.")
    return user


class XeroStatus(BaseModel):
    configured: bool
    connected: bool
    organisation: str | None = None
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None
    invoices: int = 0
    bookings_matched: int = 0
    redirect_uri: str
    # "app" = signed in from Settings; "webhook" = tokens come from the n8n workflow
    mode: str = "app"


@router.get("/xero", response_model=XeroStatus)
def xero_status(db: Session = Depends(get_db), _: User = Depends(_staff)) -> XeroStatus:
    conn = xero.connection(db)
    via_webhook = xero.webhook_mode()
    matched = db.scalar(select(func.count()).select_from(SalesOrder).where(
        func.upper(func.replace(SalesOrder.invoice_number, " ", "")).in_(select(XeroInvoice.number_key)))) or 0
    return XeroStatus(
        configured=xero.is_configured(), connected=bool(conn) or via_webhook,
        organisation=(conn.tenant_name if conn else None) or (settings.xero_tenant_name or "Xero organisation" if via_webhook else None),
        connected_at=conn.connected_at if conn else None, last_sync_at=conn.last_sync_at if conn else None,
        last_error=conn.last_error if conn else None,
        invoices=db.scalar(select(func.count()).select_from(XeroInvoice)) or 0, bookings_matched=matched,
        redirect_uri=xero.redirect_uri(), mode="webhook" if via_webhook else "app",
    )


@router.get("/xero/start")
def xero_start(return_to: str = "/settings", user: User = Depends(_staff)) -> dict:
    try:
        return {"url": xero.authorize_url(outlook.make_state(user.id, return_to))}
    except xero.XeroNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class CallbackIn(BaseModel):
    code: str
    state: str


@router.post("/xero/callback")
def xero_callback(payload: CallbackIn, db: Session = Depends(get_db)) -> dict:
    """Xero redirects the browser back here (via the frontend) - the signed
    state carries who started it, so no session lookup is needed."""
    try:
        user_id, return_to = outlook.read_state(payload.state)
        conn = xero.complete_sign_in(db, payload.code, user_id)
    except (outlook.OutlookAuthError, xero.XeroAuthError, xero.XeroNotConfigured) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        result = xero.sync(db)
    except Exception as exc:  # connected fine; the hourly sync will retry
        result = {"error": str(exc)[:200]}
    return {"organisation": conn.tenant_name, "return_to": return_to, **result}


@router.post("/xero/sync")
def xero_sync_now(full: bool = False, db: Session = Depends(get_db), _: User = Depends(_staff)) -> dict:
    """full=true re-reads every invoice from the start (picks up what each
    one is for - needed once, after the invoice matcher was added)."""
    try:
        return xero.sync(db, full=full)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Xero sync failed: {exc}") from exc


@router.delete("/xero", status_code=204, response_model=None)
def xero_disconnect(db: Session = Depends(get_db), _: User = Depends(_staff)) -> None:
    """Forgets the connection. Invoices already copied stay (they're history)."""
    if xero.webhook_mode():
        raise HTTPException(status_code=400, detail="Xero is linked through the n8n token workflow. To disconnect, remove the token webhook setting on the server.")
    conn = xero.connection(db)
    if conn:
        db.delete(conn)
        db.commit()
