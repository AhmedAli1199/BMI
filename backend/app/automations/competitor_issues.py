"""SALES-006 and SALES-007 - who advertises with the competition, and an approach to the ones not advertising with us.

A salesperson uploads a competitor's issue as a PDF (Automations > Sales & Follow-ups > "Read a competitor's issue"),
says which BMI magazine to compare it with, and the Brain reads it:
  1. Each page's text is read from the PDF. The Brain lists the companies paying to be there (adverts, sponsored
     features, "in association with"), not the ones only mentioned in the news. Pages that are only a picture (most
     full-page adverts) are looked at as an image, up to "Picture pages the Brain looks at" per issue.
     Without the Brain, the web addresses printed on the pages are listed instead, marked as not checked.
  2. Each advertiser is looked up: a client of the BMI magazine now (a booking in the last year), a past client,
     on our database but never booked with it, or new to us.
  3. One card for the salesperson: those groups, each company linked, and an approach drafted for the past clients
     and the never-booked ones, to send as a mail merge. "Also add the new companies" adds the ones we don't have,
     with their website, so someone can find the right person there.
Nothing is sent or added until the salesperson presses a button. The uploaded PDF isn't kept.
"""
from __future__ import annotations

import base64
import io
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.brevo_sync import _person
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.models import Company, Note, ReviewQueueItem, SalesEdition, SalesOrder, SalesTitle, User
from app.sales.matching import normalise

logger = logging.getLogger("app.automations.competitor_issues")

KIND = "competitor_issue"
MAX_PAGES = 250
PAGES_PER_CALL = 8
LIST_LIMIT = 12
GROUPS = (("current", "Advertising with us now"), ("lapsed", "Advertised with us before"),
          ("never", "On our database, never booked"), ("new", "New to us"))

_PROMPT = (
    "These are pages from a trade magazine published by a competitor of BMI Publishing. List the companies PAYING to "
    "appear: display adverts, sponsored or promoted features, advertorials, supplements 'in association with' a "
    "company, and named sponsors. Leave out companies only mentioned in news or editorial, the magazine's own "
    "publisher and its events, and people. Use the company's name as it would be written in a CRM. "
    'Return JSON: {"advertisers": [{"company": string, "page": number, "website": string or null, '
    '"kind": "advert" or "sponsored"}]}. An empty list is fine.'
)
_IMAGE_PROMPT = (
    "This is one page of a trade magazine. If it is a paid advert (or a sponsored page), say which company it is for. "
    'Return JSON: {"is_advert": true or false, "company": string or null, "website": string or null}.'
)
_TLDS = ("com|co\\.uk|org\\.uk|org|net|info|biz|travel|aero|holiday|holidays|cruises|hotels|io|uk|ie|eu|de|fr|es|it|pt|nl|be|ch|at|"
         "dk|se|no|fi|is|gr|mt|cy|hr|pl|cz|ca|us|mx|br|com\\.au|au|nz|za|ae|qa|sa|in|sg|hk|jp|th|my|mu|mv|lk")
_DOMAIN = re.compile(r"\b(?:https?://)?(?:www\.)?([a-z0-9-]{3,}(?:\.[a-z0-9-]{2,})*?\.(?:" + _TLDS + r"))\b(?![.-]?[a-z0-9])", re.I)
_SKIP_DOMAINS = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "linkedin.com", "facebook.com", "twitter.com",
                 "instagram.com", "youtube.com", "x.com"}


# ---- reading the PDF ------------------------------------------------------------------------------

def read_pages(data: bytes) -> list[dict]:
    """[{"n": page number, "text": str}] - raises ValueError with a plain reason if it isn't a readable PDF."""
    import pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return [{"n": i + 1, "text": (p.extract_text() or "").strip()} for i, p in enumerate(pdf.pages[:MAX_PAGES])]
    except Exception as exc:
        raise ValueError("That file couldn't be read as a PDF. Upload the issue as a PDF file.") from exc


