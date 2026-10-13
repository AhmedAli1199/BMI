"""Who may approve bookings, and when a booking is locked.

Accounts people (users with can_approve_bookings, e.g. Samantha) are the only ones who can:
  - pass or send back the accounts check on a booking (review kind "order_check");
  - change a booking once it's been checked - everyone else sends a change request (review kind
    "booking_change") that an accounts person approves or declines.

Until at least one person has the Accounts permission, nothing is locked and administrators/data managers
handle the checks as before - so switching this on never leaves bookings stuck with nobody to approve them.
"""
from __future__ import annotations

import html
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.models import SalesDeal, User
from app.roles import CAN_USE_AUTOMATIONS

logger = logging.getLogger("app.sales.accounts")


def accounts_people(db: Session) -> list[User]:
    return db.scalars(select(User).where(User.can_approve_bookings.is_(True), User.is_active.is_(True))).all()


def accounts_assigned(db: Session) -> bool:
    return bool(db.scalar(select(User.id).where(User.can_approve_bookings.is_(True), User.is_active.is_(True)).limit(1)))


def can_approve(db: Session, user_id: uuid.UUID | None, role: str | None = None) -> bool:
    """May this person pass booking checks and approve changes?"""
    user = db.get(User, user_id) if user_id else None
    if accounts_assigned(db):
        return bool(user and user.can_approve_bookings)
    role = role or (user.role if user else None)
    return role in CAN_USE_AUTOMATIONS or user_id is None   # nobody assigned yet: managers, as before


def locked(db: Session, d: SalesDeal) -> bool:
    """A checked booking can only be changed by accounts (others request the change)."""
    return bool(d.checked_at and accounts_assigned(db) and runtime_settings.get_bool(db, "orders_lock_after_check"))


def _addresses(text: str | None) -> list[str]:
    return [a.strip() for a in (text or "").replace(";", ",").split(",") if "@" in a]


def tell_accounts_new(db: Session, d: SalesDeal, by_user_id: uuid.UUID | None) -> None:
    """A new booking: a note on the bell for every accounts person (Matt's doc: "ideally an order confirmation
    would be automatically sent to me each time it was created"). The email copy goes separately."""
    if not runtime_settings.get_bool(db, "orders_copy_accounts_on_create"):
        return
    from app.services.notify import create_notification

    who = db.get(User, by_user_id) if by_user_id else None
    extra = f" Includes {d.unallocated_count} item{'s' if d.unallocated_count != 1 else ''} still to be allocated." if d.unallocated_count else ""
    for u in accounts_people(db):
        if u.id == by_user_id:
            continue
        create_notification(db, u.id, "booking_new", f"New booking {d.number}: {d.client_name}",
                            f"{who.name if who else 'Someone'} created it ({d.status}), £{float(d.total_gbp or 0):,.2f} before VAT.{extra}",
                            link=f"/sales/deals/{d.id}", email=False)


def email_new_booking(deal_id: uuid.UUID) -> None:
    """Emails the confirmation (Word file attached) to the Accounts addresses in Bookings settings, from the
    automation mailbox. Runs after the booking is saved; a failure is logged and never undoes the booking."""
    from app.core.config import settings as app_settings
    from app.db.session import SessionLocal
    from app.sales import deals as dl
    from app.services.notify import automation_mailbox, automation_mailbox_ready, send_from_automation_mailbox

    db = SessionLocal()
    try:
        d = db.get(SalesDeal, deal_id)
        if not d or not runtime_settings.get_bool(db, "orders_copy_accounts_on_create"):
            return
        to = _addresses(dl.settings(db).accounts_emails)
        if not to or not automation_mailbox_ready(db):
            return
        doc = dl.document(db, d)
        kind = "Schedule of works" if d.document == "schedule" else "Order confirmation"
        link = f"{app_settings.app_base_url.rstrip('/')}/sales/deals/{d.id}"
        rows = "".join(f"<li>{html.escape(r['description'])}{' - ' + html.escape(', '.join(r['when'])) if r['when'] else ''}</li>"
                       for r in doc["rows"])
        waiting = (f"<p><b>{d.unallocated_count} item{'s' if d.unallocated_count != 1 else ''} (£{float(d.unallocated_gbp or 0):,.2f})"
                   " still to be allocated to an issue.</b></p>") if d.unallocated_count else ""
        body = (f"<p>A new booking has been created: <b>{kind.lower()} {d.number}</b> for <b>{html.escape(d.client_name)}</b>, "
                f"£{float(d.total_gbp or 0):,.2f} before VAT ({html.escape(d.status)}).</p><ul>{rows}</ul>{waiting}"
                f"<p><a href=\"{link}\">Open the booking</a>. The {kind.lower()} is attached.</p>")
        data = dl.build_docx(doc)
        send_from_automation_mailbox(automation_mailbox(db), to, f"New booking {d.number}: {d.client_name}", body,
                                     attachments=[(f"{kind} {d.number}.docx",
                                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document", data)])
    except Exception:
        logger.exception("couldn't email accounts about booking %s", deal_id)
    finally:
        db.close()
