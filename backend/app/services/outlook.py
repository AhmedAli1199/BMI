""""Connect Outlook" - each user signs in with Microsoft once (delegated
OAuth 2.0 authorization-code flow) and mail merge sends from their own
mailbox via POST /me/sendMail.

Why delegated rather than the app's own Mail.Send: the app can only ever
send as the person who signed in, the message lands in their Sent Items,
and replies come back to them - exactly as if they'd sent it from Outlook.

Tokens: only the refresh token is needed long-term. Both tokens are
Fernet-encrypted at rest (settings.mail_token_key) and never returned by
any API. A refresh token dies after ~90 days unused or on password reset /
admin revoke - the user then sees "Reconnect" (last_error is set).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.messaging import MailAccount

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = "offline_access User.Read Mail.Send"
STATE_MAX_AGE = 900  # seconds a sign-in may take


class OutlookNotConfigured(Exception):
    pass


class OutlookAuthError(Exception):
    """The stored grant no longer works - the user has to reconnect."""


def _client() -> tuple[str, str, str]:
    cid = settings.outlook_client_id or settings.graph_client_id
    secret = settings.outlook_client_secret or settings.graph_client_secret
    tenant = settings.outlook_tenant_id or settings.graph_tenant_id
    if not (cid and secret and tenant):
        raise OutlookNotConfigured("Outlook sign-in isn't set up yet (no Microsoft app registration configured).")
    return cid, secret, tenant


def is_configured() -> bool:
    try:
        _client()
        return True
    except OutlookNotConfigured:
        return False


def redirect_uri() -> str:
    return settings.outlook_redirect_uri or f"{settings.app_base_url.rstrip('/')}/api/outlook/callback"


def _fernet() -> Fernet:
    key = settings.mail_token_key
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(("mail-token:" + settings.api_key).encode()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def _sign(payload: str) -> str:
    return hmac.new(settings.api_key.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def make_state(user_id: uuid.UUID, return_to: str = "/settings", purpose: str | None = None) -> str:
    """purpose: None for mail; "calendar" / "google_calendar" for the calendar sign-ins, which share this signing."""
    data = {"u": str(user_id), "t": int(time.time()), "r": return_to}
    if purpose:
        data["p"] = purpose
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    return f"{payload}.{_sign(payload)}"


def state_purpose(state: str) -> str | None:
    try:
        return json.loads(base64.urlsafe_b64decode(state.rsplit(".", 1)[0])).get("p")
    except Exception:
        return None


def read_state(state: str) -> tuple[uuid.UUID, str]:
    try:
        payload, sig = state.rsplit(".", 1)
    except ValueError:
        raise OutlookAuthError("Invalid sign-in state.")
    if not hmac.compare_digest(sig, _sign(payload)):
        raise OutlookAuthError("Invalid sign-in state.")
    data = json.loads(base64.urlsafe_b64decode(payload))
    if time.time() - data["t"] > STATE_MAX_AGE:
        raise OutlookAuthError("The sign-in took too long - please try again.")
    ret = data.get("r") or "/settings"
    return uuid.UUID(data["u"]), ret if ret.startswith("/") else "/settings"


def authorize_url(user_id: uuid.UUID, login_hint: str | None = None, return_to: str = "/settings") -> str:
    cid, _, tenant = _client()
    params = {
        "client_id": cid, "response_type": "code", "redirect_uri": redirect_uri(), "response_mode": "query",
        "scope": SCOPES, "state": make_state(user_id, return_to), "prompt": "select_account",
    }
    if login_hint:
        params["login_hint"] = login_hint
    return str(httpx.URL(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize", params=params))


def _token_request(data: dict) -> dict:
    cid, secret, tenant = _client()
    resp = httpx.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                      data={"client_id": cid, "client_secret": secret, "scope": SCOPES, **data}, timeout=20)
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code >= 300:
        raise OutlookAuthError(body.get("error_description") or f"Microsoft sign-in failed ({resp.status_code}).")
    return body


def _store_tokens(acct: MailAccount, body: dict) -> None:
    acct.access_token_enc = encrypt(body["access_token"])
    acct.access_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(body.get("expires_in", 3600)) - 120)
    if body.get("refresh_token"):
        acct.refresh_token_enc = encrypt(body["refresh_token"])
    acct.last_error = None


def complete_sign_in(db: Session, code: str, state: str) -> tuple[MailAccount, str]:
    user_id, return_to = read_state(state)
    body = _token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri()})
    me = httpx.get(f"{GRAPH_BASE}/me", headers={"Authorization": f"Bearer {body['access_token']}"},
                   params={"$select": "displayName,mail,userPrincipalName"}, timeout=15).json()
    email = me.get("mail") or me.get("userPrincipalName") or ""
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user_id))
    if not acct:
        acct = MailAccount(id=uuid.uuid4(), user_id=user_id, email=email, refresh_token_enc="")
        db.add(acct)
    acct.email, acct.display_name = email, me.get("displayName")
    acct.connected_at = datetime.now(timezone.utc)
    _store_tokens(acct, body)
    db.commit()
    return acct, return_to


def access_token(db: Session, acct: MailAccount) -> str:
    if acct.access_token_enc and acct.access_expires_at and acct.access_expires_at > datetime.now(timezone.utc):
        return decrypt(acct.access_token_enc)
    try:
        body = _token_request({"grant_type": "refresh_token", "refresh_token": decrypt(acct.refresh_token_enc)})
    except OutlookAuthError as exc:
        acct.last_error = f"Reconnect needed: {exc}"
        db.commit()
        raise
    _store_tokens(acct, body)
    db.commit()
    return body["access_token"]


def _attachment(a: tuple) -> dict:
    """(name, content type, bytes) or (name, content type, bytes, content id) for a picture shown in the body."""
    out = {"@odata.type": "#microsoft.graph.fileAttachment", "name": a[0], "contentType": a[1],
           "contentBytes": base64.b64encode(a[2]).decode()}
    if len(a) > 3 and a[3]:
        out.update(isInline=True, contentId=a[3])
    return out


def reply_to(db: Session, acct: MailAccount, message_id: str, *, html_body: str, to: list[str] | None = None,
             attachments: list[tuple] | None = None) -> None:
    """Replies in the same email thread, from the connected user's own mailbox (the message must be in it).
    Raises like send_mail; a RuntimeError with "404" means the message isn't in this mailbox any more."""
    token = access_token(db, acct)
    h = {"Authorization": f"Bearer {token}"}
    r = httpx.post(f"{GRAPH_BASE}/me/messages/{message_id}/createReply", headers=h, timeout=30)
    if r.status_code == 401:
        raise OutlookAuthError("Microsoft rejected the sign-in - reconnect Outlook.")
    if r.status_code >= 300:
        raise RuntimeError(f"Outlook couldn't start the reply ({r.status_code})")
    draft = r.json()
    quoted = (draft.get("body") or {}).get("content") or ""
    patch: dict = {"body": {"contentType": "HTML", "content": html_body + quoted}}
    if to:
        patch["toRecipients"] = [{"emailAddress": {"address": a}} for a in to]
    r = httpx.patch(f"{GRAPH_BASE}/me/messages/{draft['id']}", headers=h, json=patch, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"Outlook couldn't write the reply ({r.status_code})")
    for a in attachments or []:
        r = httpx.post(f"{GRAPH_BASE}/me/messages/{draft['id']}/attachments", headers=h, json=_attachment(a), timeout=60)
        if r.status_code >= 300:
            raise RuntimeError(f"Outlook couldn't attach {a[0]} ({r.status_code})")
    r = httpx.post(f"{GRAPH_BASE}/me/messages/{draft['id']}/send", headers=h, timeout=30)
    if r.status_code == 429:
        raise RateLimited(int(r.headers.get("Retry-After", "60")))
    if r.status_code >= 300:
        raise RuntimeError(f"Outlook didn't send the reply ({r.status_code})")


