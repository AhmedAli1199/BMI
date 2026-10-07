"""The editorial plan: every brand's issues, specials and events for the year,
their deadlines and key dates, the features planned for each issue, and the
brand's usual deadline rules and regular sections.

Issues ARE the order register's editions - the plan adds dates and features to
them, so an issue's bookings and its plan live in one place. Editing rights match
the rate card: admins/data managers everything, publishers their own brand.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import EditionFeature, EditorialSetting, SalesEdition, SalesOrder, SalesTitle
from app.sales import brands as B
from app.sales import editorial_seed as seed
from app.sales.analytics import BOOKED
from app.sales.editorial import STANDARD, STANDARD_LABELS, compute_deadlines, describe_rule, shift_year
from app.services.field_audit import record_field_changes

router = APIRouter(prefix="/editorial", tags=["editorial plan"])

PLAN_KINDS = ("issue", "event", "awards", "guide")  # monthly web/newsletter periods are sales buckets, not editorial issues
FORMATS = ("print_digital", "print", "digital", "event", "awards")
FEATURE_STATUSES = ("planned", "confirmed", "dropped")


# ---- shapes -------------------------------------------------------------------------

class Milestone(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    date: date


class IssueOut(BaseModel):
    id: uuid.UUID
    brand: str
    brand_name: str
    title_id: uuid.UUID
    title_name: str
    year: int
    name: str
    kind: str
    format: str | None
    period_label: str | None
    edition_date: date | None
    editorial_deadline: date | None
    ad_deadline: date | None
    copy_deadline: date | None
    milestones: list[Milestone]
    theme: str | None
    distribution: str | None
    features: int
    needs_check: bool
    booked_gbp: float
    orders: int
    status: str


class FeatureOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    sponsorable: bool
    sort_order: int


class SettingsOut(BaseModel):
    brand: str
    deadline_rules: list[dict]
    regular_sections: list[dict]
    about: str | None
    rules_described: list[str]


class IssueDetail(IssueOut):
    feature_list: list[FeatureOut]
    notes: str | None
    can_edit: bool
    settings: SettingsOut
    last_year: dict | None
    prev_issue: dict | None
    next_issue: dict | None
    can_delete: bool


class PlannerRow(BaseModel):
    title_id: uuid.UUID
    title_name: str
    issues: list[IssueOut]


class PlannerBrand(BaseModel):
    key: str
    name: str
    short: str
    can_edit: bool
    seed_available: int
    rows: list[PlannerRow]
    undated: list[IssueOut]
    about: str | None


class Planner(BaseModel):
    year: int
    years: list[int]
    today: date
    brands: list[PlannerBrand]


class DeadlineOut(BaseModel):
    date: date
    days: int
    what: str
    type: str  # editorial | advertising | copy | publication | event | milestone
    issue: IssueOut


# ---- helpers ------------------------------------------------------------------------

def _brand_or_404(key: str) -> B.Brand:
    b = B.get_brand(key)
    if not b:
        raise HTTPException(404, "Brand not found")
    return b


def _settings(db: Session, brand: str) -> SettingsOut:
    st = db.get(EditorialSetting, brand)
    rules = (st.deadline_rules if st else []) or []
    return SettingsOut(brand=brand, deadline_rules=rules, regular_sections=(st.regular_sections if st else []) or [],
                       about=st.about if st else None, rules_described=[f"{r.get('label')}: {describe_rule(r)}" for r in rules])


def _titles_by_id(db: Session) -> dict[uuid.UUID, SalesTitle]:
    return {t.id: t for t in db.scalars(select(SalesTitle))}


def _bookings(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[float, int]]:
    if not ids:
        return {}
    rows = db.execute(select(SalesOrder.edition_id, func.coalesce(func.sum(SalesOrder.value_gbp), 0), func.count())
                      .where(SalesOrder.edition_id.in_(ids), SalesOrder.status == BOOKED).group_by(SalesOrder.edition_id))
    return {e: (float(v), n) for e, v, n in rows}


def _feature_counts(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    return dict(db.execute(select(EditionFeature.edition_id, func.count()).where(EditionFeature.edition_id.in_(ids), EditionFeature.status != "dropped")
                           .group_by(EditionFeature.edition_id)).all())


def _out(e: SalesEdition, t: SalesTitle, books: dict, feats: dict) -> IssueOut:
    brand = B.brand_for_title_slug(t.slug)
    v, n = books.get(e.id, (0.0, 0))
    return IssueOut(id=e.id, brand=brand.key if brand else "", brand_name=brand.name if brand else "", title_id=t.id, title_name=t.name,
                    year=e.year, name=e.name, kind=e.kind, format=e.format, period_label=e.period_label, edition_date=e.edition_date,
                    editorial_deadline=e.editorial_deadline, ad_deadline=e.ad_deadline, copy_deadline=e.copy_deadline,
                    milestones=[Milestone(**m) for m in (e.milestones or []) if m.get("label") and m.get("date")], theme=e.theme,
                    distribution=e.distribution, features=feats.get(e.id, 0), needs_check=e.plan_needs_check, booked_gbp=v, orders=n, status=e.status)


def _brand_editions(db: Session, brand: B.Brand, *, year: int | None = None, start: date | None = None, end: date | None = None) -> list[SalesEdition]:
    ids = [t.id for t in B.brand_titles(db, brand)]
    if not ids:
        return []
    q = select(SalesEdition).where(SalesEdition.title_id.in_(ids), SalesEdition.kind.in_(PLAN_KINDS))
    if year:
        q = q.where(SalesEdition.year == year)
    return list(db.scalars(q.order_by(SalesEdition.edition_date.nullslast(), SalesEdition.name)))


def _edition_brand(db: Session, e: SalesEdition) -> tuple[B.Brand, SalesTitle]:
    t = db.get(SalesTitle, e.title_id)
    b = B.brand_for_title_slug(t.slug) if t else None
    if not b:
        raise HTTPException(404, "Issue not found")
    return b, t


def _require_edit(db: Session, identity: Identity, brand: B.Brand) -> None:
    if not B.can_edit_brand(db, identity, brand):
        raise HTTPException(403, f"Only admins, data managers and {brand.name}'s publishers can change this plan.")


def _years(db: Session) -> list[int]:
    this = date.today().year
    have = set(db.scalars(select(SalesEdition.year).distinct()))
    return sorted({y for y in have if y >= this - 2} | {this, this + 1}, reverse=True)


# ---- reading ----------------------------------------------------------------------------

@router.get("/planner", response_model=Planner)
def planner(year: int | None = None, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> Planner:
    y = year or date.today().year
    titles = _titles_by_id(db)
    out = []
    for b in B.BRANDS:
        eds = _brand_editions(db, b, year=y)
        books, feats = _bookings(db, [e.id for e in eds]), _feature_counts(db, [e.id for e in eds])
        rows: dict[uuid.UUID, PlannerRow] = {}
        undated = []
        for t in B.brand_titles(db, b):
            rows[t.id] = PlannerRow(title_id=t.id, title_name=t.name, issues=[])
        for e in eds:
            o = _out(e, titles[e.title_id], books, feats)
            (rows[e.title_id].issues if e.edition_date else undated).append(o)
        st = db.get(EditorialSetting, b.key)
        out.append(PlannerBrand(key=b.key, name=b.name, short=b.short, can_edit=B.can_edit_brand(db, identity, b),
                                seed_available=seed.seed_available(db, b.key, y), rows=[r for r in rows.values() if r.issues],
                                undated=undated, about=st.about if st else None))
    return Planner(year=y, years=_years(db), today=date.today(), brands=out)


def _deadline_entries(e: IssueOut) -> list[tuple[date, str, str]]:
    out = []
    if e.editorial_deadline:
        out.append((e.editorial_deadline, "Editorial deadline", "editorial"))
    if e.ad_deadline:
        out.append((e.ad_deadline, "Advertising deadline", "advertising"))
    if e.copy_deadline:
        out.append((e.copy_deadline, "Copy & artwork deadline", "copy"))
    for m in e.milestones:
        out.append((m.date, m.label, "milestone"))
    if e.edition_date:
        out.append((e.edition_date, "Publication" if e.kind in ("issue", "guide") else ("Ceremony" if e.kind == "awards" else "Event day"),
                    "publication" if e.kind in ("issue", "guide") else "event"))
    return out


@router.get("/deadlines", response_model=list[DeadlineOut])
def deadlines(days: int = Query(90, ge=1, le=400), past: int = Query(0, ge=0, le=60), brand: str | None = None,
              db: Session = Depends(get_db)) -> list[DeadlineOut]:
    """Every deadline and key date coming up, soonest first."""
    today = date.today()
    start, end = today - timedelta(days=past), today + timedelta(days=days)
    titles = _titles_by_id(db)
    out: list[DeadlineOut] = []
    for b in [_brand_or_404(brand)] if brand else B.BRANDS:
        eds = [e for e in _brand_editions(db, b) if e.year >= start.year - 1 and e.year <= end.year + 1]
        books, feats = _bookings(db, [e.id for e in eds]), _feature_counts(db, [e.id for e in eds])
        for e in eds:
            o = _out(e, titles[e.title_id], books, feats)
            for d, what, typ in _deadline_entries(o):
                if start <= d <= end:
                    out.append(DeadlineOut(date=d, days=(d - today).days, what=what, type=typ, issue=o))
    return sorted(out, key=lambda x: (x.date, x.issue.brand, x.issue.name))


def _neighbour(db: Session, e: SalesEdition, direction: int) -> dict | None:
    q = select(SalesEdition).where(SalesEdition.title_id == e.title_id, SalesEdition.kind.in_(PLAN_KINDS), SalesEdition.edition_date.isnot(None), SalesEdition.id != e.id)
    if not e.edition_date:
        return None
    q = q.where(SalesEdition.edition_date > e.edition_date).order_by(SalesEdition.edition_date) if direction > 0 else \
        q.where(SalesEdition.edition_date < e.edition_date).order_by(SalesEdition.edition_date.desc())
    n = db.scalars(q.limit(1)).first()
    return {"id": str(n.id), "name": n.name, "year": n.year} if n else None


@router.get("/issues/{eid}", response_model=IssueDetail)
def issue(eid: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> IssueDetail:
    e = db.get(SalesEdition, eid)
    if not e:
        raise HTTPException(404, "Issue not found")
    brand, t = _edition_brand(db, e)
    books = _bookings(db, [e.id])
    feats = list(db.scalars(select(EditionFeature).where(EditionFeature.edition_id == e.id).order_by(EditionFeature.sort_order, EditionFeature.created_at)))
    base = _out(e, t, books, {e.id: sum(1 for f in feats if f.status != "dropped")})
    last = None
    if e.edition_date:
        ly = db.scalars(select(SalesEdition).where(SalesEdition.title_id == e.title_id, SalesEdition.year == e.year - 1, SalesEdition.edition_date.isnot(None))
                        .order_by(func.abs(SalesEdition.edition_date - (e.edition_date - timedelta(days=365))))).first()
        if ly:
            lb = _bookings(db, [ly.id]).get(ly.id, (0.0, 0))
            last = {"id": str(ly.id), "name": ly.name, "year": ly.year, "booked_gbp": lb[0], "orders": lb[1]}
    has_orders = db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.edition_id == e.id)) or 0
    return IssueDetail(**base.model_dump(), feature_list=[FeatureOut(id=f.id, title=f.title, description=f.description, status=f.status,
                                                                        sponsorable=f.sponsorable, sort_order=f.sort_order) for f in feats],
                       notes=e.notes, can_edit=B.can_edit_brand(db, identity, brand), settings=_settings(db, brand.key), last_year=last,
                       prev_issue=_neighbour(db, e, -1), next_issue=_neighbour(db, e, 1), can_delete=has_orders == 0 and e.source_file is None)


@router.get("/brands/{key}/settings", response_model=SettingsOut)
def get_settings(key: str, db: Session = Depends(get_db)) -> SettingsOut:
    _brand_or_404(key)
    return _settings(db, key)


# ---- writing: issues --------------------------------------------------------------------

class IssueIn(BaseModel):
    brand: str
    title_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    name: str = Field(min_length=1, max_length=120)
    kind: str = "issue"
    format: str | None = None
    period_label: str | None = Field(default=None, max_length=200)
    edition_date: date | None = None
    editorial_deadline: date | None = None
    ad_deadline: date | None = None
    copy_deadline: date | None = None
    milestones: list[Milestone] = []
    theme: str | None = Field(default=None, max_length=300)
    distribution: str | None = Field(default=None, max_length=300)
    use_rules: bool = True  # fill empty deadlines from the brand's rules


class IssuePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = None
    format: str | None = None
    period_label: str | None = Field(default=None, max_length=200)
    edition_date: date | None = None
    editorial_deadline: date | None = None
    ad_deadline: date | None = None
    copy_deadline: date | None = None
    milestones: list[Milestone] | None = None
    theme: str | None = Field(default=None, max_length=300)
    distribution: str | None = Field(default=None, max_length=300)
    notes: str | None = None
    needs_check: bool | None = None


AUDIT_FIELDS = ("name", "edition_date", "editorial_deadline", "ad_deadline", "copy_deadline", "theme", "distribution", "period_label", "format")


@router.post("/issues", response_model=IssueDetail, status_code=201)
def add_issue(p: IssueIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> IssueDetail:
    brand = _brand_or_404(p.brand)
    _require_edit(db, identity, brand)
    t = db.get(SalesTitle, p.title_id)
    if not t or t.slug not in brand.title_slugs:
        raise HTTPException(422, "Choose which part of the brand it belongs to.")
    if p.kind not in PLAN_KINDS:
        raise HTTPException(422, "Choose what it is: an issue, a special, an event or awards.")
    if p.format and p.format not in FORMATS:
        raise HTTPException(422, "Choose a format.")
    name = p.name.strip()
    if db.scalar(select(SalesEdition.id).where(SalesEdition.title_id == t.id, SalesEdition.year == p.year, func.lower(SalesEdition.name) == name.lower())):
        raise HTTPException(409, f"There's already “{name}” in {t.name} {p.year}.")
    st = _settings(db, brand.key)
    auto = compute_deadlines(st.deadline_rules, p.edition_date) if p.use_rules and p.kind in ("issue", "guide") else {}
    milestones = [m.model_dump(mode="json") for m in p.milestones] + [
        {"label": r["label"], "date": auto[r["key"]].isoformat()} for r in st.deadline_rules if r["key"] not in STANDARD and auto.get(r["key"])]
    e = SalesEdition(id=uuid.uuid4(), title_id=t.id, year=p.year, name=name, kind=p.kind, status="open", format=p.format,
                     period_label=(p.period_label or "").strip() or None, edition_date=p.edition_date, date_set_in_plan=bool(p.edition_date),
                     editorial_deadline=p.editorial_deadline or auto.get("editorial"), ad_deadline=p.ad_deadline or auto.get("advertising"),
                     copy_deadline=p.copy_deadline or auto.get("copy"), milestones=milestones, theme=(p.theme or "").strip() or None,
                     distribution=(p.distribution or "").strip() or None)
    db.add(e)
    db.flush()
    record_field_changes(db, entity_type="sales_edition", entity_id=e.id, before={"created": None}, updates={"created": name}, changed_by_user_id=identity.user_uuid)
    db.commit()
    return issue(e.id, db, identity)


@router.patch("/issues/{eid}", response_model=IssueDetail)
def edit_issue(eid: uuid.UUID, p: IssuePatch, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> IssueDetail:
    e = db.get(SalesEdition, eid)
    if not e:
        raise HTTPException(404, "Issue not found")
    brand, t = _edition_brand(db, e)
    _require_edit(db, identity, brand)
    data = p.model_dump(exclude_unset=True)
    if "kind" in data and data["kind"] not in PLAN_KINDS:
        raise HTTPException(422, "Choose what it is: an issue, a special, an event or awards.")
    if data.get("format") and data["format"] not in FORMATS:
        raise HTTPException(422, "Choose a format.")
    if "name" in data:
        data["name"] = data["name"].strip()
        if db.scalar(select(SalesEdition.id).where(SalesEdition.title_id == e.title_id, SalesEdition.year == e.year, SalesEdition.id != e.id,
                                                   func.lower(SalesEdition.name) == data["name"].lower())):
            raise HTTPException(409, f"There's already “{data['name']}” in {t.name} {e.year}.")
    before = {k: getattr(e, k) for k in AUDIT_FIELDS}
    for k, v in data.items():
        if k == "milestones":
            e.milestones = [m if isinstance(m, dict) else m.model_dump(mode="json") for m in v or []]
            e.milestones = [{"label": m["label"], "date": str(m["date"])} for m in e.milestones]
        elif k == "needs_check":
            e.plan_needs_check = bool(v)
        elif k in ("theme", "distribution", "period_label") and isinstance(v, str):
            setattr(e, k, v.strip() or None)
        else:
            setattr(e, k, v)
    if "edition_date" in data:
        e.date_set_in_plan = True
    if any(k in data for k in ("edition_date", "editorial_deadline", "ad_deadline", "copy_deadline")) and "needs_check" not in data:
        e.plan_needs_check = False  # a person just set the dates
    record_field_changes(db, entity_type="sales_edition", entity_id=e.id, before=before, updates={k: getattr(e, k) for k in AUDIT_FIELDS},
                         changed_by_user_id=identity.user_uuid)
    db.commit()
    return issue(e.id, db, identity)


@router.post("/issues/{eid}/apply-rules", response_model=IssueDetail)
def apply_rules(eid: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> IssueDetail:
    """Works the deadlines out again from the publication date and the brand's rules."""
    e = db.get(SalesEdition, eid)
    if not e:
        raise HTTPException(404, "Issue not found")
    brand, _ = _edition_brand(db, e)
    _require_edit(db, identity, brand)
    if not e.edition_date:
        raise HTTPException(422, "Set the publication date first.")
    st = _settings(db, brand.key)
    if not st.deadline_rules:
        raise HTTPException(422, "This brand has no deadline rules yet - add them in the brand's settings.")
    auto = compute_deadlines(st.deadline_rules, e.edition_date)
    for key, col in STANDARD.items():
        if key in auto:
            setattr(e, col, auto[key])
    custom_labels = {r["label"] for r in st.deadline_rules if r["key"] not in STANDARD}
    kept = [m for m in (e.milestones or []) if m.get("label") not in custom_labels]
    e.milestones = kept + [{"label": r["label"], "date": auto[r["key"]].isoformat()} for r in st.deadline_rules if r["key"] not in STANDARD and r["key"] in auto]
    e.plan_needs_check = False
    db.commit()
    return issue(e.id, db, identity)


