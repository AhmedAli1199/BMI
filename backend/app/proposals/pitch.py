"""SALES-023 - meeting notes to a pitch.

From a call's notes (the notetaker) or notes someone pastes, a proposal draft that answers what the client said:
1. The Brain pulls a brief out of the notes: the client's situation, the angle to take, what they responded well to,
   their own words, budget signals, which magazine and products came up - and leaves out remarks that sounded
   private or off the record. Notes too thin to pitch from are refused with a plain reason, not padded out.
2. The closest past pitches are found among proposals already sent (same magazine, same kind of business, the most
   words in common with the brief), so the draft can reuse an angle and structure that worked.
3. An ordinary proposal is built - the magazine's template, its next open issue, products picked from the rate card
   for what came up, the writer's own style and blocks - and its wording is rewritten to answer the brief. Figures
   still only come from the rate card and booking history: the brief and the past pitches reach the Brain with their
   numbers taken out, so a budget mentioned on the call or an old price can't slip in.
4. It waits in Proposals as a draft for the salesperson to tailor and send. Sending it logs it on the client as
   usual (SALES-009), and the proposal remembers the call it came from and the past pitches it drew on.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CallRecording, Company, Contact, Proposal, SalesEdition, SalesOrder, SalesTitle, User

logger = logging.getLogger("app.proposals.pitch")

MIN_NOTES = 120          # characters - less than this isn't a meeting worth pitching from
PAST_LIMIT = 3
_FIGURE = re.compile(r"[£$€]\s?\d[\d,.]*(?:\s?[kKmM]\b)?|\d[\d,.]*\s?%|\d[\d,.]*")
_WORD = re.compile(r"[a-z]{4,}")
_STOP = set("this that with from have will would could their there they them what when were been about into your ours also "
            "more some such than then very just like over only most much many each other which while where these those "
            "said says want wants need needs make made call meeting client company please thanks thank".split())

BRIEF_SYSTEM = (
    "You read a salesperson's notes from a meeting or call with a client of BMI Publishing, a UK travel and hospitality "
    "publisher (magazines, newsletters, websites, events and awards). Pull out a brief for a pitch. Return JSON with keys: "
    "enough (true only if the notes say what the client is trying to achieve or what they're interested in), "
    "situation (1-2 sentences: where the client is and what they want to achieve), "
    "angle (1 sentence: the positioning to take in the pitch), "
    "resonant_points (list of short phrases: what they responded well to), "
    "client_quotes (list: up to 3 short things the client said, in their words, only if the notes give them), "
    "budget_signals (list of short phrases about budget or timing), "
    "magazine (the BMI title discussed, or empty), "
    "wants (short phrase: the kinds of product that came up, e.g. 'print advert and newsletter'), "
    "left_out (number of remarks you left out because they were personal, sensitive or off the record). "
    "Never include personal or off-the-record remarks in any field. Plain British English."
)


def strip_figures(text: str) -> str:
    """Numbers out, so the Brain can borrow the words but never a price, budget or date from them."""
    return _FIGURE.sub("[figure]", text or "")


def brief_from_notes(notes: str) -> dict:
    """The brief, or a ValueError with a plain reason."""
    from app.automations import llm
    text = (notes or "").strip()
    if len(text) < MIN_NOTES:
        raise ValueError("These notes are too short to build a pitch from. Add what the client wants and what they responded to, then try again.")
    if not llm.is_configured():
        raise ValueError("The Brain isn't switched on for this account, so it can't write a pitch from notes. An administrator can switch it on.")
    out = llm.extract_json(BRIEF_SYSTEM, f"MEETING NOTES:\n{text[:12000]}", max_tokens=700, purpose="pitch_brief")
    if not isinstance(out, dict):
        raise ValueError("The Brain couldn't read these notes just now. Try again in a minute.")
    if not out.get("enough"):
        raise ValueError("The notes don't say enough about what the client wants to pitch from. Add a line on what they're after, then try again.")

    def lst(k: str) -> list[str]:
        v = out.get(k)
        return [str(x).strip()[:200] for x in v if str(x).strip()][:6] if isinstance(v, list) else []

    left = out.get("left_out")
    return {"situation": str(out.get("situation") or "").strip()[:600], "angle": str(out.get("angle") or "").strip()[:300],
            "resonant_points": lst("resonant_points"), "client_quotes": lst("client_quotes")[:3], "budget_signals": lst("budget_signals"),
            "magazine": str(out.get("magazine") or "").strip()[:80], "wants": str(out.get("wants") or "").strip()[:200],
            "left_out": int(left) if isinstance(left, (int, float)) and left > 0 else 0}


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def _proposal_text(p: Proposal) -> str:
    return " ".join(f"{s.get('heading', '')} {s.get('body', '')}" for s in p.sections or [] if not s.get("block"))


def similar_pitches(db: Session, brief: dict, title_id: uuid.UUID | None, company: Company, limit: int = PAST_LIMIT) -> list[Proposal]:
    """The sent proposals most like this brief: the same magazine and the same kind of business count, then words in common."""
    want = _words(" ".join([brief.get("situation", ""), brief.get("angle", ""), brief.get("wants", ""), *brief.get("resonant_points", [])]))
    if not want:
        return []
    sector = (company.industry or "").strip().lower()
    scored = []
    for p in db.scalars(select(Proposal).where(Proposal.status == "sent").order_by(Proposal.sent_at.desc().nullslast()).limit(300)):
        common = len(want & _words(_proposal_text(p)))
        if not common:
            continue
        score = common + (3 if title_id and p.title_id == title_id else 0)
        if sector and p.company_id != company.id:
            other = db.get(Company, p.company_id)
            score += 2 if other and (other.industry or "").strip().lower() == sector else 0
        scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for s, p in scored[:limit] if s >= 3]


def _title(db: Session, brief: dict, title_id: uuid.UUID | None, company: Company, user: User) -> SalesTitle | None:
    from app.automations.proposal_requests import _title_for
    if title_id:
        return db.get(SalesTitle, title_id)
    if brief.get("magazine"):
        t = _title_for(db, brief["magazine"], None)
        if t:
            return t
    # the magazine they last booked
    last = db.scalars(select(SalesEdition.title_id).join(SalesOrder, SalesOrder.edition_id == SalesEdition.id)
                      .where(SalesOrder.company_id == company.id).order_by(SalesEdition.edition_date.desc().nullslast())).first()
    return (db.get(SalesTitle, last) if last else None) or _title_for(db, None, user)


def instruction(brief: dict, past: list[Proposal]) -> str:
    parts = [
        "Rewrite this proposal as a pitch that answers what the client said in our meeting. Open with their situation, "
        "take the angle below, and make each section speak to what they responded well to. Keep it warm, specific and short. "
        "Don't mention their budget or any figure from the meeting; prices are in the price table. Don't add sections about "
        "things they didn't raise.",
        f"Their situation: {strip_figures(brief['situation'])}",
        f"Angle to take: {strip_figures(brief['angle'])}",
    ]
    if brief["resonant_points"]:
        parts.append("They responded well to: " + "; ".join(strip_figures(x) for x in brief["resonant_points"]))
    if brief["client_quotes"]:
        parts.append("What they said (you may echo the idea, not quote it): " + "; ".join(strip_figures(x) for x in brief["client_quotes"]))
    if brief["budget_signals"]:
        parts.append("Timing and budget context (shape the urgency only, never state it): " + "; ".join(strip_figures(x) for x in brief["budget_signals"]))
    for i, p in enumerate(past, 1):
        parts.append(f"PAST PITCH {i} THAT WE SENT (borrow its angle and structure only - never its figures, dates or client details):\n"
                     + strip_figures(_proposal_text(p))[:1800])
    return "\n\n".join(parts)


def company_for_call(db: Session, call: CallRecording) -> tuple[Company | None, Contact | None]:
    """Who a call's pitch is for: the call's company, or the company of the contact it's linked to."""
    contact = db.get(Contact, call.contact_id) if call.contact_id else None
    company = db.get(Company, call.company_id) if call.company_id else None
    if not company and contact and contact.company_id:
        company = db.get(Company, contact.company_id)
    return company, contact


