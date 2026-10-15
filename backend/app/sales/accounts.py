"""Who may approve bookings, and when a booking is locked.

Accounts people (users with can_approve_bookings, e.g. Samantha) are the only ones who can:
  - pass or send back the accounts check on a booking (review kind "order_check");
  - change a booking once it's been checked - everyone else sends a change request (review kind
    "booking_change") that an accounts person approves or declines.

Until at least one person has the Accounts permission, nothing is locked and administrators/data managers
handle the checks as before - so switching this on never leaves bookings stuck with nobody to approve them.

Agreed on the 15 Oct call: the salesperson sends the confirmation and presses Confirm when the client has said yes;
that's when accounts check it. A booking locks once accounts have checked it (approved it for invoicing) or any of
its items has been invoiced. Accounts can unlock it for the salesperson, and while "Accounts are away" is on,
administrators (Matt, Clare) stand in.
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


def away(db: Session) -> bool:
    return runtime_settings.get_bool(db, "accounts_away")


def notify_people(db: Session) -> list[User]:
    """Who hears about accounts' work: accounts, plus administrators while accounts are away."""
    people = list(accounts_people(db))
    if away(db) or not people:
        have = {u.id for u in people}
        people += [u for u in db.scalars(select(User).where(User.role == "admin", User.is_active.is_(True))) if u.id not in have]
    return people


def can_approve(db: Session, user_id: uuid.UUID | None, role: str | None = None) -> bool:
    """May this person pass booking checks and approve changes?"""
    user = db.get(User, user_id) if user_id else None
    if accounts_assigned(db):
        if user and user.can_approve_bookings:
            return True
        return bool(user and user.role == "admin" and away(db))
    role = role or (user.role if user else None)
    return role in CAN_USE_AUTOMATIONS or user_id is None   # nobody assigned yet: managers, as before


def invoiced(db: Session, d: SalesDeal) -> bool:
    from app.models import SalesOrder

    return bool(db.scalar(select(SalesOrder.id).where(SalesOrder.deal_id == d.id, (SalesOrder.invoice_number.isnot(None))
                                                       | (SalesOrder.xero_invoice_id.isnot(None))).limit(1)))


def locked(db: Session, d: SalesDeal) -> bool:
    """Checked by accounts (approved for invoicing) or already invoiced: only accounts change it, others request the
    change - unless accounts have unlocked it for the salesperson."""
    if d.unlocked_at or not accounts_assigned(db) or not runtime_settings.get_bool(db, "orders_lock_after_check"):
        return False
    return bool(d.checked_at) or invoiced(db, d)


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
    for u in notify_people(db):
        if u.id == by_user_id:
            continue
        create_notification(db, u.id, "booking_new", f"New booking {d.number}: {d.client_name}",
                            f"{who.name if who else 'Someone'} created it ({d.status}), £{float(d.total_gbp or 0):,.2f} before VAT.{extra}",
                            link=f"/sales/deals/{d.id}", email=False)


def tell_accounts(db: Session, kind: str, title: str, body: str | None, link: str, skip: uuid.UUID | None = None) -> None:
    """Something for accounts to act on: on their bell, and by email for anyone whose "Email me notifications" is on."""
    from app.services.notify import create_notification

    for u in notify_people(db):
        if u.id != skip:
            create_notification(db, u.id, kind, title, body, link=link, email=True)


def email_new_booking(deal_id: uuid.UUID) -> None:
    """Emails the confirmation (Word file attached) to the Accounts addresses in Bookings settings, from the
    automation mailbox. Runs after the booking is saved; a failure is logged and never undoes the booking."""
    from app.core.config import settings as app_settings
    from app.db.session import SessionLocal
    from app.sales import deals as dl
    from app.services.notify import automation_mailbox_ready, send_automation_email

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
        send_automation_email(db, to, f"New booking {d.number}: {d.client_name}", body,
                                     attachments=[(f"{kind} {d.number}.docx",
                                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document", data)])
    except Exception:
        logger.exception("couldn't email accounts about booking %s", deal_id)
    finally:
        db.close()