@router.delete("/issues/{eid}", status_code=204, response_model=None)
def delete_issue(eid: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> None:
    e = db.get(SalesEdition, eid)
    if not e:
        return
    brand, _ = _edition_brand(db, e)
    _require_edit(db, identity, brand)
    if e.source_file is not None or db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.edition_id == e.id)):
        raise HTTPException(409, "This issue has bookings in the order register, so it can't be deleted.")
    db.delete(e)
    db.commit()


# ---- writing: features ------------------------------------------------------------------

class FeatureIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    status: str = "planned"
    sponsorable: bool = False


class FeaturePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: str | None = None
    sponsorable: bool | None = None


def _feature_edition(db: Session, identity: Identity, eid: uuid.UUID) -> SalesEdition:
    e = db.get(SalesEdition, eid)
    if not e:
        raise HTTPException(404, "Issue not found")
    _require_edit(db, identity, _edition_brand(db, e)[0])
    return e


def _fout(f: EditionFeature) -> FeatureOut:
    return FeatureOut(id=f.id, title=f.title, description=f.description, status=f.status, sponsorable=f.sponsorable, sort_order=f.sort_order)


@router.post("/issues/{eid}/features", response_model=FeatureOut, status_code=201)
def add_feature(eid: uuid.UUID, p: FeatureIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> FeatureOut:
    e = _feature_edition(db, identity, eid)
    if p.status not in FEATURE_STATUSES:
        raise HTTPException(422, "Choose planned, confirmed or dropped.")
    last = db.scalar(select(func.max(EditionFeature.sort_order)).where(EditionFeature.edition_id == e.id)) or 0
    f = EditionFeature(id=uuid.uuid4(), edition_id=e.id, title=p.title.strip(), description=(p.description or "").strip() or None,
                       status=p.status, sponsorable=p.sponsorable, sort_order=last + 10)
    db.add(f)
    db.commit()
    return _fout(f)


@router.patch("/features/{fid}", response_model=FeatureOut)
def edit_feature(fid: uuid.UUID, p: FeaturePatch, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> FeatureOut:
    f = db.get(EditionFeature, fid)
    if not f:
        raise HTTPException(404, "Feature not found")
    _feature_edition(db, identity, f.edition_id)
    data = p.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in FEATURE_STATUSES:
        raise HTTPException(422, "Choose planned, confirmed or dropped.")
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip() or (None if k == "description" else v)
        setattr(f, k, v)
    db.commit()
    return _fout(f)


@router.delete("/features/{fid}", status_code=204, response_model=None)
def delete_feature(fid: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> None:
    f = db.get(EditionFeature, fid)
    if not f:
        return
    _feature_edition(db, identity, f.edition_id)
    db.delete(f)
    db.commit()


class ReorderIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=300)


@router.post("/issues/{eid}/features/reorder")
def reorder_features(eid: uuid.UUID, p: ReorderIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    e = _feature_edition(db, identity, eid)
    feats = {f.id: f for f in db.scalars(select(EditionFeature).where(EditionFeature.edition_id == e.id))}
    for i, fid in enumerate(p.ids):
        if fid in feats:
            feats[fid].sort_order = (i + 1) * 10
    db.commit()
    return {"ok": True}


# ---- brand settings -----------------------------------------------------------------------

class RuleIn(BaseModel):
    key: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=80)
    kind: str
    value: int = Field(ge=0, le=365)


class SettingsIn(BaseModel):
    deadline_rules: list[RuleIn] = []
    regular_sections: list[dict] = []
    about: str | None = None


@router.put("/brands/{key}/settings", response_model=SettingsOut)
def save_settings(key: str, p: SettingsIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> SettingsOut:
    brand = _brand_or_404(key)
    _require_edit(db, identity, brand)
    for r in p.deadline_rules:
        if r.kind not in ("days_before", "day_prev_month"):
            raise HTTPException(422, "Each deadline is either a number of days before publication, or a day of the month before.")
        if r.kind == "day_prev_month" and not 1 <= r.value <= 31:
            raise HTTPException(422, "The day of the month must be between 1 and 31.")
    sections = [{"name": str(s.get("name", "")).strip()[:120], "description": (str(s.get("description") or "").strip()[:300] or None)}
                for s in p.regular_sections if str(s.get("name", "")).strip()]
    st = db.get(EditorialSetting, key) or EditorialSetting(brand=key)
    st.deadline_rules = [r.model_dump() for r in p.deadline_rules]
    st.regular_sections = sections
    st.about = (p.about or "").strip() or None
    db.merge(st)
    db.commit()
    return _settings(db, key)


# ---- next year & loading the published plan -------------------------------------------------

class NextYearIn(BaseModel):
    brand: str
    from_year: int
    keep_features: bool = True
    skip_ids: list[uuid.UUID] = []


class NextYearRow(BaseModel):
    id: uuid.UUID
    title_name: str
    kind: str
    old_name: str
    new_name: str
    old_date: date
    new_date: date
    features: int


def _new_name(e: SalesEdition, siblings: list[SalesEdition]) -> str:
    nums = [int(s.name) for s in siblings if s.kind == "issue" and s.name.strip().isdigit()]
    if e.name.strip().isdigit() and nums and len(nums) == len([s for s in siblings if s.kind == "issue"]):
        return str(int(e.name) + len(nums))
    return re.sub(rf"\b{e.year}\b", str(e.year + 1), re.sub(rf"\b{e.year + 1}\b", str(e.year + 2), e.name))


def _plan_next(db: Session, brand: B.Brand, from_year: int) -> list[tuple[SalesEdition, str, date]]:
    eds = [e for e in _brand_editions(db, brand, year=from_year) if e.edition_date]
    by_title: dict[uuid.UUID, list[SalesEdition]] = {}
    for e in eds:
        by_title.setdefault(e.title_id, []).append(e)
    out = []
    for e in eds:
        name = _new_name(e, by_title[e.title_id])
        if db.scalar(select(SalesEdition.id).where(SalesEdition.title_id == e.title_id, SalesEdition.year == from_year + 1, func.lower(SalesEdition.name) == name.lower())):
            continue
        out.append((e, name, shift_year(e.edition_date)))
    return out


@router.post("/next-year/preview", response_model=list[NextYearRow])
def next_year_preview(p: NextYearIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> list[NextYearRow]:
    brand = _brand_or_404(p.brand)
    _require_edit(db, identity, brand)
    titles = _titles_by_id(db)
    feats = _feature_counts(db, [e.id for e in _brand_editions(db, brand, year=p.from_year)])
    return [NextYearRow(id=e.id, title_name=titles[e.title_id].name, kind=e.kind, old_name=e.name, new_name=n, old_date=e.edition_date,
                        new_date=d, features=feats.get(e.id, 0)) for e, n, d in _plan_next(db, brand, p.from_year)]


@router.post("/next-year")
def next_year_apply(p: NextYearIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """Copies the brand's issues and events a year on - same weekday, deadlines moved with them - all marked "please check"."""
    brand = _brand_or_404(p.brand)
    _require_edit(db, identity, brand)
    n = 0
    skip = set(p.skip_ids)
    for e, name, new_date in _plan_next(db, brand, p.from_year):
        if e.id in skip:
            continue
        delta = new_date - e.edition_date
        mv = lambda d: d + delta if d else None  # noqa: E731
        ne = SalesEdition(id=uuid.uuid4(), title_id=e.title_id, year=p.from_year + 1, name=name, kind=e.kind, status="open", format=e.format,
                          period_label=e.period_label, edition_date=new_date, date_set_in_plan=True, editorial_deadline=mv(e.editorial_deadline),
                          ad_deadline=mv(e.ad_deadline), copy_deadline=mv(e.copy_deadline),
                          milestones=[{"label": m["label"], "date": mv(date.fromisoformat(m["date"])).isoformat()} for m in (e.milestones or []) if m.get("date")],
                          distribution=e.distribution, plan_needs_check=True)
        db.add(ne)
        db.flush()
        if p.keep_features:
            for f in db.scalars(select(EditionFeature).where(EditionFeature.edition_id == e.id, EditionFeature.status != "dropped")):
                db.add(EditionFeature(id=uuid.uuid4(), edition_id=ne.id, title=f.title, description=f.description, status="planned",
                                      sponsorable=f.sponsorable, sort_order=f.sort_order))
        n += 1
    db.commit()
    return {"created": n, "year": p.from_year + 1}


@router.post("/brands/{key}/load-plan")
def load_plan(key: str, year: int = Query(seed.SEED_YEAR), db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """Loads the brand's published plan (features list, media kit dates) into its issues."""
    brand = _brand_or_404(key)
    _require_edit(db, identity, brand)
    r = seed.load_seed(db, key, year)
    db.commit()
    return r
