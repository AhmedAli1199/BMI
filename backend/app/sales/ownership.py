"""Who looks after each client, on each magazine (Matt, 20 Oct 2026). The rules, in order:

1. By product: The Business Travel Magazine and its events (incl. The Business Travel People Awards) -> Kirsty;
   Selling Travel events (Connect and the rest, worldwide) -> Steve; the Accessibility Awards -> David.
2. Existing clients stay with whoever looks after them now: whoever from that magazine's team last made a note or
   logged a call/email/meeting in ACT (or BMI Brain), or last booked them, within the last `ownership_recent_years`
   (2 for now - Matt hasn't said). Contact with the client's people counts as contact with the client.
3. Onboard Hospitality: anyone else is new business, for Craig.
4. Selling Travel: by the destination the client promotes (app/sales/regions.py). A client covering several
   regions (tour operators) goes to whoever had the last contact with them in ACT, however long ago; if nobody
   has, to whoever takes it first (their first note or booking makes it theirs on the next run).
5. Not sure (no destination found, but the client is active or someone used to look after it) -> the Review Queue
   asks once, with a suggestion. The answer is kept and never worked out again, like any change made on the
   company page.

`refresh()` works it all out for some or every company and saves the result in client_owners - nightly
(job client_owner_refresh), and for one company whenever its page asks.
"""
from __future__ import annotations

import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import and_, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.models import ClientOwner, Company, Contact, HistoryEntry, Note, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.sales.regions import REGION_REP, spot, spot_website

logger = logging.getLogger("app.sales.ownership")


@dataclass(frozen=True)
class Area:
    key: str
    magazine: str                       # as shown on the company page
    title_slugs: tuple[str, ...]        # bookings under these titles count
    source_dbs: tuple[str, ...]         # companies in these Act! databases get this area
    fixed: str | None = None            # rule 1: always this SalesRep code
    team: tuple[str, ...] = ()          # whose notes and bookings count (rule 2)
    new_business: str | None = None     # rule 3
    by_region: bool = False             # rule 4
    why_fixed: str = ""


SELLING_TRAVEL_DBS = ("sellingtravel", "prospects")
AREAS: tuple[Area, ...] = (
    Area("obh", "Onboard Hospitality", ("obh", "obh-web", "obh-awards", "obh-forum-asia"), ("onboard",),
         team=("SW", "CM"), new_business="CM"),
    Area("tbtm", "The Business Travel Magazine", ("tbtm", "tbtm-events"), SELLING_TRAVEL_DBS, fixed="KH",
         why_fixed="The Business Travel Magazine and its events, including the Business Travel People Awards, are all Kirsty's."),
    Area("stm", "Selling Travel", ("selling-travel", "selling-travel-online", "selling-travel-supplements", "selling-travel-guides",
                                   "selling-canada", "selling-australia", "visit-usa-planner", "visit-usa-online"),
         SELLING_TRAVEL_DBS, team=("SP", "ST", "DW"), by_region=True),
    Area("stm-events", "Selling Travel events", ("selling-travel-events", "stm-connect-events"), SELLING_TRAVEL_DBS, fixed="ST",
         why_fixed="Selling Travel's events, including Connect, are all Steve's, worldwide."),
    Area("accessibility", "Accessibility Awards", ("travel-for-every-body-awards",), SELLING_TRAVEL_DBS, fixed="DW",
         why_fixed="The Accessibility Awards are David's."),
)
BY_KEY = {a.key: a for a in AREAS}
RULE_WORDS = {
    "product": "By product", "last_contact": "Last contact", "last_booking": "Last booking", "region": "By region",
    "new_business": "New business", "first_to_take": "Nobody yet", "chosen": "Chosen by a person", "not_sure": "Not sure yet",
}
# Act! spells some names differently from the order register.
NAME_ALIASES = {"sue wiliams": "sue williams", "steve thompson": "steven thompson"}


def _key(name: str | None) -> str:
    k = re.sub(r"\s+", " ", (name or "").strip().lower())
    return NAME_ALIASES.get(k, k)


