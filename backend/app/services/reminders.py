"""Due reminders -> notifications. Runs every few minutes (see
app/automations/messaging_jobs.py), so a reminder fires within minutes of
its due time; notified_at makes each fire exactly once."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Contact
from app.models.messaging import Reminder
from app.services.notify import create_notification


def reminder_subject(db: Session, r: Reminder) -> tuple[str, str | None]:
    """(what it's about, app link)."""
    if r.contact_id:
        c = db.get(Contact, r.contact_id)
        if c:
            name = c.full_name or " ".join(x for x in (c.first_name, c.last_name) if x) or "a contact"
            return name, f"/contacts/{c.id}"
    if r.company_id:
        co = db.get(Company, r.company_id)
        if co:
            return co.name, f"/companies/{co.id}"
    return "", "/reminders"


def fire_due_reminders(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    due = db.scalars(select(Reminder).where(Reminder.status == "open", Reminder.notified_at.is_(None),
                                            Reminder.due_at <= now).order_by(Reminder.due_at).limit(500)).all()
    for r in due:
        about, link = reminder_subject(db, r)
        title = f"Reminder: {about}" if about else "Reminder"
        create_notification(db, r.user_id, "reminder", title, r.note or "You asked to be reminded about this.",
                            link, email=r.email_me)
        r.notified_at = now
    db.commit()
    return len(due)
