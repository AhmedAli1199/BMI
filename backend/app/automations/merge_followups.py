"""SALES-032 - follow-ups for people who didn't answer a mail merge.

Most people a mail merge goes to neither book nor say no - they just don't answer, and the second email that would win
some of them is easy to forget once the next issue is under way. Each morning this looks at the email mail merges sent
between "Wait before following up (days)" and "Only mail merges sent in the last (days)" ago, and for each one works
out who simply didn't answer. Left out:
  - anyone who replied (the sender's inbox is checked for an email from them since the merge went out; only who sent
    each email is looked at),
  - anyone whose email bounced, or who has unsubscribed,
  - anyone whose company has booked since,
  - anyone with a note added since (someone has been talking to them),
  - anyone the merge didn't actually reach.
The salesperson who sent the merge gets one card: who's left, with a short follow-up drafted. "Open as a mail merge"
opens the mail merge screen with those people and the draft filled in, to change, preview and send as usual. A
follow-up is never followed up again, and each mail merge gets one card at most.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.mail_parsing import looks_like_bounce, parse_message
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Contact, Note, ReviewQueueItem, SalesOrder, User
from app.models.messaging import MailMerge, MailMergeRecipient

logger = logging.getLogger("app.automations.merge_followups")

KIND = "merge_followup"
FOLLOW_UP_LABEL = "Follow-up to "   # a merge started from one of these cards is labelled so, and never followed up itself
STATE = "merge_followups"
MAX_TRIES = 3                       # days the replies check can fail before the card goes out marked "not checked"
LIST_LIMIT = 15

_PROMPT = (
    "Write a short, friendly follow-up email from a magazine salesperson at BMI Publishing to someone who didn't answer "
    "the email below. Two to four sentences: say you're following up, remind them in a line what it was about, and make "
    "it easy to reply. British English, plain text. No greeting line and no sign-off - those are added. Don't add any "
    "prices, figures or dates that aren't in the original email."
)


def _strip_subject(s: str | None) -> str:
    return re.sub(r"^((re|fw|fwd):\s*)+", "", s or "", flags=re.I).strip()


def replied_addresses(mailbox: str, since: datetime) -> tuple[set[str], set[str]]:
    """(who emailed the sender since, who bounced) - from the sender's inbox. Raises GraphRequestError."""
    from app.graph_client import list_messages_since

    replied, bounced = set(), set()
    for raw in list_messages_since(mailbox, since.strftime("%Y-%m-%dT%H:%M:%SZ"), max_pages=20):
        msg = parse_message(raw)
        if looks_like_bounce(msg):
            bounced |= {a.lower() for a in msg.failed_recipients}
        elif msg.from_address:
            replied.add(msg.from_address.lower())
    return replied, bounced


def who_is_left(db: Session, m: MailMerge, replied: set[str], bounced: set[str]) -> tuple[list[tuple[Contact, str]], dict[str, int]]:
    """(the people to follow up, with the address it went to; how many were left out and why)."""
    since = m.finished_at or m.created_at
    rows = db.execute(select(MailMergeRecipient, Contact).join(Contact, Contact.id == MailMergeRecipient.contact_id)
                      .where(MailMergeRecipient.merge_id == m.id, MailMergeRecipient.status == "sent")).all()
    cids = [c.id for _, c in rows]
    noted = {r[0] for r in db.execute(select(Note.entity_id).where(Note.entity_type == "contact", Note.entity_id.in_(cids),
                                                                  Note.act_created_at >= since))} if cids else set()
    companies = {c.company_id for _, c in rows if c.company_id}
    booked = {r[0] for r in db.execute(select(SalesOrder.company_id).where(SalesOrder.company_id.in_(companies),
                                                                          SalesOrder.booked_on >= since.date(),
                                                                          SalesOrder.status != "cancelled"))} if companies else set()
    left, out = [], {"replied": 0, "booked": 0, "bounced or unsubscribed": 0, "talked to since": 0}
    seen: set[str] = set()
    for r, c in rows:
        email = (r.email or "").lower()
        if not email or email in seen:
            continue
        seen.add(email)
        if email in replied:
            out["replied"] += 1
        elif email in bounced or c.has_bounced or c.is_unsubscribed:
            out["bounced or unsubscribed"] += 1
        elif c.company_id in booked:
            out["booked"] += 1
        elif c.id in noted:
            out["talked to since"] += 1
        else:
            left.append((c, r.email))
    return left, out