def areas_for(company: Company, booked_areas: set[str] = frozenset()) -> list[Area]:
    db_ = (company.source_db or "").lower()
    db_ = "onboard" if db_.startswith("onboard") else db_
    return [a for a in AREAS if db_ in a.source_dbs or a.key in booked_areas]


@dataclass
class Decision:
    rep: SalesRep | None
    rule: str
    reason: str
    evidence_on: date | None = None
    regions: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    contacts: list[tuple[SalesRep | None, str, date]] = field(default_factory=list)  # (rep, who in words, date)
    bookings: dict[str, list[tuple[SalesRep | None, date]]] = field(default_factory=lambda: defaultdict(list))  # area -> ...


def _d(v) -> date | None:
    return v.date() if isinstance(v, datetime) else v


def _fmt(d: date) -> str:
    return f"{d.day} {d:%b %Y}"


def gather(db: Session, company_ids: list[uuid.UUID] | None) -> dict[uuid.UUID, Evidence]:
    """Every note, history entry and booking that says who's been dealing with each company - one pass each."""
    reps = list(db.scalars(select(SalesRep)))
    by_name = {_key(r.name): r for r in reps}
    by_user = {r.user_id: r for r in reps if r.user_id}
    title_area = {s: a.key for a in AREAS for s in a.title_slugs}
    out: dict[uuid.UUID, Evidence] = defaultdict(Evidence)

    people = select(Contact.id).where(Contact.company_id.in_(company_ids)) if company_ids is not None else None

    def rows(model, when):
        q = select(model.entity_type.label("et"), model.entity_id.label("eid"), model.act_author.label("author"),
                   model.created_by_user_id.label("uid"), when.label("d")) \
            .where(model.entity_type.in_(("company", "contact")), or_(model.act_author.isnot(None), model.created_by_user_id.isnot(None)))
        if people is not None:   # one company (its page): only its own notes and its people's, by index
            q = q.where(or_(and_(model.entity_type == "company", model.entity_id.in_(company_ids)),
                            and_(model.entity_type == "contact", model.entity_id.in_(people))))
        return q

    x = union_all(rows(Note, Note.act_created_at), rows(HistoryEntry, HistoryEntry.occurred_at)).subquery()
    cid = func.coalesce(Contact.company_id, x.c.eid)
    q = (select(cid.label("company_id"), x.c.author, x.c.uid, func.max(x.c.d))
         .select_from(x).outerjoin(Contact, and_(x.c.et == literal("contact"), Contact.id == x.c.eid))
         .where(x.c.d.isnot(None)).group_by(cid, x.c.author, x.c.uid))
    if company_ids is not None:
        q = q.where(cid.in_(company_ids))
    for company_id, author, uid, when in db.execute(q):
        if company_id is None:
            continue
        rep = by_user.get(uid) if uid else by_name.get(_key(author))
        who = rep.name if rep else (author or "someone")
        out[company_id].contacts.append((rep, who, _d(when)))

    bq = (select(SalesOrder.company_id, SalesOrder.rep_id, SalesTitle.slug, func.max(func.coalesce(SalesOrder.booked_on, SalesEdition.edition_date)))
          .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id).join(SalesTitle, SalesEdition.title_id == SalesTitle.id)
          .where(SalesOrder.company_id.isnot(None), SalesOrder.status.in_(("booked", "pencilled")))
          .group_by(SalesOrder.company_id, SalesOrder.rep_id, SalesTitle.slug))
    if company_ids is not None:
        bq = bq.where(SalesOrder.company_id.in_(company_ids))
    rep_by_id = {r.id: r for r in reps}
    for company_id, rep_id, slug, when in db.execute(bq):
        area = title_area.get(slug)
        if area and when:
            out[company_id].bookings[area].append((rep_by_id.get(rep_id), _d(when)))
    return out


def _latest(items):
    return max(items, key=lambda t: t[-1]) if items else None