def send_mail(db: Session, acct: MailAccount, *, to: list[str], subject: str, html_body: str,
              cc: list[str] | None = None, bcc: list[str] | None = None,
              attachments: list[tuple] | None = None) -> None:
    """Sends as the connected user. Raises OutlookAuthError (reconnect),
    RateLimited (back off) or RuntimeError (this message failed)."""
    token = access_token(db, acct)
    msg = {
        "subject": subject, "body": {"contentType": "HTML", "content": html_body},
        "toRecipients": [{"emailAddress": {"address": a}} for a in to],
        "ccRecipients": [{"emailAddress": {"address": a}} for a in (cc or [])],
        "bccRecipients": [{"emailAddress": {"address": a}} for a in (bcc or [])],
    }
    if attachments:
        msg["attachments"] = [_attachment(a) for a in attachments]
    resp = httpx.post(f"{GRAPH_BASE}/me/sendMail", headers={"Authorization": f"Bearer {token}"},
                      json={"message": msg, "saveToSentItems": True}, timeout=60)
    if resp.status_code == 401:
        acct.access_token_enc = None
        db.commit()
        raise OutlookAuthError("Microsoft rejected the sign-in - reconnect Outlook.")
    if resp.status_code == 429:
        raise RateLimited(int(resp.headers.get("Retry-After", "60")))
    if resp.status_code >= 300:
        raise RuntimeError(f"Outlook refused the message ({resp.status_code}): {resp.text[:300]}")


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        super().__init__(f"rate limited, retry after {retry_after}s")
        self.retry_after = retry_after
