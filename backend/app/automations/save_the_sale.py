"""SALES-022 - save-the-sale replies (docs/build-spec.txt).

When a client says no by email ("no budget this year", "we've gone with another magazine"), the email scan
(email_summary.py) records a "decline" signal with the reason. This job turns each one into a review item: a draft
reply that acknowledges the no, asks why (or confirms the reason), and offers a sensible alternative where there
is one - for the salesperson to edit and send. Nothing is ever sent by itself.

The alternative is chosen by rules, never by the AI, so every product and price comes from the rate card and
every issue from the editorial plan:
  budget      -> a smaller or cheaper product in the same title (rate card), or a current offer
  timing      -> the next open issue of the same title, or the same issue next year
  results     -> a different format (online / newsletter) in the same brand
  competitor / other -> no forced offer; acknowledge and ask
The wording comes from the "Save the sale" templates in the email template library (one per reason, loaded as
"needs a check" for BMI to make their own). AI may polish the wording when configured, but its version is thrown
away if it adds any figure that isn't in the template or the facts.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.llm import draft_text, is_configured
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import Company, Contact, Email, EmailSignal, Note, ReviewQueueItem, SalesEdition, SalesOrder, SalesRate, SalesRep, SalesTitle
from app.models.messaging import MailTemplate

logger = logging.getLogger("app.automations.save_the_sale")

KIND = "save_the_sale"
REASON_LABELS = {"budget": "No budget", "timing": "Timing doesn't work", "results": "Didn't work for them last time",
                 "competitor": "Going with someone else", "other": "No reason given"}

# Starting wording, one per reason. Loaded into the template library as "needs a check" - BMI's own wording replaces it.
DEFAULT_TEMPLATES = {
    "budget": ("Save the sale: no budget", "Re: {{title}}",
               "Hi {{first_name}},\n\nThanks for letting me know, and I completely understand - budgets are tight for everyone at the moment.\n\n"
               "{{alternative}}\n\nWould that be worth a quick chat? If not, no problem at all - I'll keep you posted on what's coming up.\n\n"
               "Best wishes,\n{{sender}}"),
    "timing": ("Save the sale: timing", "Re: {{title}}",
               "Hi {{first_name}},\n\nThanks for coming back to me - I understand the timing isn't right for this one.\n\n"
               "{{alternative}}\n\nShall I pencil that in for you, with no commitment until you confirm?\n\nBest wishes,\n{{sender}}"),
    "results": ("Save the sale: results", "Re: {{title}}",
                "Hi {{first_name}},\n\nThanks for the honest feedback - it's really useful to hear. Could you tell me a little more about "
                "what you were hoping to see? I'd like to make sure anything we suggest next time works harder for you.\n\n"
                "{{alternative}}\n\nBest wishes,\n{{sender}}"),
    "competitor": ("Save the sale: another publication", "Re: {{title}}",
                   "Hi {{first_name}},\n\nThanks for letting me know, I appreciate it. May I ask what tipped the balance? It would help us "
                   "a lot to understand.\n\nIf anything changes, or you'd like to add {{title}} alongside, I'd be very happy to help.\n\n"
                   "Best wishes,\n{{sender}}"),
    "other": ("Save the sale: general", "Re: {{title}}",
              "Hi {{first_name}},\n\nThanks for letting me know. Is there anything we could do differently that would make it work for you - "
              "a different issue, size or format? I'd be glad to put some options together.\n\nBest wishes,\n{{sender}}"),
}
TEMPLATE_NAMES = {reason: t[0] for reason, t in DEFAULT_TEMPLATES.items()}


def ensure_templates(db: Session) -> int:
    """Adds the default "Save the sale" templates once (by name); a person can then edit them into BMI's own words."""
    have = set(db.scalars(select(MailTemplate.name).where(MailTemplate.kind == "save_sale")))
    n = 0
    for reason, (name, subject, body) in DEFAULT_TEMPLATES.items():
        if name in have:
            continue
        db.add(MailTemplate(id=uuid.uuid4(), name=name, subject=subject, body=body, shared=True, kind="save_sale",
                            description=f"Reply to a client who said no - {REASON_LABELS[reason].lower()}.",
                            source="default", needs_check=True))
        n += 1
    db.flush()
    return n


def _money(v) -> str:
    v = float(v or 0)
    return f"£{v:,.0f}" if v == int(v) else f"£{v:,.2f}"


