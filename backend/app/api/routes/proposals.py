"""Proposal builder (SALES-020) and proposal logging (SALES-009).

A salesperson picks a client, a title and products from the rate card; the
brain drafts the wording (never the figures); they edit, download the Word
document, and "mark as sent" logs it on the client with a follow-up
reminder. Nothing is ever sent from here.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.api.schemas import MANUAL_SOURCE_DB
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Company, Contact, Email, Note, SalesEdition, SalesRate, SalesTitle, User
from app.models.messaging import MailAccount
from app.services import mail_merge as mm
from app.services import outlook
from app.models.messaging import Reminder
from app.models.proposal import PROPOSAL_TEMPLATES, Proposal
from app.proposals import context as ctx_mod
from app.proposals import blocks, drafting
from app.proposals import render as rnd
from app.proposals import pricing
from app.proposals.docx_builder import TEMPLATE_LABELS, build_docx, template_for_slug
from app.roles import CAN_USE_AUTOMATIONS
from app.sales.editorial import issue_facts, next_issue
from app.sales.offers import apply_offers

router = APIRouter(prefix="/proposals", tags=["proposals"])


class LineIn(BaseModel):
    id: str | None = None
    product: str = Field(min_length=1, max_length=200)
    qty: int = Field(default=1, ge=1, le=999)
    unit_price: float | None = Field(default=None, ge=0)
    source: str = "manual"  # rate_card | manual | offer (offer lines are worked out here, so the browser's copy is ignored)
    rate_id: uuid.UUID | None = None
    title_id: uuid.UUID | None = None          # a line can be for another title (newsletter, awards) than the proposal's
    issues: list[uuid.UUID] = Field(default_factory=list, max_length=24)   # the issues it runs in (sets the quantity)
    discount_pct: float = Field(default=0, ge=0, le=1)
    option: str | None = Field(default=None, max_length=80)   # "Option A: one issue" - lines without one are in every option


class BlockIn(BaseModel):
    kind: str = Field(pattern="^(package|prices|stats|issues|events|examples)$")
    config: dict = Field(default_factory=dict)


class SectionIn(BaseModel):
    id: str | None = None
    kind: str = "custom"
    heading: str = Field(max_length=200)
    body: str = ""
    html: str | None = Field(default=None, max_length=6_000_000)   # rich text from the editor (pictures included)
    block: BlockIn | None = None                                    # a ready-made block instead of text


class ProposalCreate(BaseModel):
    company_id: uuid.UUID
    contact_id: uuid.UUID | None = None
    title_id: uuid.UUID | None = None
    edition_id: uuid.UUID | None = None  # none -> the title's next issue that's still open for bookings
    template: str | None = None
    campaign_name: str | None = None
    year: int | None = None
    lines: list[LineIn] = []
    use_ai: bool = True
    kind: str = Field(default="issue", pattern="^(issue|multi|annual|digital|sponsorship|mixed)$")
    discount_pct: float = Field(default=0, ge=0, le=1)


class ProposalPatch(BaseModel):
    campaign_name: str | None = Field(default=None, max_length=200)
    template: str | None = None
    contact_id: uuid.UUID | None = None
    edition_id: uuid.UUID | None = None
    lines: list[LineIn] | None = None
    sections: list[SectionIn] | None = None
    notes: str | None = None
    kind: str | None = Field(default=None, pattern="^(issue|multi|annual|digital|sponsorship|mixed)$")
    discount_pct: float | None = Field(default=None, ge=0, le=1)
    output: str | None = Field(default=None, pattern="^(word|email)$")


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
    as_body: bool = False      # the proposal itself is the email (body = a short opening line above it)
    attach_word: bool = True   # also attach the Word document


class EmailDraft(BaseModel):
    to: list[str]
    subject: str
    body: str
    outlook_connected: bool
    outlook_email: str | None
    contact_name: str | None
    output: str = "word"


class ProposalOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    contact_id: uuid.UUID | None
    title_id: uuid.UUID | None
    title_name: str | None
    edition_id: uuid.UUID | None = None
    issue: dict | None = None
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
    kind: str = "issue"
    kind_label: str = ""
    discount_pct: float = 0
    totals: list[dict] = []          # one per option (or a single one)
    titles: list[str] = []           # every title the lines are for
    kinds: dict[str, str] = {}
    output: str = "word"
    brand: str | None = None
    request_item_id: uuid.UUID | None = None


def _is_staff(identity: Identity) -> bool:
    return not identity.is_known or identity.role in CAN_USE_AUTOMATIONS


def _out(db: Session, p: Proposal) -> ProposalOut:
    company = db.get(Company, p.company_id)
    title = db.get(SalesTitle, p.title_id) if p.title_id else None
    user = db.get(User, p.created_by_user_id) if p.created_by_user_id else None
    rem = db.get(Reminder, p.follow_up_reminder_id) if p.follow_up_reminder_id else None
    return ProposalOut(
        id=p.id, company_id=p.company_id, company_name=company.name if company else "", contact_id=p.contact_id,
        title_id=p.title_id, title_name=title.name if title else None, edition_id=p.edition_id,
        issue=(p.context or {}).get("issue"), template=p.template,
        template_label=TEMPLATE_LABELS.get(p.template, p.template), campaign_name=p.campaign_name, status=p.status,
        sections=p.sections, lines=p.lines, total_gbp=float(p.total_gbp), context=p.context, flags=[*p.flags, *((p.context or {}).get("offer_notes") or [])],
        drafted_by=p.drafted_by, created_by=user.name if user else None, created_at=p.created_at, sent_at=p.sent_at,
        sent_via=p.sent_via, follow_up_due=rem.due_at if rem and rem.status == "open" else None, notes=p.notes,
        kind=p.kind or "issue", kind_label=pricing.KINDS.get(p.kind or "issue", ""), discount_pct=float(p.discount_pct or 0),
        totals=pricing.totals(p.lines or [], float(p.discount_pct or 0)), titles=pricing.title_names(db, p.lines or []), kinds=pricing.KINDS,
        output=p.output or "word", brand=(b.key if (b := blocks.brand_of(db, p.title_id)) else None), request_item_id=p.request_item_id,
    )


def _set_lines(db: Session, p: Proposal, lines: list[LineIn], year: int) -> None:
    """Prices the lines (rate card prices always from the rate card), adds any rate-card offers they qualify for
    (e.g. "book 3, save 20%"), and works out each option's total."""
    priced, notes = pricing.price_lines(db, [ln.model_dump(mode="json") for ln in lines], p.title_id, year)
    p.lines, p.total_gbp = priced, pricing.headline_total(priced, float(p.discount_pct or 0))
    p.context = {**(p.context or {}), "offer_notes": notes}