def draft(m: MailMerge) -> tuple[str, str, bool]:
    """(subject, body, ai_used). The body uses merge fields, so each person gets their own name."""
    from app.automations.llm import draft_text, is_configured
    from app.proposals.drafting import numbers_in
    from app.services.mail_merge import to_text

    original = to_text(m.body or "")
    sent = (m.finished_at or m.created_at).strftime("%-d %B")
    subject = f"Re: {_strip_subject(m.subject)}" if m.subject else "Following up"
    text = (f"I'm just following up on my email of {sent} about {_strip_subject(m.subject) or 'our magazine'}, in case it got "
            "buried. If it's of interest, I'd be very happy to send more details or have a quick chat - just reply to this email.")
    ai = False
    if is_configured():
        got = draft_text(_PROMPT, f"THE EMAIL THEY DIDN'T ANSWER (sent {sent}):\nSubject: {m.subject}\n\n{original[:4000]}",
                         max_tokens=220, purpose="merge_followups.draft")
        if got and len(got) < 900 and numbers_in(got) <= numbers_in(original):
            text, ai = got.strip(), True
    body = (f"Dear {{{{salutation|colleague}}}},\n\n{text}\n\nKind regards,\n{{{{my_name}}}}\n\n"
            f"---\nMy email of {sent}:\n\n{original.strip()}")
    return subject, body, ai


def queue(db: Session, m: MailMerge, left: list[tuple[Contact, str]], out: dict[str, int], checked: bool) -> ReviewQueueItem:
    subject, body, ai = draft(m)
    sent_on = (m.finished_at or m.created_at)
    sender = db.get(User, m.created_by_user_id) if m.created_by_user_id else None
    label = m.source_label or m.subject or "your mail merge"
    details = [{"label": "Mail merge", "value": f"{m.subject or '(no subject)'} - sent {sent_on:%-d %b %Y} to {m.sent} people",
                "href": f"/mail-merge/{m.id}"},
               {"label": "No answer from", "value": f"{len(left)} {'person' if len(left) == 1 else 'people'}"}]
    gone = ", ".join(f"{n} {why}" for why, n in out.items() if n)
    if gone:
        details.append({"label": "Left out", "value": gone})
    if not checked:
        details.append({"label": "Worth knowing", "value": "Your inbox couldn't be checked for replies, so some of these people may "
                                                           "have answered. Look through the list before sending."})
    for c, email in left[:LIST_LIMIT]:
        details.append({"label": "Follow up", "value": f"{c.full_name or email} ({email})", "href": f"/contacts/{c.id}"})
    if len(left) > LIST_LIMIT:
        details.append({"label": "Follow up", "value": f"and {len(left) - LIST_LIMIT} more - all listed in the mail merge"})
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=None, status="pending",
        payload={
            "summary": f"{len(left)} {'person' if len(left) == 1 else 'people'} didn't answer \"{_strip_subject(m.subject) or label}\"",
            "details": details,
            "original_text": f"Subject: {subject}\n\n{body}", "original_label": "Drafted follow-up",
            "merge_id": str(m.id), "owner_user_id": str(m.created_by_user_id) if m.created_by_user_id else None,
            "merge": {"contact_ids": [str(c.id) for c, _ in left], "subject": subject, "body": body,
                      "label": f"{FOLLOW_UP_LABEL}{label}"[:300]},
            "ai_drafted": ai,
            "facets": {"replies": "Replies checked" if checked else "Replies not checked",
                       "size": "Under 20" if len(left) < 20 else "20 to 100" if len(left) <= 100 else "Over 100",
                       "salesperson": (sender.name or sender.email) if sender else "No one"},
            "sort_date": sent_on.date().isoformat(),
        },
    )
    db.add(item)
    return item


