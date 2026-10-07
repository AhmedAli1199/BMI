"""Proposal builder (SALES-020) and proposal logging (SALES-009).

A salesperson picks a client, a title and products from the rate card; the
brain drafts the wording (never the figures); they edit, download the Word
document, and "mark as sent" logs it on the client with a follow-up
reminder. Nothing is ever sent from here.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.api.schemas import MANUAL_SOURCE_DB
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Company, Contact, Email, Note, SalesRate, SalesTitle, User
from app.models.messaging import MailAccount
from app.services import mail_merge as mm
from app.services import outlook
from app.models.messaging import Reminder
from app.models.proposal import PROPOSAL_TEMPLATES, Proposal
from app.proposals import context as ctx_mod
from app.proposals import drafting
from app.proposals.docx_builder import TEMPLATE_LABELS, build_docx, template_for_slug
from app.roles import CAN_USE_AUTOMATIONS

router = APIRouter(prefix="/proposals", tags=["proposals"])


class LineIn(BaseModel):
    id: str | None = None
    product: str = Field(min_length=1, max_length=200)
    qty: int = Field(default=1, ge=1, le=999)
    unit_price: float | None = Field(default=None, ge=0)
    source: str = "manual"  # rate_card | manual
    rate_id: uuid.UUID | None = None


class SectionIn(BaseModel):
    id: str | None = None
    kind: str = "custom"
    heading: str = Field(max_length=200)
    body: str = ""


class ProposalCreate(BaseModel):
    company_id: uuid.UUID
    contact_id: uuid.UUID | None = None
    title_id: uuid.UUID | None = None
    template: str | None = None
    campaign_name: str | None = None
    year: int | None = None
    lines: list[LineIn] = []
    use_ai: bool = True


class ProposalPatch(BaseModel):
    campaign_name: str | None = Field(default=None, max_length=200)
    template: str | None = None
    contact_id: uuid.UUID | None = None
    lines: list[LineIn] | None = None
    sections: list[SectionIn] | None = None
    notes: str | None = None


class RedraftIn(BaseModel):
    use_ai: bool = True


class FinishIn(BaseModel):
    via: str = "downloaded"
    follow_up_days: int = Field(default=14, ge=0, le=365)


class SendIn(BaseModel):
    to: list[str] = Field(min_length=1, max_length=10)
    cc: list[str] = []
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    follow_up_days: int = Field(default=14, ge=0, le=365)


class EmailDraft(BaseModel):
    to: list[str]
    subject: str
    body: str
    outlook_connected: bool
    outlook_email: str | None
    contact_name: str | None


class ProposalOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    contact_id: uuid.UUID | None
    title_id: uuid.UUID | None
    title_name: str | None
    template: str
    template_label: str
    campaign_name: str
    status: str
    sections: list[dict]
    lines: list[dict]
    total_gbp: float
    context: dict
    flags: list[str]
    drafted_by: str
    created_by: str | None
    created_at: datetime
    sent_at: datetime | None
    sent_via: str | None
    follow_up_due: datetime | None = None
    notes: str | None


def _is_staff(identity: Identity) -> bool:
    return not identity.is_known or identity.role in CAN_USE_AUTOMATIONS


def _out(db: Session, p: Proposal) -> ProposalOut:
    company = db.get(Company, p.company_id)
    title = db.get(SalesTitle, p.title_id) if p.title_id else None
    user = db.get(User, p.created_by_user_id) if p.created_by_user_id else None
    rem = db.get(Reminder, p.follow_up_reminder_id) if p.follow_up_reminder_id else None
    return ProposalOut(
        id=p.id, company_id=p.company_id, company_name=company.name if company else "", contact_id=p.contact_id,
        title_id=p.title_id, title_name=title.name if title else None, template=p.template,
        template_label=TEMPLATE_LABELS.get(p.template, p.template), campaign_name=p.campaign_name, status=p.status,
        sections=p.sections, lines=p.lines, total_gbp=float(p.total_gbp), context=p.context, flags=p.flags,
        drafted_by=p.drafted_by, created_by=user.name if user else None, created_at=p.created_at, sent_at=p.sent_at,
        sent_via=p.sent_via, follow_up_due=rem.due_at if rem and rem.status == "open" else None, notes=p.notes,
    )


def _price_lines(db: Session, lines: list[LineIn], title_id: uuid.UUID | None, year: int) -> list[dict]:
    """Rate-card lines are always priced from the rate card, whatever the
    browser sent. Manual lines keep the price the salesperson typed."""
    out = []
    for ln in lines:
        if ln.source == "rate_card":
            rate = db.get(SalesRate, ln.rate_id) if ln.rate_id else None
            if rate is None and title_id:
                rate = db.scalars(select(SalesRate).where(SalesRate.title_id == title_id, SalesRate.year == year,
                                                          SalesRate.product == ln.product)).first()
            if rate is None:
                raise HTTPException(422, f"“{ln.product}” isn't on the rate card - add it as a manual line instead.")
            if rate.price_gbp is None:
                raise HTTPException(422, f"“{rate.product}” is priced on request - add it as your own line with the price you've agreed.")
            out.append({"id": ln.id or str(uuid.uuid4()), "product": rate.product, "qty": ln.qty,
                        "unit_price": float(rate.price_gbp), "source": "rate_card"})
        else:
            if ln.unit_price is None:
                raise HTTPException(422, f"Add a price for “{ln.product}”.")
            out.append({"id": ln.id or str(uuid.uuid4()), "product": ln.product.strip(), "qty": ln.qty,
                        "unit_price": round(ln.unit_price, 2), "source": "manual"})
    return out


def _total(lines: list[dict]) -> float:
    return round(sum(ln["qty"] * ln["unit_price"] for ln in lines), 2)


def _get(db: Session, pid: uuid.UUID, user: User, identity: Identity) -> Proposal:
    p = db.get(Proposal, pid)
    if not p or (not _is_staff(identity) and p.created_by_user_id != user.id):
        raise HTTPException(404, "Proposal not found")
    return p


def _draft(db: Session, p: Proposal, *, use_ai: bool) -> None:
    company = db.get(Company, p.company_id)
    title = db.get(SalesTitle, p.title_id) if p.title_id else None
    year = (p.context or {}).get("year") or date.today().year
    ctx, flags = ctx_mod.build_context(db, company, title, year)
    wording, by = drafting.draft_sections(ctx, p.lines, p.campaign_name, use_ai=use_ai)
    if not p.lines:
        flags.append("No products added yet - add some from the rate card so the Investment section has prices.")
    p.context, p.flags, p.drafted_by = ctx, flags, by
    p.sections = drafting.default_sections(wording)


@router.post("", response_model=ProposalOut, status_code=201)
def create_proposal(payload: ProposalCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ProposalOut:
    company = db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    title = db.get(SalesTitle, payload.title_id) if payload.title_id else None
    if payload.title_id and not title:
        raise HTTPException(422, "Unknown title")
    year = payload.year or date.today().year
    template = payload.template or template_for_slug(title.slug if title else None)
    if template not in PROPOSAL_TEMPLATES:
        raise HTTPException(422, "Unknown template")
    lines = _price_lines(db, payload.lines, payload.title_id, year)
    p = Proposal(id=uuid.uuid4(), company_id=company.id, contact_id=payload.contact_id, title_id=payload.title_id,
                 template=template, campaign_name=(payload.campaign_name or f"{company.name} {year}/{str(year + 1)[2:]}").strip(),
                 status="draft", lines=lines, total_gbp=_total(lines), context={"year": year}, flags=[], sections=[],
                 created_by_user_id=user.id)
    _draft(db, p, use_ai=payload.use_ai)
    db.add(p)
    db.commit()
    return _out(db, p)


@router.get("", response_model=list[ProposalOut])
def list_proposals(company_id: uuid.UUID | None = None, db: Session = Depends(get_db), user: User = Depends(current_user),
                   identity: Identity = Depends(get_identity)) -> list[ProposalOut]:
    q = select(Proposal)
    if company_id:
        q = q.where(Proposal.company_id == company_id)
    if not _is_staff(identity):
        q = q.where(Proposal.created_by_user_id == user.id)
    return [_out(db, p) for p in db.scalars(q.order_by(Proposal.created_at.desc()).limit(200))]


@router.get("/{pid}", response_model=ProposalOut)
def get_proposal(pid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user),
                 identity: Identity = Depends(get_identity)) -> ProposalOut:
    return _out(db, _get(db, pid, user, identity))


@router.patch("/{pid}", response_model=ProposalOut)
def update_proposal(pid: uuid.UUID, payload: ProposalPatch, db: Session = Depends(get_db), user: User = Depends(current_user),
                    identity: Identity = Depends(get_identity)) -> ProposalOut:
    p = _get(db, pid, user, identity)
    if payload.campaign_name is not None and payload.campaign_name.strip():
        p.campaign_name = payload.campaign_name.strip()
    if payload.template is not None:
        if payload.template not in PROPOSAL_TEMPLATES:
            raise HTTPException(422, "Unknown template")
        p.template = payload.template
    if "contact_id" in payload.model_fields_set:
        p.contact_id = payload.contact_id
    if payload.lines is not None:
        p.lines = _price_lines(db, payload.lines, p.title_id, (p.context or {}).get("year") or date.today().year)
        p.total_gbp = _total(p.lines)
    if payload.sections is not None:
        p.sections = [{"id": s.id or str(uuid.uuid4()), "kind": s.kind, "heading": s.heading.strip(), "body": s.body}
                      for s in payload.sections]
    if "notes" in payload.model_fields_set:
        p.notes = payload.notes
    db.commit()
    return _out(db, p)


@router.post("/{pid}/redraft", response_model=ProposalOut)
def redraft(pid: uuid.UUID, payload: RedraftIn, db: Session = Depends(get_db), user: User = Depends(current_user),
            identity: Identity = Depends(get_identity)) -> ProposalOut:
    """Rewrites every section from scratch - edits made on screen are replaced."""
    p = _get(db, pid, user, identity)
    _draft(db, p, use_ai=payload.use_ai)
    db.commit()
    return _out(db, p)


@router.get("/{pid}/download")
def download(pid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user),
             identity: Identity = Depends(get_identity)) -> Response:
    p = _get(db, pid, user, identity)
    data = build_docx(template=p.template, campaign_name=p.campaign_name, sections=p.sections, lines=p.lines, total=float(p.total_gbp))
    safe = "".join(c for c in p.campaign_name if c.isalnum() or c in " -_/").replace("/", "-").strip() or "Proposal"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{safe} proposal.docx"'})


def _log_sent(db: Session, p: Proposal, user: User, via: str, follow_up_days: int, sent_to: list[str] | None = None) -> None:
    """Notes the proposal on the client ("Proposal sent" with the figures) and sets the follow-up reminder."""
    now = datetime.now(timezone.utc)
    company = db.get(Company, p.company_id)
    products = "; ".join(f"{ln['product']} x{ln['qty']} at {ctx_mod.gbp(ln['unit_price'])}" for ln in p.lines) or "no products listed"
    body = f"Proposal sent: {p.campaign_name}. {products}. Total {ctx_mod.gbp(float(p.total_gbp))} before VAT."
    if sent_to:
        body += f" Emailed to {', '.join(sent_to)} from Outlook."
    note = Note(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type="company",
                entity_id=p.company_id, note_type="Proposal sent", body=body, act_created_at=now, created_by_user_id=user.id)
    db.add(note)
    reminder = Reminder(id=uuid.uuid4(), user_id=user.id, contact_id=p.contact_id, company_id=p.company_id,
                        due_at=now + timedelta(days=follow_up_days),
                        note=f"Follow up on the proposal sent to {company.name}: {p.campaign_name}.", email_me=True, status="open")
    db.add(reminder)
    db.flush()
    p.status, p.sent_at, p.sent_via = "sent", now, via
    p.logged_note_id, p.follow_up_reminder_id = note.id, reminder.id


@router.post("/{pid}/finish", response_model=ProposalOut)
def finish(pid: uuid.UUID, payload: FinishIn, db: Session = Depends(get_db), user: User = Depends(current_user),
           identity: Identity = Depends(get_identity)) -> ProposalOut:
    """For a proposal sent some other way: logs it on the client and sets the follow-up reminder."""
    p = _get(db, pid, user, identity)
    if p.status == "sent":
        raise HTTPException(409, "This proposal is already logged as sent.")
    if payload.via not in ("downloaded", "other"):
        raise HTTPException(422, "Unknown way of sending")
    _log_sent(db, p, user, payload.via, payload.follow_up_days)
    db.commit()
    return _out(db, p)


@router.get("/{pid}/email-draft", response_model=EmailDraft)
def email_draft(pid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user),
                identity: Identity = Depends(get_identity)) -> EmailDraft:
    """A starting email for the rep to edit: the contact's address, a plain subject and short note."""
    p = _get(db, pid, user, identity)
    contact = db.get(Contact, p.contact_id) if p.contact_id else None
    to: list[str] = []
    if contact:
        addr = db.scalars(select(Email.address).where(Email.contact_id == contact.id).order_by(Email.is_primary.desc())).first()
        if addr:
            to = [addr]
    first = (contact.first_name if contact and contact.first_name else None)
    sign = (user.name or "").strip()
    body = (f"Hi {first or 'there'},\n\nThank you for your time. I've attached our proposal for {p.campaign_name}, "
            f"with everything we discussed. Do have a look and let me know if you'd like to change anything - "
            f"I'm happy to talk it through.\n\nKind regards,\n{sign}")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id))
    return EmailDraft(to=to, subject=f"Proposal: {p.campaign_name}", body=body, outlook_connected=bool(acct),
                      outlook_email=acct.email if acct else None,
                      contact_name=(contact.full_name if contact else None))