def _edition_for(db: Session, title: SalesTitle | None, edition_id: uuid.UUID | None) -> SalesEdition | None:
    if not edition_id:
        return None
    e = db.get(SalesEdition, edition_id)
    if not e or (title and e.title_id != title.id):
        raise HTTPException(422, "That issue isn't one of this title's issues.")
    return e


def _get(db: Session, pid: uuid.UUID, user: User, identity: Identity) -> Proposal:
    p = db.get(Proposal, pid)
    if not p or (not _is_staff(identity) and p.created_by_user_id != user.id):
        raise HTTPException(404, "Proposal not found")
    return p


def _draft(db: Session, p: Proposal, *, use_ai: bool) -> None:
    company = db.get(Company, p.company_id)
    title = db.get(SalesTitle, p.title_id) if p.title_id else None
    year = (p.context or {}).get("year") or date.today().year
    edition = db.get(SalesEdition, p.edition_id) if p.edition_id else None
    ctx, flags = ctx_mod.build_context(db, company, title, year, edition)
    ctx["offer_notes"] = (p.context or {}).get("offer_notes") or []
    ctx["kind"], ctx["kind_label"] = p.kind or "issue", pricing.KINDS.get(p.kind or "issue")
    ctx["titles"] = pricing.title_names(db, p.lines or [])
    ctx["discount_pct"] = float(p.discount_pct or 0)
    ctx["totals"] = pricing.totals(p.lines or [], ctx["discount_pct"])
    # Every issue the lines run in (from the editorial plan), so the wording can name them.
    seen = list(dict.fromkeys(i for ln in p.lines or [] for i in ln.get("issues") or []))[:8]
    eds = [e for e in (db.get(SalesEdition, uuid.UUID(i)) for i in seen) if e]
    eds.sort(key=lambda e: (e.edition_date is None, e.edition_date))
    ctx["issues"] = [issue_facts(db, e) for e in eds]
    if (p.context or {}).get("issue_auto") and edition:
        ctx["issue_auto"] = True
        flags.insert(0, f"We picked {ctx['issue']['label']}, the next one still open for bookings - change it if the client wants a different one.")
    from app.proposals import style
    prof = style.effective(db, p.created_by_user_id)
    if prof.get("_personal"):
        ctx["style"] = f"{prof['summary']} Tone: {prof['tone']}. Length: {prof['length']}." + (f" Never: {'; '.join(prof['never'])}." if prof["never"] else "") \
            + (f" Always: {'; '.join(prof['always'])}." if prof["always"] else "")
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
    edition = _edition_for(db, title, payload.edition_id)
    auto = False
    if edition is None and title:
        edition = next_issue(db, title.id)
        auto = edition is not None
    p = Proposal(id=uuid.uuid4(), company_id=company.id, contact_id=payload.contact_id, title_id=payload.title_id,
                 edition_id=edition.id if edition else None,
                 template=template, campaign_name=(payload.campaign_name or f"{company.name} {year}/{str(year + 1)[2:]}").strip(),
                 status="draft", lines=[], total_gbp=0, context={"year": year, "issue_auto": auto}, flags=[], sections=[],
                 created_by_user_id=user.id, kind=payload.kind, discount_pct=payload.discount_pct)
    _set_lines(db, p, payload.lines, year)
    _draft(db, p, use_ai=payload.use_ai)
    _apply_style(db, p, user)
    db.add(p)
    db.commit()
    return _out(db, p)