def decide(area: Area, company: Company, ev: Evidence, reps: dict[str, SalesRep], today: date, years: int) -> Decision:
    if area.fixed:
        return Decision(reps.get(area.fixed), "product", area.why_fixed)
    cutoff = date(today.year - years, today.month, min(today.day, 28))
    team = [(r, w, d) for r, w, d in ev.contacts if r and r.code in area.team and r.active]
    booked = [(r, d) for r, d in ev.bookings.get(area.key, []) if r and r.code in area.team and r.active]
    last_note = _latest([t for t in team if t[2] >= cutoff])
    last_booking = _latest([t for t in booked if t[1] >= cutoff])
    span = f"{years} year{'s' if years != 1 else ''}"
    if last_note and (not last_booking or last_note[2] >= last_booking[1]):
        r, _w, d = last_note
        return Decision(r, "last_contact", f"{r.name} was the last in touch, on {_fmt(d)} - an existing client stays with them.", d)
    if last_booking:
        r, d = last_booking
        return Decision(r, "last_booking", f"{r.name} booked them last, on {_fmt(d)} - an existing client stays with them.", d)

    if area.new_business:
        return Decision(reps.get(area.new_business), "new_business",
                        f"Nobody from {area.magazine} has been in touch or booked them in the last {span}, so it's new business.")

    found = spot(" ".join(filter(None, (company.name, company.description, company.category, company.industry))))
    found = found or spot_website(company.website or "") or spot(" ".join(filter(None, (company.region, company.territory))))
    regions = [r for r, _t in found]
    covers = {REGION_REP[r] for r in regions if r in REGION_REP}
    if len(covers) == 1:
        region, term = found[0]
        r = reps.get(next(iter(covers)))
        place = term.title() if term.lower() != region.lower() else region
        what = f"{place} ({region})" if place != region else region
        return Decision(r, "region", f"Promotes {what}, which {r.name if r else 'nobody'} covers.", regions=regions)
    older = _latest(team) or _latest([(r, "", d) for r, d in booked])
    if len(covers) > 1:
        where = ", ".join(sorted(regions))
        if older:
            r, _w, d = older
            return Decision(r, "last_contact", f"Covers several regions ({where}); {r.name} was the last in touch, on {_fmt(d)}.", d, regions)
        return Decision(None, "first_to_take", f"Covers several regions ({where}) and nobody has been in touch yet, so it's whoever takes it first.",
                        regions=regions)
    active = any(d >= cutoff for _r, _w, d in ev.contacts) or any(d >= cutoff for lst in ev.bookings.values() for _r, d in lst)
    if older:
        r, _w, d = older
        return Decision(r, "not_sure", f"No destination found. {r.name} was the last in touch, on {_fmt(d)} - more than {span} ago.", d)
    if active:
        return Decision(None, "not_sure", "No destination found, and nobody from Selling Travel has dealt with them.")
    return Decision(None, "first_to_take", "No destination found and nobody has been in touch yet, so it's whoever takes it first.")


def refresh(db: Session, company_ids: list[uuid.UUID] | None = None, today: date | None = None) -> dict:
    """Works out (again) every rule-made row for these companies (all if None). Rows a person chose are left alone.
    Returns counts, and the (company, area) pairs that are now "not sure", for the Review Queue."""
    today = today or date.today()
    years = max(1, runtime_settings.get_int(db, "ownership_recent_years"))
    reps = {r.code: r for r in db.scalars(select(SalesRep))}
    evidence = gather(db, company_ids)
    ids = company_ids if company_ids is not None else list(db.scalars(select(Company.id)))
    existing: dict[tuple, ClientOwner] = {}
    oq = select(ClientOwner)
    if company_ids is not None:
        oq = oq.where(ClientOwner.company_id.in_(company_ids))
    for row in db.scalars(oq):
        existing[(row.company_id, row.area)] = row
    stats = {"companies": 0, "changed": 0, "not_sure": []}
    seen: set[tuple] = set()
    companies = (c for i in range(0, len(ids), 1000) for c in db.scalars(select(Company).where(Company.id.in_(ids[i:i + 1000]))).all())
    for company in companies:
        stats["companies"] += 1
        ev = evidence.get(company.id) or Evidence()
        for area in areas_for(company, set(ev.bookings)):
            k = (company.id, area.key)
            seen.add(k)
            row = existing.get(k)
            if row and row.chosen:
                continue
            dec = decide(area, company, ev, reps, today, years)
            new = (dec.rep.id if dec.rep else None, dec.rule, dec.reason[:400], dec.evidence_on, dec.regions)
            if row is None:
                row = ClientOwner(id=uuid.uuid4(), company_id=company.id, area=area.key, chosen=False)
                db.add(row)
            elif (row.rep_id, row.rule, row.reason, row.evidence_on, row.regions) == new:
                if dec.rule == "not_sure":
                    stats["not_sure"].append(k)
                continue
            row.rep_id, row.rule, row.reason, row.evidence_on, row.regions = new
            stats["changed"] += 1
            if dec.rule == "not_sure":
                stats["not_sure"].append(k)
    for k, row in existing.items():
        if k not in seen and not row.chosen:
            db.delete(row)
    db.flush()
    return stats


