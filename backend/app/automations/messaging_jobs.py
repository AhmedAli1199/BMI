"""Background jobs for reminders, notification emails and mail merge.
Unlike the review-queue scanners these are ON by default - they only act
on things a user explicitly asked for (a reminder, a mail merge)."""
from __future__ import annotations

import logging

from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal

logger = logging.getLogger("app.automations.messaging_jobs")


def _with_db(fn):
    def run() -> None:
        db = SessionLocal()
        try:
            result = fn(db)
            logger.info("%s: %s", fn.__name__, result)
        finally:
            db.close()
    run.__name__ = fn.__name__
    return run


def _reminders(db):
    from app.services.reminders import fire_due_reminders
    return fire_due_reminders(db)


def _emails(db):
    from app.services.notify import send_pending_emails
    return send_pending_emails(db)


def _merge(db):
    from app.services.mail_merge import send_queued
    return send_queued(db)


register_job(ScheduledJob(
    id="reminders_due_scan", label="Reminders",
    description="Every 5 minutes: turns reminders that have come due into notifications (bell + email).",
    cron="*/5 * * * *", func=_with_db(_reminders), enabled_flag="automations_reminders_scan_enabled",
))
register_job(ScheduledJob(
    id="notification_email_sender", label="Notification emails",
    description="Every 2 minutes: emails pending notifications from the automation mailbox, retrying failures.",
    cron="*/2 * * * *", func=_with_db(_emails), enabled_flag="automations_notification_email_enabled",
))
register_job(ScheduledJob(
    id="mail_merge_sender", label="Mail merge sender",
    description="Every minute: sends the next batch of each queued mail merge from the sender's Outlook, within Exchange's rate limit.",
    cron="* * * * *", func=_with_db(_merge), enabled_flag="automations_mail_merge_sender_enabled",
))