def _last_booking(db: Session, contact: Contact) -> tuple[SalesOrder, SalesEdition, SalesTitle] | None:
    if not contact.company_id:
        return None
    q = (select(SalesOrder, SalesEdition).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
         .where(SalesOrder.status == "booked", SalesOrder.company_id == contact.company_id))
    row = db.execute(q.order_by(SalesEdition.edition_date.desc().nulls_last()).limit(1)).first()
    if not row:
        return None
    o, ed = row
    return o, ed, db.get(SalesTitle, ed.title_id)


def alternatives(db: Session, reason: str, last: tuple[SalesOrder, SalesEdition, SalesTitle] | None, today: date | None = None) -> list[dict]:
    """Rule-based options to offer, best first. Each: {key, label, text, price, href}. Empty = nothing sensible to offer."""
    today = today or date.today()
    if not last or reason in ("competitor", "other"):
        return []
    o, ed, title = last
    out: list[dict] = []
    rates = db.scalars(select(SalesRate).where(SalesRate.title_id == title.id, SalesRate.year.in_((today.year, today.year + 1)),
                                               SalesRate.archived.is_(False), SalesRate.price_gbp.isnot(None))
                       .order_by(SalesRate.year.desc())).all()
    paid = float(o.value_gbp or 0)
    if reason == "budget":
        cheaper = sorted({r.product: r for r in rates if 0 < float(r.price_gbp) < paid}.values(), key=lambda r: -float(r.price_gbp))
        for r in cheaper[:2]:
            out.append({"key": f"rate:{r.id}", "label": f"{r.product} ({_money(r.price_gbp)})", "price": float(r.price_gbp),
                        "href": "/sales/rate-card",
                        "text": f"If it would help, a {r.product.lower()} in {title.name} is {_money(r.price_gbp)} - a smaller commitment "
                                f"that keeps you in front of the same readers."})
    if reason in ("timing", "budget"):
        nxt = db.scalars(select(SalesEdition).where(SalesEdition.title_id == title.id, SalesEdition.status == "open",
                                                    SalesEdition.edition_date > today).order_by(SalesEdition.edition_date).limit(2)).all()
        for e in nxt:
            if e.id == ed.id:
                continue
            when = e.edition_date.strftime("%B %Y") if e.edition_date else e.name
            out.append({"key": f"edition:{e.id}", "label": f"{title.name} {e.name} ({when})", "price": None,
                        "href": f"/sales/editions/{e.id}",
                        "text": f"Would a later issue work better? {title.name} {e.name} comes out in {when}"
                                + (f", with advertising booked by {e.ad_deadline:%-d %B}." if e.ad_deadline else ".")})
            break
    if reason == "results":
        from app.sales.brands import brand_for_title_slug, brand_titles

        b = brand_for_title_slug(title.slug)
        ids = [t.id for t in brand_titles(db, b, active_only=True)] if b else [title.id]
        online = db.scalars(select(SalesRate).where(SalesRate.title_id.in_(ids), SalesRate.section.in_(("website", "newsletter")),
                                                    SalesRate.year.in_((today.year, today.year + 1)), SalesRate.archived.is_(False),
                                                    SalesRate.price_gbp.isnot(None)).order_by(SalesRate.price_gbp)).all()
        if online:
            r = online[0]
            out.append({"key": f"rate:{r.id}", "label": f"{r.product} ({_money(r.price_gbp)})", "price": float(r.price_gbp),
                        "href": "/sales/rate-card",
                        "text": f"One idea: our {r.product.lower()} ({_money(r.price_gbp)}) reaches the same audience online, and we can "
                                f"share the results with you afterwards."})
    return out


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[£,]", "", m) for m in re.findall(r"£?\d[\d,]*(?:\.\d+)?", text or "")}


def _template(db: Session, reason: str) -> tuple[str, str]:
    t = db.scalars(select(MailTemplate).where(MailTemplate.kind == "save_sale", MailTemplate.name == TEMPLATE_NAMES.get(reason))).first()
    if t:
        return t.subject or "", t.body
    _, subject, body = DEFAULT_TEMPLATES.get(reason, DEFAULT_TEMPLATES["other"])
    return subject, body