def due_merges(db: Session, now: datetime) -> list[MailMerge]:
    wait = runtime_settings.get_int(db, "merge_followup_wait_days")
    back = runtime_settings.get_int(db, "merge_followup_lookback_days")
    smallest = runtime_settings.get_int(db, "merge_followup_min_recipients")
    done = {r[0] for r in db.execute(select(ReviewQueueItem.payload["merge_id"].astext).where(ReviewQueueItem.kind == KIND)) if r[0]}
    done |= set(get_state(db, STATE).get("nothing_left") or [])
    stmt = (select(MailMerge).where(MailMerge.output == "email", MailMerge.status == "done", MailMerge.sent >= smallest,
                                    func.coalesce(MailMerge.finished_at, MailMerge.created_at) <= now - timedelta(days=wait),
                                    func.coalesce(MailMerge.finished_at, MailMerge.created_at) >= now - timedelta(days=back),
                                    func.coalesce(MailMerge.source_label, "").notlike(f"{FOLLOW_UP_LABEL}%"))
            .order_by(MailMerge.created_at))
    return [m for m in db.scalars(stmt) if str(m.id) not in done]


def scan() -> None:
    from app.graph_client import GraphRequestError

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        st = get_state(db, STATE)
        tries = dict(st.get("tries") or {})
        nothing = list(st.get("nothing_left") or [])
        queued = 0
        for m in due_merges(db, now):
            checked = True
            try:
                replied, bounced = replied_addresses(m.from_email, m.created_at) if m.from_email else (set(), set())
                checked = bool(m.from_email)
            except GraphRequestError as exc:
                tries[str(m.id)] = tries.get(str(m.id), 0) + 1
                logger.warning("merge follow-ups: inbox %s couldn't be read for merge %s (HTTP %s)", m.from_email, m.id, exc.status_code)
                if tries[str(m.id)] < MAX_TRIES:
                    continue   # try again tomorrow
                replied, bounced, checked = set(), set(), False
            left, out = who_is_left(db, m, replied, bounced)
            tries.pop(str(m.id), None)
            if left:
                queue(db, m, left, out, checked)
                queued += 1
            else:   # everyone answered or was left out - remember it so it isn't looked at again
                nothing.append(str(m.id))
            db.commit()
        set_state(db, STATE, {"tries": tries, "nothing_left": nothing[-2000:]})
        db.commit()
        logger.info("merge follow-ups: %d cards", queued)
    finally:
        db.close()


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "open_merge":
        item.payload = {**item.payload, "open_href": f"/mail-merge?review={item.id}"}
    elif action_id != "no_follow_up":
        raise ValueError("That button isn't available on this card.")


register(ReviewKind(
    kind=KIND,
    label="Mail merge follow-ups",
    description="People who didn't answer one of your mail merges, with a short follow-up drafted to send as a new mail merge.",
    actions=[
        ReviewAction(id="open_merge", label="Open as a mail merge", style="primary", outcome="approved"),
        ReviewAction(id="no_follow_up", label="No follow-up this time", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("replies", "Replies"), ("size", "How many"), ("salesperson", "Salesperson")),
    date_sort_label="date the mail merge went out",
))

register_job(ScheduledJob(
    id="merge_followup_scan",
    label="Mail merge follow-ups",
    description="Each morning, finds the people who didn't answer a mail merge sent a while ago, and drafts one follow-up.",
    cron="40 7 * * 1-5",
    func=scan,
    enabled_flag="automations_merge_followups_enabled",
))