def choose(db: Session, company: Company, area_key: str, rep: SalesRep | None, user_id: uuid.UUID | None, who: str | None,
           back_to_rules: bool = False) -> ClientOwner | None:
    """A person decides (company page, or the answer to the Review Queue question). Kept for good."""
    area = BY_KEY.get(area_key)
    if not area:
        raise ValueError("That magazine isn't one we know.")
    row = db.scalars(select(ClientOwner).where(ClientOwner.company_id == company.id, ClientOwner.area == area_key)).first()
    if back_to_rules:
        if row:
            row.chosen, row.chosen_by_user_id = False, None
        refresh(db, [company.id])
        return db.scalars(select(ClientOwner).where(ClientOwner.company_id == company.id, ClientOwner.area == area_key)).first()
    if row is None:
        row = ClientOwner(id=uuid.uuid4(), company_id=company.id, area=area_key)
        db.add(row)
    today = date.today()
    row.rep_id = rep.id if rep else None
    row.rule, row.chosen, row.chosen_by_user_id, row.evidence_on = "chosen", True, user_id, today
    by = f" by {who}" if who else ""
    row.reason = (f"Chosen{by} on {_fmt(today)}." if rep else f"Set to nobody{by} on {_fmt(today)} - whoever takes it first.")[:400]
    db.flush()
    return row


def owners_for(db: Session, company: Company, fresh: bool = True) -> list[dict]:
    """The company page's list: one line per magazine, worked out fresh (cheap for one company). fresh=False reads
    what's saved, without writing anything (the Brain)."""
    if fresh:
        refresh(db, [company.id])
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    rows = {r.area: r for r in db.scalars(select(ClientOwner).where(ClientOwner.company_id == company.id))}
    out = []
    for area in AREAS:
        row = rows.get(area.key)
        if not row:
            continue
        rep = reps.get(row.rep_id) if row.rep_id else None
        out.append({"area": area.key, "magazine": area.magazine, "rep_id": str(rep.id) if rep else None,
                    "rep_name": rep.name if rep else None, "rep_user_id": str(rep.user_id) if rep and rep.user_id else None,
                    "rule": row.rule, "rule_label": RULE_WORDS.get(row.rule, row.rule), "reason": row.reason,
                    "chosen": row.chosen, "fixed": bool(area.fixed), "regions": row.regions or []})
    return out


def owner_rep(db: Session, company_id: uuid.UUID | None, title_slug: str | None) -> SalesRep | None:
    """Who looks after this client on the magazine this title belongs to (None if nobody, or not worked out yet)."""
    if not company_id or not title_slug:
        return None
    area = next((a for a in AREAS if title_slug in a.title_slugs), None)
    if not area:
        return None
    row = db.scalars(select(ClientOwner).where(ClientOwner.company_id == company_id, ClientOwner.area == area.key)).first()
    return db.get(SalesRep, row.rep_id) if row and row.rep_id else None