_BLOCK_FOR_ITEM = {"stats": "stats", "prices": "prices", "examples": "examples", "issues": "issues", "events": "events"}


def _apply_style(db: Session, p: Proposal, user: User, *, standard: bool = False) -> None:
    """Shapes a new proposal the way its writer works (app/proposals/style.py): email or Word, and the ready-made
    blocks they use, in their order, after the drafted wording. Remembers which blocks it started with, so what
    they take out can be learned."""
    from app.proposals import style
    prof = style.effective(db, user.id)
    if not prof.get("_personal") and not standard:
        return   # no profile yet: proposals look as they always have
    sit = style.situation(prof, "full_proposal")
    p.output = prof["output"]
    blocks_now = []
    for item in sit["include"]:
        kind = _BLOCK_FOR_ITEM.get(item)
        if kind:
            blocks_now.append({"id": str(uuid.uuid4()), "kind": f"block_{kind}", "heading": blocks.BLOCKS[kind] if kind != "stats" else "Key statistics",
                               "body": "", "block": {"kind": kind, "config": {}}})
    if blocks_now:
        secs = list(p.sections or [])
        at = next((i for i, x in enumerate(secs) if x.get("kind") == "next_steps"), len(secs))
        p.sections = secs[:at] + blocks_now + secs[at:]
    p.context = {**(p.context or {}), "initial_blocks": [b["block"]["kind"] for b in blocks_now]}


def _learn_from(db: Session, p: Proposal, user: User) -> None:
    from app.proposals import style
    start = set((p.context or {}).get("initial_blocks") or [])
    now = {(s.get("block") or {}).get("kind") for s in p.sections or [] if s.get("block")}
    gone = [item for item, kind in _BLOCK_FOR_ITEM.items() if kind in start and kind not in now]
    style.record_edit(db, user.id, kind="proposal", situation="full_proposal", removed=gone)


@router.get("", response_model=list[ProposalOut])
def list_proposals(company_id: uuid.UUID | None = None, limit: int = Query(default=200, ge=1, le=2000), offset: int = Query(default=0, ge=0),
                   db: Session = Depends(get_db), user: User = Depends(current_user),
                   identity: Identity = Depends(get_identity)) -> list[ProposalOut]:
    """Newest first, a page at a time (the list page asks for one more than it shows, to know if there are more)."""
    q = select(Proposal)
    if company_id:
        q = q.where(Proposal.company_id == company_id)
    if not _is_staff(identity):
        q = q.where(Proposal.created_by_user_id == user.id)
    return [_out(db, p) for p in db.scalars(q.order_by(Proposal.created_at.desc(), Proposal.id).limit(limit).offset(offset))]


@router.get("/{pid}", response_model=ProposalOut)
def get_proposal(pid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user),
                 identity: Identity = Depends(get_identity)) -> ProposalOut:
    return _out(db, _get(db, pid, user, identity))