def page_image(data: bytes, n: int) -> str | None:
    """Page n as a JPEG data URL, for the Brain to look at."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        img = pdf[n - 1].render(scale=1.2).to_pil().convert("RGB")
        img.thumbnail((1100, 1500))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=70)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        logger.warning("competitor issue: page %s couldn't be turned into a picture", n)
        return None


def _web(site: str | None) -> str | None:
    m = _DOMAIN.search(site or "")
    return m.group(1).lower() if m else None


def find_advertisers(data: bytes, pages: list[dict], *, use_brain: bool, picture_pages: int) -> tuple[list[dict], bool]:
    """([{"company", "page", "website", "kind"}], read by the Brain)."""
    found: list[dict] = []
    brain_ok = False
    if use_brain:
        from app.automations.llm import extract_json, extract_json_from_image
        texty = [p for p in pages if len(p["text"]) >= 40]
        for i in range(0, len(texty), PAGES_PER_CALL):
            chunk = texty[i:i + PAGES_PER_CALL]
            text = "\n\n".join(f"--- Page {p['n']} ---\n{p['text'][:1800]}" for p in chunk)
            got = extract_json(_PROMPT, text, max_tokens=900, purpose="competitor_issues.read")
            if isinstance(got, dict):
                brain_ok = True
                for a in got.get("advertisers") or []:
                    if isinstance(a, dict) and (a.get("company") or "").strip():
                        found.append({"company": a["company"].strip(), "page": a.get("page"), "website": _web(a.get("website")),
                                      "kind": a.get("kind") or "advert"})
        for p in [p for p in pages if len(p["text"]) < 40][:picture_pages]:
            url = page_image(data, p["n"])
            got = extract_json_from_image(_IMAGE_PROMPT, url, max_tokens=200, purpose="competitor_issues.page") if url else None
            if isinstance(got, dict):
                brain_ok = True
                if got.get("is_advert") and (got.get("company") or "").strip():
                    found.append({"company": got["company"].strip(), "page": p["n"], "website": _web(got.get("website")), "kind": "advert"})
    if not brain_ok:   # no Brain: the web addresses printed in the issue
        for p in pages:
            for m in _DOMAIN.finditer(p["text"]):
                d = m.group(1).lower()
                if d not in _SKIP_DOMAINS:
                    found.append({"company": d.split(".")[0].replace("-", " ").title(), "page": p["n"], "website": d, "kind": "web address"})
    out, seen = [], set()
    for a in found:
        k = normalise(a["company"])
        if len(k) >= 3 and k not in seen:
            seen.add(k)
            out.append(a)
    return out, brain_ok


# ---- comparing with BMI's own records -------------------------------------------------------------

def match(db: Session, a: dict, own_names: set[str]) -> Company | None:
    k = normalise(a["company"])
    if k in own_names:
        return None   # the competitor itself, or one of BMI's own titles
    hits = [c for c in db.scalars(select(Company).where(func.lower(Company.name).op("%")(a["company"].lower())).limit(20))
            if normalise(c.name) == k]
    if hits:
        return hits[0]
    if a.get("website"):
        c = db.scalars(select(Company).where(func.lower(Company.website).contains(a["website"]))).first()
        if c:
            return c
    best = db.execute(select(Company, func.similarity(func.lower(Company.name), a["company"].lower()).label("s"))
                      .where(func.lower(Company.name).op("%")(a["company"].lower()))
                      .order_by(func.similarity(func.lower(Company.name), a["company"].lower()).desc()).limit(1)).first()
    return best[0] if best and best[1] >= 0.75 else None


def group_of(db: Session, co: Company | None, title_id: uuid.UUID, today: date) -> str:
    if not co:
        return "new"
    last = db.scalar(select(func.max(SalesOrder.booked_on)).join(SalesEdition, SalesEdition.id == SalesOrder.edition_id).where(
        SalesOrder.company_id == co.id, SalesOrder.status != "cancelled", SalesEdition.title_id == title_id))
    if last and last >= today - timedelta(days=365):
        return "current"
    return "lapsed" if last else "never"


def draft(shared: dict, competitor: str) -> tuple[str, str]:
    brand = shared.get("brand") or "our magazine"
    reach = f", reaching {shared['readership']}" if shared.get("readership") else ""
    subject = f"Reaching more of your customers with {brand}"
    body = ("Dear {{salutation|colleague}},\n\n"
            "I noticed {{company}} advertising in the trade press recently, and wondered whether you'd considered "
            f"{brand}{reach}.\n\nI'd be happy to send over our media pack and the upcoming issues that would suit you. "
            "Would a quick call next week help?\n\nKind regards,\n{{my_name}}")
    return subject, body


def make_card(db: Session, *, uploader: User | None, competitor: str, issue: str, title: SalesTitle, advertisers: list[dict],
              brain_read: bool, pages: int) -> ReviewQueueItem:
    from app.sales.brands import brand_for_title_slug
    from app.services import mail_merge as mm

    today = date.today()
    b = brand_for_title_slug(title.slug)
    shared = mm.shared_context(db, b.key if b else None)
    own = {normalise(competitor), normalise(title.name), *(normalise(x) for x in ("BMI Publishing", b.name if b else ""))}
    rows = []
    for a in advertisers:
        co = match(db, a, own)
        if co is None and normalise(a["company"]) in own:
            continue
        rows.append((a, co, group_of(db, co, title.id, today)))
    groups = {g: [(a, co) for a, co, gg in rows if gg == g] for g, _ in GROUPS}
    approach = [(a, co, p) for g in ("lapsed", "never") for a, co in groups[g] for p in [_person(db, co)] if p]
    no_one = [co.name for g in ("lapsed", "never") for a, co in groups[g] if not _person(db, co)]
    label = f"{competitor} {issue}".strip()
    details = [{"label": "Competitor issue", "value": f"{label} ({pages} pages)"},
               {"label": "Compared with", "value": shared.get("brand") or title.name}]
    for g, glabel in GROUPS:
        items = groups[g]
        details.append({"label": glabel, "value": str(len(items)) if items else "None"})
        for a, co in items[:LIST_LIMIT]:
            where = f"page {a['page']}" if a.get("page") else ""
            if co:
                details.append({"label": f"  {co.name}", "value": " · ".join(x for x in (where, a.get("kind")) if x) or "In the issue",
                                "href": f"/companies/{co.id}"})
            else:
                details.append({"label": f"  {a['company']}", "value": " · ".join(x for x in (where, a.get("website")) if x) or "In the issue",
                                **({"href": f"https://{a['website']}"} if a.get("website") else {})})
        if len(items) > LIST_LIMIT:
            details.append({"label": "  And", "value": f"{len(items) - LIST_LIMIT} more"})
    if no_one:
        details.append({"label": "No one to email at", "value": ", ".join(sorted(no_one))[:500]})
    if not brain_read:
        details.append({"label": "Worth knowing", "value": "The Brain couldn't read this issue, so these are the web addresses printed in it, "
                                                           "not checked as adverts. Check the list before you send."})
    subject, body = draft(shared, competitor)
    new = [{"company": a["company"], "website": a.get("website"), "page": a.get("page")} for a, _ in groups["new"]]
    hidden = [x for x, cond in (("open_merge", not approach), ("add_companies", not new)) if cond]
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, status="pending",
        payload={
            "summary": f"{len(rows)} advertiser{'s' if len(rows) != 1 else ''} in {label}: {len(groups['lapsed']) + len(groups['never'])} "
                       f"to approach, {len(new)} new to us",
            "details": details, "original_text": f"Subject: {subject}\n\n{body}", "original_label": "Drafted approach",
            "owner_user_id": str(uploader.id) if uploader else None, "ai_drafted": False,
            "merge": {"contact_ids": [str(p.id) for _, _, p in approach], "subject": subject, "body": body,
                      "label": f"Advertisers in {label}"[:300]},
            "new_companies": new, "source_db": title.crm_source_db, "competitor": label,
            "field_defaults": {"add_new": "true" if new else "false"},
            "hidden_actions": hidden,
            "related_entities": [{"type": "company", "id": str(co.id), "label": co.name} for _, co, _ in approach[:LIST_LIMIT]],
            "facets": {"magazine": shared.get("brand") or title.name, "competitor": competitor or "Not given",
                       "read": "Read by the Brain" if brain_read else "Web addresses only"},
            "sort_date": today.isoformat(),
        })
    db.add(item)
    return item


def process(data: bytes, *, uploader_id: uuid.UUID | None, competitor: str, issue: str, title_id: uuid.UUID) -> None:
    """Reads the issue and makes the card (run after the upload has been answered: a big issue takes a minute)."""
    from app.db.session import SessionLocal
    from app.services.notify import create_notification

    db = SessionLocal()
    try:
        title = db.get(SalesTitle, title_id)
        uploader = db.get(User, uploader_id) if uploader_id else None
        try:
            pages = read_pages(data)
        except ValueError as exc:
            if uploader:
                create_notification(db, uploader.id, "automation", f"{competitor} {issue} couldn't be read", str(exc), email=False)
                db.commit()
            return
        advertisers, brain = find_advertisers(data, pages, use_brain=runtime_settings.get_bool(db, "competitor_use_brain"),
                                              picture_pages=runtime_settings.get_int(db, "competitor_picture_pages"))
        item = make_card(db, uploader=uploader, competitor=competitor, issue=issue, title=title, advertisers=advertisers,
                         brain_read=brain, pages=len(pages))
        if uploader:
            create_notification(db, uploader.id, "automation", f"{competitor} {issue} has been read",
                                item.payload["summary"], link=f"/automations/review?kind={KIND}", email=False)
        db.commit()
    except Exception:
        logger.exception("competitor issue: reading failed")
        db.rollback()
    finally:
        db.close()


# ---- the buttons ----------------------------------------------------------------------------------

def _add_companies(db: Session, item: ReviewQueueItem, actor: uuid.UUID | None) -> int:
    p = item.payload
    made = []
    for a in p.get("new_companies") or []:
        k = normalise(a["company"])
        if any(normalise(c.name) == k for c in db.scalars(select(Company).where(func.lower(Company.name).op("%")(a["company"].lower())).limit(20))):
            continue
        co = Company(id=uuid.uuid4(), source_db=p.get("source_db") or MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
                     name=a["company"][:256], website=a.get("website"))
        db.add(co)
        db.flush()
        db.add(Note(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type="company", entity_id=co.id,
                    note_type="Competitor advertiser", act_created_at=datetime.now(timezone.utc), created_by_user_id=actor,
                    body=f"Added because they advertised in {p.get('competitor') or 'a competitor issue'}"
                         f"{' (page ' + str(a['page']) + ')' if a.get('page') else ''}. Find the right person to approach."))
        made.append(co)
    item.payload = {**p, "details": [{"label": "Done", "value": f"Added {len(made)} new compan{'y' if len(made) == 1 else 'ies'} to the database"},
                                     *p["details"]]}
    return len(made)


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    a = input_data.get("_actor_user_id")
    actor = uuid.UUID(a) if a else None
    if action_id == "open_merge":
        if (input_data.get("add_new") or "").lower() == "true":
            _add_companies(db, item, actor)
        item.payload = {**item.payload, "open_href": f"/mail-merge?review={item.id}"}
    elif action_id == "add_companies":
        _add_companies(db, item, actor)
    elif action_id != "not_useful":
        raise ValueError("That button isn't available on this card.")


register(ReviewKind(
    kind=KIND,
    label="Competitor advertisers",
    description="The companies advertising in a competitor's issue you uploaded, compared with who advertises with us, "
                "with an approach drafted for the ones who don't.",
    actions=[
        ReviewAction(id="open_merge", label="Open as a mail merge", style="primary", outcome="approved",
                     extra_fields=[ExtraField(key="add_new", label="Also add the new companies to the database", field_type="bool", required=False)]),
        ReviewAction(id="add_companies", label="Just add the new companies", style="secondary", outcome="approved"),
        ReviewAction(id="not_useful", label="Not useful", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("magazine", "Magazine"), ("competitor", "Competitor"), ("read", "Read")),
    date_sort_label="date uploaded",
))
