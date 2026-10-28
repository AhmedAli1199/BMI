"""Sending a drafted reply from the reviewer's own Outlook - shared by the Review Queue cards that answer someone
(subscription changes, overseas readers). Nothing is ever sent without a person pressing the card's button."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

EMAIL = re.compile(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+")


def send(db: Session, actor_user_id: str | None, to: str, subject: str, body: str, *,
         mailbox: str | None = None, message_id: str | None = None) -> None:
    """Sends from the reviewer's Outlook. When the reviewer's own inbox received the email, it goes as a reply in the
    same thread; otherwise as a new email. ValueError with a plain sentence when it can't be sent."""
    from app.models.messaging import MailAccount
    from app.services import outlook
    from app.services.mail_merge import to_html

    to = (to or "").strip()
    if not EMAIL.fullmatch(to):
        raise ValueError("Enter the email address to send this to.")
    if not (body or "").strip():
        raise ValueError("The reply is empty - write it first.")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == uuid.UUID(actor_user_id))) if actor_user_id else None
    if not acct:
        raise ValueError("Connect your Outlook first (Settings › Email), then try again - or reply from Outlook yourself.")
    html = to_html(body)
    try:
        if mailbox and message_id and acct.email.lower() == mailbox.lower():
            try:
                outlook.reply_to(db, acct, message_id, html_body=html, to=[to])
                return
            except RuntimeError:
                pass   # the email was moved or deleted - send it as a new email instead
        outlook.send_mail(db, acct, to=[to], subject=subject or "Thank you for your email", html_body=html)
    except outlook.OutlookAuthError as exc:
        raise ValueError("Your Outlook connection has lapsed. Reconnect Outlook in Settings, then try again.") from exc
    except outlook.RateLimited as exc:
        raise ValueError("Outlook is asking us to slow down - try again in a minute.") from exc
    except RuntimeError as exc:
        raise ValueError("Outlook didn't accept the email, so nothing was sent. Please try again.") from exc