@router.patch("/{pid}", response_model=ProposalOut)
def update_proposal(pid: uuid.UUID, payload: ProposalPatch, db: Session = Depends(get_db), user: User = Depends(current_user),
                    identity: Identity = Depends(get_identity)) -> ProposalOut:
    p = _get(db, pid, user, identity)
    if p.status == "sent" and payload.model_fields_set - {"notes"}:
        raise HTTPException(409, "This proposal has been sent, so it can't be changed. You can still add notes.")
    if payload.campaign_name is not None and payload.campaign_name.strip():
        p.campaign_name = payload.campaign_name.strip()
    if payload.template is not None:
        if payload.template not in PROPOSAL_TEMPLATES:
            raise HTTPException(422, "Unknown template")
        p.template = payload.template
    if "contact_id" in payload.model_fields_set:
        p.contact_id = payload.contact_id
    if "edition_id" in payload.model_fields_set:
        title = db.get(SalesTitle, p.title_id) if p.title_id else None
        edition = _edition_for(db, title, payload.edition_id)
        p.edition_id = edition.id if edition else None
        # The wording isn't rewritten (it may have been edited) - the screen offers a redraft.
        p.context = {**(p.context or {}), "issue": issue_facts(db, edition) if edition else None, "issue_auto": False}
        p.flags = [f for f in p.flags if not f.startswith("We picked ")]
    if payload.kind is not None:
        p.kind = payload.kind
    if payload.discount_pct is not None:
        p.discount_pct = payload.discount_pct
    if payload.lines is not None:
        _set_lines(db, p, payload.lines, (p.context or {}).get("year") or date.today().year)
    p.total_gbp = pricing.headline_total(p.lines or [], float(p.discount_pct or 0))
    if payload.output is not None:
        p.output = payload.output
    if payload.sections is not None:
        p.sections = [_section(s) for s in payload.sections]
    if "notes" in payload.model_fields_set:
        p.notes = payload.notes
    db.commit()
    return _out(db, p)


def _section(s: SectionIn) -> dict:
    out = {"id": s.id or str(uuid.uuid4()), "kind": s.kind, "heading": s.heading.strip(), "body": s.body}
    if s.block:
        out["block"] = s.block.model_dump()
        out["kind"] = f"block_{s.block.kind}"
    elif s.html is not None:
        out["html"] = rnd.clean_html(s.html)
        out["body"] = mm.to_text(out["html"]).strip()   # kept for the AI's instructions and older screens
    return out


class PreviewOut(BaseModel):
    html: str
    warnings: list[str] = []


@router.get("/{pid}/preview", response_model=PreviewOut)
def preview(pid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user),
            identity: Identity = Depends(get_identity)) -> PreviewOut:
    """The proposal exactly as it goes out (blocks filled in), and anything that may not show well in an email."""
    p = _get(db, pid, user, identity)
    body = rnd.email_html(db, p)
    return PreviewOut(html=body, warnings=rnd.email_warnings(body) if (p.output or "word") == "email" else [])


@router.post("/{pid}/block-preview", response_model=PreviewOut)
def block_preview(pid: uuid.UUID, payload: BlockIn, db: Session = Depends(get_db), user: User = Depends(current_user),
                  identity: Identity = Depends(get_identity)) -> PreviewOut:
    p = _get(db, pid, user, identity)
    return PreviewOut(html=blocks.render(db, payload.kind, payload.config, title_id=p.title_id, lines=p.lines or [],
                                         discount_pct=float(p.discount_pct or 0)))


@router.post("/{pid}/redraft", response_model=ProposalOut)
def redraft(pid: uuid.UUID, payload: RedraftIn, db: Session = Depends(get_db), user: User = Depends(current_user),
            identity: Identity = Depends(get_identity)) -> ProposalOut:
    """Rewrites every section from scratch - edits made on screen are replaced."""
    p = _get(db, pid, user, identity)
    _draft(db, p, use_ai=payload.use_ai)
    db.commit()
    return _out(db, p)


class ReviseIn(BaseModel):
    instruction: str = Field(min_length=3, max_length=4000)
    sections: list[SectionIn] | None = None  # what's on screen now (unsaved edits included)


class ReviseOut(BaseModel):
    proposal: ProposalOut
    summary: str
    previous_sections: list[dict]


class FromNotesIn(BaseModel):
    company_id: uuid.UUID
    contact_id: uuid.UUID | None = None
    title_id: uuid.UUID | None = None
    notes: str = Field(min_length=1, max_length=20000)