def compose(db: Session, reason: str, contact: Contact, title_name: str, alt: dict | None, sender: str, extra: str = "") -> tuple[str, bool]:
    """'Subject: ...\\n\\nbody' from the reason's template; AI polish only if it adds no figures of its own."""
    subject, body = _template(db, reason)
    fields = {"first_name": contact.first_name or (contact.full_name or "").split(" ")[0] or "there", "title": title_name or "the magazine",
              "sender": sender or "", "alternative": alt["text"] if alt else ""}
    fill = lambda s: re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(fields.get(m.group(1), m.group(0))), s or "")  # noqa: E731
    body_text = re.sub(r"\n{3,}", "\n\n", fill(body)).strip()
    text = f"Subject: {fill(subject)}\n\n{body_text}"
    if not is_configured():
        return text, False
    prompt = ("You lightly improve a salesperson's reply to a client who has said no to advertising. Keep it short, warm and "
              "British English. Keep the structure: thank them, acknowledge the reason, ask or offer as the draft does. Keep the "
              "'Subject:' line. Do NOT add any price, date, figure or product that isn't already in the draft. Return only the email.")
    ai = draft_text(prompt, text + (f"\n\nExtra instruction from the salesperson: {extra}" if extra else ""), max_tokens=500,
                    purpose="save_the_sale.draft")
    if ai and ai.strip().lower().startswith("subject:") and _numbers(ai) <= _numbers(text):
        return ai.strip(), True
    return text, False


def _sender(db: Session, rep: SalesRep | None) -> str:
    return (rep.name.split(" ")[0] if rep and rep.name else "")


def queue_for_signal(db: Session, signal: EmailSignal) -> ReviewQueueItem | None:
    contact = db.get(Contact, signal.contact_id)
    if not contact:
        return None
    reason = signal.reason or "other"
    last = _last_booking(db, contact)
    alts = alternatives(db, reason, last)
    o, ed, title = last if last else (None, None, None)
    rep = db.get(SalesRep, o.rep_id) if o and o.rep_id else None
    draft, was_ai = compose(db, reason, contact, title.name if title else "", alts[0] if alts else None, _sender(db, rep))
    company = db.get(Company, contact.company_id) if contact.company_id else None
    email = db.scalars(select(Email.address).where(Email.contact_id == contact.id).limit(1)).first()
    name = contact.full_name or contact.first_name or "a contact"
    details = [
        {"key": "reason", "label": "Why they said no", "value": REASON_LABELS.get(reason, reason)},
        {"key": "said", "label": "What they said", "value": signal.summary},
        {"key": "contact", "label": "Contact", "value": name, "href": f"/contacts/{contact.id}"},
    ]
    if company:
        details.append({"key": "company", "label": "Company", "value": company.name, "href": f"/companies/{company.id}"})
    if o:
        details.append({"key": "last", "label": "Last booking", "value": f"{title.name} {ed.name} · {o.size or 'booking'} · {_money(o.value_gbp)}",
                        "href": f"/sales/orders/{o.id}"})
    if alts:
        details.append({"key": "offer", "label": "Suggested offer", "value": alts[0]["label"], "href": alts[0]["href"]})
        if len(alts) > 1:
            details.append({"key": "others", "label": "Other options", "value": " · ".join(a["label"] for a in alts[1:])})
    else:
        details.append({"key": "offer", "label": "Suggested offer", "value": "None - the reply just acknowledges and asks"})
    details.append({"key": "draft_source", "label": "Draft", "value": "From the template, polished by AI" if was_ai else "From the template"})
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=contact.source_db, entity_type="contact", entity_id=contact.id,
        payload={
            "summary": f"{name}{f' ({company.name})' if company else ''} said no - {REASON_LABELS.get(reason, reason).lower()}",
            "details": details, "original_text": draft, "original_label": "Draft reply", "source_context": signal.source_snippet,
            "related_entities": [{"type": "contact", "id": str(contact.id), "label": name}],
            "signal_id": str(signal.id), "reason": reason, "alternatives": alts, "alt_index": 0,
            "suggested_to": email, "title_name": title.name if title else None, "sender": _sender(db, rep),
            "owner_user_id": str(rep.user_id) if rep and rep.user_id else None,
            "facets": {"salesperson": rep.name if rep else "No salesperson", "title": title.name if title else "No past booking",
                       "reason": REASON_LABELS.get(reason, reason)},
            "sort_date": (signal.created_at or datetime.now(timezone.utc)).date().isoformat(),
            "dedupe_key": f"save_the_sale:{signal.id}",
        })
    db.add(item)
    return item


def scan_declines() -> None:
    db = SessionLocal()
    try:
        ensure_templates(db)
        queued_for = set(db.scalars(select(ReviewQueueItem.payload["signal_id"].astext).where(ReviewQueueItem.kind == KIND)))
        n = 0
        cap = runtime_settings.get_int(db, "save_the_sale_max_per_run")
        for s in db.scalars(select(EmailSignal).where(EmailSignal.signal_type == "decline", EmailSignal.status == "open")
                            .order_by(EmailSignal.created_at)):
            if str(s.id) in queued_for or n >= cap:
                continue
            if queue_for_signal(db, s):
                n += 1
        db.commit()
        logger.info("save the sale: %d reply draft(s) queued", n)
    finally:
        db.close()