@router.post("/{pid}/send", response_model=ProposalOut)
def send_from_outlook(pid: uuid.UUID, payload: SendIn, db: Session = Depends(get_db), user: User = Depends(current_user),
                      identity: Identity = Depends(get_identity)) -> ProposalOut:
    """Sends the proposal from the rep's own Outlook with the Word file attached, then logs it. Only runs
    when the rep presses Send - nothing is ever sent automatically."""
    p = _get(db, pid, user, identity)
    if p.status == "sent":
        raise HTTPException(409, "This proposal is already logged as sent.")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id))
    if not acct:
        raise HTTPException(409, "Connect your Outlook first (Settings > Email) - proposals are sent from your own account.")
    for a in [*payload.to, *payload.cc]:
        if "@" not in a or " " in a.strip():
            raise HTTPException(422, f"“{a}” doesn't look like an email address.")
    data = build_docx(template=p.template, campaign_name=p.campaign_name, sections=p.sections, lines=p.lines, total=float(p.total_gbp))
    if len(data) > 3 * 1024 * 1024:
        raise HTTPException(413, "The Word file is over 3 MB, which Outlook can't send in one go. Download it and attach it yourself.")
    safe = "".join(c for c in p.campaign_name if c.isalnum() or c in " -_").strip() or "Proposal"
    try:
        outlook.send_mail(db, acct, to=[a.strip() for a in payload.to], cc=[a.strip() for a in payload.cc], subject=payload.subject,
                          html_body=mm.to_html(payload.body),
                          attachments=[(f"{safe} proposal.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", data)])
    except outlook.OutlookAuthError as exc:
        raise HTTPException(409, str(exc))
    except outlook.RateLimited:
        raise HTTPException(429, "Outlook is asking us to slow down - try again in a minute.")
    except Exception as exc:
        raise HTTPException(502, f"Outlook didn't accept the message: {exc}")
    _log_sent(db, p, user, "outlook", payload.follow_up_days, sent_to=[a.strip() for a in payload.to])
    db.commit()
    return _out(db, p)


@router.delete("/{pid}", status_code=204, response_model=None)
def delete_draft(pid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user),
                 identity: Identity = Depends(get_identity)) -> None:
    p = _get(db, pid, user, identity)
    if p.status == "sent":
        raise HTTPException(409, "A sent proposal is kept on record and can't be deleted.")
    db.delete(p)
    db.commit()