@router.post("/from-notes", response_model=ProposalOut, status_code=201)
def from_notes(payload: FromNotesIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ProposalOut:
    """SALES-023: a pitch from meeting notes someone types or pastes (app/proposals/pitch.py)."""
    from app.proposals import pitch
    company = db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    contact = db.get(Contact, payload.contact_id) if payload.contact_id else None
    try:
        p = pitch.make_pitch(db, user, company, payload.notes, contact=contact, title_id=payload.title_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return _out(db, p)


@router.post("/{pid}/revise", response_model=ReviseOut)
def revise(pid: uuid.UUID, payload: ReviseIn, db: Session = Depends(get_db), user: User = Depends(current_user),
           identity: Identity = Depends(get_identity)) -> ReviseOut:
    """Applies the salesperson's own instruction ("shorter intro, add a section on the Awards, friendlier tone") to the
    whole proposal. Figures still only come from the data; the previous version is returned so the screen can undo."""
    p = _get(db, pid, user, identity)
    if p.status == "sent":
        raise HTTPException(409, "This proposal has been sent, so it can't be changed.")
    current = [_section(s) for s in payload.sections] if payload.sections is not None else list(p.sections)
    text = [s for s in current if not s.get("block")]
    try:
        new, summary = drafting.revise_sections(p.context or {}, p.lines, p.campaign_name, text, payload.instruction.strip())
    except drafting.RevisionRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    # Ready-made blocks keep their place; the AI only rewrites the wording around them.
    merged, it = [], iter(new)
    for s in current:
        merged.append(s if s.get("block") else next(it, None))
    p.sections, p.drafted_by = [x for x in merged if x] + list(it), "ai"
    db.commit()
    return ReviseOut(proposal=_out(db, p), summary=summary, previous_sections=current)


@router.post("/transcribe")
async def transcribe(request: Request, user: User = Depends(current_user)) -> dict:
    """Spoken instruction to text. The browser sends the recording as the request body."""
    from app.automations import llm
    audio = await request.body()
    if not audio:
        raise HTTPException(422, "We didn't get any sound. Try again, a little closer to the microphone.")
    if len(audio) > 8 * 1024 * 1024:
        raise HTTPException(413, "That recording is too long. Keep it under a couple of minutes.")
    mime = (request.headers.get("content-type") or "audio/webm").split(";")[0]
    text = await run_in_threadpool(llm.transcribe_audio, audio, mime, purpose="proposal_voice")
    if not text:
        raise HTTPException(422, "We couldn't make out the recording. Try again, or type the change instead.")
    return {"text": text}


@router.get("/{pid}/download")
def download(pid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user),
             identity: Identity = Depends(get_identity)) -> Response:
    p = _get(db, pid, user, identity)
    data = _docx(db, p)
    safe = "".join(c for c in p.campaign_name if c.isalnum() or c in " -_/").replace("/", "-").strip() or "Proposal"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{safe} proposal.docx"'})


def _docx(db: Session, p: Proposal) -> bytes:
    return build_docx(template=p.template, campaign_name=p.campaign_name, sections=rnd.output_sections(db, p), lines=p.lines,
                      total=float(p.total_gbp), discount_pct=float(p.discount_pct or 0))


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
    _learn_from(db, p, user)
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
    if (p.output or "word") == "email":   # the proposal is the email: just the opening line above it
        body = f"Hi {first or 'there'},\n\nThank you for your time. Here's what we discussed for {p.campaign_name}."
    else:
        body = (f"Hi {first or 'there'},\n\nThank you for your time. I've attached our proposal for {p.campaign_name}, "
                f"with everything we discussed. Do have a look and let me know if you'd like to change anything - "
                f"I'm happy to talk it through.\n\nKind regards,\n{sign}")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id))
    return EmailDraft(to=to, subject=f"Proposal: {p.campaign_name}", body=body, outlook_connected=bool(acct),
                      outlook_email=acct.email if acct else None,
                      contact_name=(contact.full_name if contact else None), output=p.output or "word")


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
    safe = "".join(c for c in p.campaign_name if c.isalnum() or c in " -_").strip() or "Proposal"
    files: list[tuple] = []
    if payload.as_body:
        html_body, files = rnd.inline_images(rnd.email_html(db, p, intro=payload.body))
    else:
        html_body = mm.to_html(payload.body)
    if payload.attach_word or not payload.as_body:
        data = _docx(db, p)
        files.append((f"{safe} proposal.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", data))
    if sum(len(f[2]) for f in files) + len(html_body.encode()) > 3 * 1024 * 1024:
        raise HTTPException(413, "This is over 3 MB with its pictures, which Outlook can't send in one go. Make the pictures smaller, "
                                 "or download the Word file and attach it yourself.")
    try:
        outlook.send_mail(db, acct, to=[a.strip() for a in payload.to], cc=[a.strip() for a in payload.cc], subject=payload.subject,
                          html_body=html_body, attachments=files)
    except outlook.OutlookAuthError as exc:
        raise HTTPException(409, str(exc))
    except outlook.RateLimited:
        raise HTTPException(429, "Outlook is asking us to slow down - try again in a minute.")
    except Exception as exc:
        raise HTTPException(502, "Outlook didn't accept the email, so nothing was sent or logged. Please try again.")
    _log_sent(db, p, user, "outlook", payload.follow_up_days, sent_to=[a.strip() for a in payload.to])
    _learn_from(db, p, user)
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