def _note(db: Session, item: ReviewQueueItem, body: str, note_type: str) -> None:
    db.add(Note(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type="contact",
                entity_id=item.entity_id, note_type=note_type, body=body, act_created_at=datetime.now(timezone.utc)))


def _close_signal(db: Session, item: ReviewQueueItem, status: str) -> None:
    s = db.get(EmailSignal, uuid.UUID(item.payload["signal_id"])) if item.payload.get("signal_id") else None
    if s:
        s.status = status


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    from app.automations.sales_orders import _split_draft

    draft = (input_data.get("note") or "").strip() or item.payload.get("original_text") or ""
    reason = REASON_LABELS.get(item.payload.get("reason"), "")
    if action_id == "send":
        from app.models.messaging import MailAccount
        from app.services import outlook
        from app.services.mail_merge import to_html

        to = (input_data.get("to") or item.payload.get("suggested_to") or "").strip()
        if not re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", to):
            raise ValueError("Enter the email address to send this to.")
        actor = input_data.get("_actor_user_id")
        acct = db.scalar(select(MailAccount).where(MailAccount.user_id == uuid.UUID(actor))) if actor else None
        if not acct:
            raise ValueError("Connect your Outlook first (Settings › Email), or use “Log to CRM only” and send it yourself.")
        subject, body = _split_draft(draft)
        try:
            outlook.send_mail(db, acct, to=[to], subject=subject or "Thank you", html_body=to_html(body))
        except outlook.OutlookAuthError as exc:
            raise ValueError(f"{exc} Reconnect Outlook in Settings, then try again.") from exc
        except outlook.RateLimited as exc:
            raise ValueError("Outlook is asking us to slow down - try again in a minute.") from exc
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc
        _note(db, item, f"Save-the-sale reply sent to {to} ({reason}).\n\n{draft}", "Save the sale")
        _close_signal(db, item, "actioned")
    elif action_id == "approve":
        _note(db, item, f"Save-the-sale reply ({reason}), sent outside BMI Brain.\n\n{draft}", "Save the sale")
        _close_signal(db, item, "actioned")
    elif action_id == "let_go":
        why = (input_data.get("note") or "").strip()
        _note(db, item, f"Declined: {reason}." + (f" {why}" if why else ""), "Declined")
        _close_signal(db, item, "dismissed")
    else:
        raise ValueError(f"Unknown action {action_id!r} for {KIND}")


def _redraft(db: Session, item: ReviewQueueItem, extra: str) -> str:
    """Regenerate: an instruction naming another option ("offer the newsletter") switches to it; otherwise the next option."""
    p = item.payload
    alts = p.get("alternatives") or []
    idx = int(p.get("alt_index") or 0)
    low = (extra or "").lower()
    pick = next((i for i, a in enumerate(alts) if low and any(w in low for w in a["label"].lower().split()[:2] if len(w) > 3)), None)
    if pick is None and alts:
        pick = (idx + 1) % len(alts) if not extra else idx
    contact = db.get(Contact, item.entity_id)
    alt = alts[pick] if alts and pick is not None else None
    draft, _ = compose(db, p.get("reason") or "other", contact, p.get("title_name") or "", alt, p.get("sender") or "", extra)
    details = [d for d in p.get("details", []) if d.get("key") != "offer"]
    if alt:
        details.insert(4, {"key": "offer", "label": "Suggested offer", "value": alt["label"], "href": alt["href"]})
    item.payload = {**p, "alt_index": pick or 0, "details": details}
    return draft


register(ReviewKind(
    kind=KIND,
    label="Save the sale",
    description="A client said no by email - with a drafted reply that acknowledges it, asks why, and offers a sensible alternative from the rate card or editorial plan.",
    actions=[
        ReviewAction(id="send", label="Send from my Outlook", style="primary", outcome="approved",
                     extra_fields=[ExtraField(key="to", label="Send to", placeholder="name@company.com", required=False)]),
        ReviewAction(id="approve", label="Log to CRM only", style="secondary", outcome="approved"),
        ReviewAction(id="let_go", label="Let it go", style="secondary", outcome="rejected"),
    ],
    handler=_handle,
    redraft=_redraft,
    audience="sales",
    facets=(("salesperson", "Salesperson"), ("title", "Title"), ("reason", "Why they said no")),
    date_sort_label="when they said no",
))

register_job(ScheduledJob(
    id="save_the_sale_scan", label="Save the sale",
    description="Every 30 minutes: turns each client \"no\" found in the email scan into a drafted save-the-sale reply in the Review Queue.",
    cron="*/30 * * * *", func=scan_declines, enabled_flag="automations_save_the_sale_enabled",
))
