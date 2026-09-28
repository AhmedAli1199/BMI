"""In-app notifications, and the automation mailbox that emails them.

create_notification() always writes the in-app row (the bell) first and
marks it email_status="pending" when an email is wanted; a separate job
(send_pending_emails) delivers those. Keeping the two apart means a mail
outage never loses a notification, failures are retried, and a request
never waits on Graph.

The automation mailbox (settings.automation_mailbox, e.g.
automation@bmipublishing.co.uk) sends via the app registration's
application Mail.Send permission: POST /users/{mailbox}/sendMail. IT
should scope that permission to this single mailbox with an Exchange
Application Access Policy, so the app cannot send as anyone else.
"""
from __future__ import annotations

import html
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User
from app.models.messaging import Notification

logger = logging.getLogger("app.services.notify")

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MAX_EMAIL_ATTEMPTS_AGE = timedelta(days=2)  # stop retrying a notification email after this


def create_notification(db: Session, user_id: uuid.UUID, kind: str, title: str, body: str | None = None,
                        link: str | None = None, email: bool = True) -> Notification:
    n = Notification(id=uuid.uuid4(), user_id=user_id, kind=kind, title=title[:300], body=body, link=link,
                     email_status="pending" if email else None)
    db.add(n)
    db.flush()
    return n


def automation_mailbox(db: Session) -> str:
    from app.automations.runtime_settings import get_str

    return (get_str(db, "automation_mailbox") or "").strip()


def automation_mailbox_ready(db: Session) -> bool:
    return bool(automation_mailbox(db) and settings.graph_tenant_id and settings.graph_client_id
                and settings.graph_client_secret)


def send_from_automation_mailbox(mailbox: str, to: str, subject: str, html_body: str) -> None:
    """Raises on failure (caller records the error)."""
    from app.graph_client import get_app_token

    token = get_app_token()
    resp = httpx.post(
        f"{GRAPH_BASE}/users/{mailbox}/sendMail",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": {"subject": subject, "body": {"contentType": "HTML", "content": html_body},
                          "toRecipients": [{"emailAddress": {"address": to}}]},
              "saveToSentItems": False},
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Graph {resp.status_code}: {resp.text[:300]}")


def notification_email_html(n: Notification) -> str:
    link = f"{settings.app_base_url.rstrip('/')}{n.link}" if n.link else settings.app_base_url
    body = html.escape(n.body or "").replace("\n", "<br>")
    return (
        "<div style=\"font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#1f2937\">"
        f"<p style=\"font-size:16px;font-weight:600;margin:0 0 8px\">{html.escape(n.title)}</p>"
        f"<p style=\"margin:0 0 16px\">{body}</p>"
        f"<p><a href=\"{html.escape(link)}\" style=\"background:#1e3a8a;color:#fff;padding:8px 14px;"
        "border-radius:6px;text-decoration:none\">Open in BMI CRM</a></p>"
        "<p style=\"color:#6b7280;font-size:12px;margin-top:24px\">Sent automatically by BMI CRM. "
        "You can turn these emails off under Settings &rsaquo; Notifications.</p></div>"
    )


def send_pending_emails(db: Session, limit: int = 50) -> tuple[int, int, int]:
    """(sent, failed, skipped). Commits per notification."""
    rows = db.scalars(select(Notification).where(Notification.email_status == "pending")
                      .order_by(Notification.created_at).limit(limit)).all()
    sent = failed = skipped = 0
    now = datetime.now(timezone.utc)
    for n in rows:
        user = db.get(User, n.user_id)
        prefs = (user.preferences or {}) if user else {}
        if not user or not user.is_active or prefs.get("email_notifications") == "off":
            n.email_status, n.email_error = "skipped", "user has email notifications off" if user else "no user"
            skipped += 1
        elif not automation_mailbox_ready(db):
            n.email_status, n.email_error = "skipped", "no automation mailbox configured"
            skipped += 1
        else:
            try:
                send_from_automation_mailbox(automation_mailbox(db), user.email, n.title, notification_email_html(n))
                n.email_status, n.email_error = "sent", None
                sent += 1
            except Exception as exc:  # retried next run until too old
                logger.warning("notification email failed: %s", exc)
                n.email_error = str(exc)[:500]
                if n.created_at and now - n.created_at > MAX_EMAIL_ATTEMPTS_AGE:
                    n.email_status = "failed"
                failed += 1
        db.commit()
    return sent, failed, skipped