def make_pitch(db: Session, user: User, company: Company, notes: str, *, contact: Contact | None = None,
               title_id: uuid.UUID | None = None, call: CallRecording | None = None) -> Proposal:
    """A draft proposal answering the notes. ValueError (a plain sentence) when it can't be made."""
    from app.api.routes.proposals import LineIn, ProposalCreate, _apply_style, create_proposal
    from app.automations.proposal_requests import pick_rates
    from app.proposals import drafting

    brief = brief_from_notes(notes)
    title = _title(db, brief, title_id, company, user)
    rates = [r for r in pick_rates(db, title, brief.get("wants")) if r.price_gbp is not None]
    firsts = list({r.section: r for r in reversed(rates)}.values())[::-1][:3]
    lines = [LineIn(product=r.product, rate_id=r.id, source="rate_card", title_id=r.title_id) for r in firsts]
    when = (call.ended_at or call.created_at) if call else None
    try:
        out = create_proposal(ProposalCreate(company_id=company.id, contact_id=contact.id if contact else None,
                                             title_id=title.id if title else None, lines=lines, use_ai=True), db=db, user=user)
    except Exception as exc:   # an HTTPException from the builder carries a plain reason
        raise ValueError(getattr(exc, "detail", None) or "The pitch couldn't be started. Try again from Proposals.") from exc
    prop = db.get(Proposal, out.id)
    if not any(s.get("block") for s in prop.sections or []):
        _apply_style(db, prop, user, standard=True)
    past = similar_pitches(db, brief, prop.title_id, company)
    flags = ["Made from your meeting notes - check it says what you agreed and fits the client before sending."]
    text = [s for s in prop.sections or [] if not s.get("block")]
    try:
        new, _ = drafting.revise_sections(prop.context or {}, prop.lines, prop.campaign_name, text, instruction(brief, past))
        merged, it = [], iter(new)
        for s in prop.sections or []:
            merged.append(s if s.get("block") else next(it, None))
        prop.sections, prop.drafted_by = [x for x in merged if x] + list(it), "ai"
    except drafting.RevisionRefused as exc:
        flags.append(f"Couldn't tailor the wording to the meeting ({exc}) - this is the standard draft.")
    if not past:
        flags.append("No similar past pitch was found, so this is written from the notes alone.")
    if brief["left_out"]:
        flags.append(f"Left out {brief['left_out']} remark{'s' if brief['left_out'] != 1 else ''} from the notes that sounded personal or off the record.")
    prop.flags = [*flags, *(prop.flags or [])]
    prop.context = {**(prop.context or {}), "pitch": {
        "brief": brief, "call_id": str(call.id) if call else None, "source_proposal_ids": [str(p.id) for p in past],
        "made_at": datetime.now(timezone.utc).isoformat()}}
    prop.notes = ((f"Pitch from the call on {when:%-d %b %Y}" if when else "Pitch from meeting notes")
                  + (f" ({call.title})" if call and call.title else "") + ".")
    if call:
        call.notes = {**(call.notes or {}), "pitch_proposal_id": str(prop.id)}
    db.flush()
    return prop
