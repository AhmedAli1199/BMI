"""Ready-made blocks a proposal (or an enquiry reply) can include. Each is filled from the Brain's own data at the
moment it's shown or sent, so figures are never typed by hand or made up by the AI:

  package   the products, issues and prices on the proposal, with each option's total
  prices    a price list from the rate card (the products chosen, or the brand's main ones)
  stats     the brand's audience numbers (brand facts on the editorial plan's brand settings)
  issues    the next issues of the title, with their themes and booking deadlines (editorial plan)
  events    the brand's coming events and awards
  examples  links to past pages and resources (examples library)

Each block renders to plain HTML with simple inline styles (what Outlook shows reliably). The Word file is built
from the same HTML (app/proposals/html_docx.py), so the email and the document always say the same thing.
"""
from __future__ import annotations

import html
import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import EditorialSetting, ProposalExample, SalesEdition, SalesRate, SalesTitle
from app.sales.brands import BRANDS, Brand, brand_for_title_slug

BLOCKS = {
    "package": "Package and prices",
    "prices": "Prices from the rate card",
    "stats": "Audience numbers",
    "issues": "Coming issues",
    "events": "Events and awards",
    "examples": "Examples of our work",
}
# Fixed colours: these are written into the email or document itself, not the app's screens.
_TABLE = 'style="border-collapse:collapse;width:100%;max-width:640px;font-size:10.5pt"'
_TH = 'style="text-align:left;padding:6px 8px;border-bottom:2px solid #1f2937;font-weight:bold"'
_TD = 'style="padding:6px 8px;border-bottom:1px solid #d1d5db;vertical-align:top"'
_TDR = 'style="padding:6px 8px;border-bottom:1px solid #d1d5db;text-align:right;white-space:nowrap;vertical-align:top"'
_TOTAL = 'style="padding:6px 8px;text-align:right;font-weight:bold;white-space:nowrap"'

SECTION_ORDER = ("print", "sponsored", "newsletter", "website", "events", "awards", "listings", "other")
UNIT_TEXT = {"each": "", "month": " a month", "week": " a week", "year": " a year", "event": " per event", "entry": " per entry"}


def esc(v) -> str:
    return html.escape(str(v or ""))


def money(v: float) -> str:
    v = float(v or 0)
    return f"£{v:,.0f}" if abs(v - round(v)) < 0.005 else f"£{v:,.2f}"


def brand_of(db: Session, title_id) -> Brand | None:
    t = db.get(SalesTitle, uuid.UUID(str(title_id))) if title_id else None
    return brand_for_title_slug(t.slug) if t else None


def _table(head: list[str], rows: list[list[str]], right: set[int] = frozenset(), total: tuple[str, str] | None = None) -> str:
    th = "".join(f"<th {_TH}>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td {_TDR if i in right else _TD}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    foot = (f"<tr><td colspan=\"{len(head) - 1}\" {_TOTAL}>{total[0]}</td><td {_TOTAL}>{total[1]}</td></tr>" if total else "")
    return f"<table {_TABLE}><thead><tr>{th}</tr></thead><tbody>{body}{foot}</tbody></table>"


def price_text(r: SalesRate) -> str:
    if r.price_type == "poa" or r.price_gbp is None:
        return "Price on request"
    return f"{'From ' if r.price_type == 'from' else ''}{money(float(r.price_gbp))}{UNIT_TEXT.get(r.unit, '')}"


def brand_rates(db: Session, brand: Brand, year: int | None = None) -> list[SalesRate]:
    titles = [t.id for t in db.scalars(select(SalesTitle).where(SalesTitle.slug.in_(brand.title_slugs)))]
    if not titles:
        return []
    year = year or date.today().year
    have = db.scalars(select(SalesRate.year).where(SalesRate.title_id.in_(titles), SalesRate.archived.is_(False))
                      .order_by((SalesRate.year == year).desc(), SalesRate.year.desc())).first()
    if not have:
        return []
    rows = list(db.scalars(select(SalesRate).where(SalesRate.title_id.in_(titles), SalesRate.year == have, SalesRate.archived.is_(False))
                           .order_by(SalesRate.sort_order, SalesRate.product)))
    rows.sort(key=lambda r: (SECTION_ORDER.index(r.section) if r.section in SECTION_ORDER else 99, r.sort_order))
    return rows


# ---- each block -------------------------------------------------------------------------------------

def package_html(lines: list[dict], discount_pct: float = 0.0) -> str:
    from app.proposals import pricing

    if not lines:
        return "<p><em>No products added yet.</em></p>"
    out = []
    for t in pricing.totals(lines, discount_pct):
        group = [ln for ln in lines if ln.get("option") in (t["option"], None)]
        rows = []
        for ln in group:
            q = len(ln.get("issues") or []) or int(ln.get("qty") or 1)
            when = ", ".join(ln.get("issue_labels") or [])
            each = float(ln.get("unit_price") or 0)
            d = float(ln.get("discount_pct") or 0)
            price = money(pricing.line_total(ln)) if ln.get("source") != "offer" else f"-{money(abs(pricing.line_total(ln)))}"
            detail = f"{q} × {money(each)}" if q > 1 else ""
            if d:
                detail = (detail + ", " if detail else "") + f"less {d * 100:g}%"
            rows.append([esc(ln.get("product")) + (f"<br><span style=\"color:#6b7280\">{esc(detail)}</span>" if detail else ""),
                         esc(when) or "&nbsp;", price])
        if t["discount_gbp"]:
            rows.append([f"Less {discount_pct * 100:g}% discount", "&nbsp;", f"-{money(t['discount_gbp'])}"])
        head = f"<p><strong>{esc(t['option'])}</strong></p>" if t["option"] else ""
        total = (f"{esc(t['option']) + ' total' if t['option'] else 'Total'} (before VAT)", money(t["total_gbp"]))
        if all(r[1] == "&nbsp;" for r in rows):   # no issues chosen yet: no empty "When" column
            out.append(head + _table(["What", "Price"], [[r[0], r[2]] for r in rows], right={1}, total=total))
        else:
            out.append(head + _table(["What", "When", "Price"], rows, right={2}, total=total))
    return "".join(out)


def prices_html(db: Session, brand: Brand | None, rate_ids: list[str] | None = None, sections: list[str] | None = None) -> str:
    if not brand:
        return "<p><em>Choose a title first, so the right rate card is used.</em></p>"
    rates = brand_rates(db, brand)
    if rate_ids:
        wanted = [str(x) for x in rate_ids]
        by_id = {str(r.id): r for r in rates}
        rates = [by_id[i] for i in wanted if i in by_id]
    elif sections:
        rates = [r for r in rates if r.section in sections]
    else:
        rates = [r for r in rates if r.section in ("print", "sponsored", "newsletter")][:10]
    if not rates:
        return "<p><em>No prices on the rate card for this yet.</em></p>"
    rows = [[esc(r.product) + (f"<br><span style=\"color:#6b7280\">{esc(r.specs)}</span>" if r.specs else ""), esc(price_text(r))] for r in rates]
    return _table(["Product", "Price (before VAT)"], rows, right={1})


def stats_html(db: Session, brand: Brand | None) -> str:
    from app.services.mail_merge import BRAND_FIELDS

    if not brand:
        return "<p><em>Choose a title first.</em></p>"
    st = db.get(EditorialSetting, brand.key)
    facts = (st.facts if st else None) or {}
    rows = []
    for key, (label, _example) in BRAND_FIELDS.items():
        if key in ("brand", "media_pack", "video", "latest_issue"):
            continue
        val = facts.get(key) or (brand.website if key == "website" else None)
        if val:
            rows.append(f"<li><strong>{esc(label)}:</strong> {esc(val)}</li>")
    for k, v in facts.items():          # anything else the brand keeps (LinkedIn followers, open rates...)
        if k not in BRAND_FIELDS and isinstance(v, str) and v.strip():
            rows.append(f"<li><strong>{esc(k.replace('_', ' ').capitalize())}:</strong> {esc(v)}</li>")
    if facts.get("media_pack"):
        rows.append(f"<li>Full media information: <a href=\"{esc(facts['media_pack'])}\">media pack</a></li>")
    return f"<ul>{''.join(rows)}</ul>" if rows else "<p><em>No audience numbers saved for this brand yet (Editorial plan, brand settings).</em></p>"


def issues_html(db: Session, title_id, count: int = 4) -> str:
    from app.sales.editorial import fmt_day, issue_label

    if not title_id:
        return "<p><em>Choose a title first.</em></p>"
    today = date.today()
    eds = list(db.scalars(select(SalesEdition).where(SalesEdition.title_id == uuid.UUID(str(title_id)), SalesEdition.kind.in_(("issue", "guide")),
                                                     SalesEdition.edition_date.isnot(None),
                                                     or_(SalesEdition.ad_deadline >= today, SalesEdition.ad_deadline.is_(None) & (SalesEdition.edition_date >= today)))
                          .order_by(SalesEdition.edition_date).limit(count)))
    if not eds:
        return "<p><em>No coming issues in the editorial plan yet.</em></p>"
    deadlines = any(e.ad_deadline for e in eds)
    rows = [[esc(issue_label(e)), esc(fmt_day(e.edition_date)), esc(e.theme) or "&nbsp;", *([esc(fmt_day(e.ad_deadline)) or "&nbsp;"] if deadlines else [])]
            for e in eds]
    return _table(["Issue", "Out", "Theme", *(["Book by"] if deadlines else [])], rows)


def events_html(db: Session, brand: Brand | None, count: int = 6) -> str:
    from app.sales.editorial import fmt_day

    if not brand:
        return "<p><em>Choose a title first.</em></p>"
    titles = {t.id: t for t in db.scalars(select(SalesTitle).where(SalesTitle.slug.in_(brand.title_slugs)))}
    eds = list(db.scalars(select(SalesEdition).where(SalesEdition.title_id.in_(list(titles)), SalesEdition.kind.in_(("event", "awards")),
                                                     SalesEdition.edition_date >= date.today()).order_by(SalesEdition.edition_date).limit(count)))
    if not eds:
        return "<p><em>No coming events in the editorial plan yet.</em></p>"
    return "<ul>" + "".join(f"<li><strong>{esc(e.name)}</strong>, {esc(fmt_day(e.edition_date))}"
                            + (f": {esc(e.theme)}" if e.theme else "") + "</li>" for e in eds) + "</ul>"


def examples_html(db: Session, brand: Brand | None, ids: list[str] | None = None, sector: str | None = None) -> str:
    from app.proposals import examples as ex

    if not brand:
        return "<p><em>Choose a title first.</em></p>"
    if ids:
        by_id = {str(r.id): r for r in db.scalars(select(ProposalExample).where(ProposalExample.id.in_([uuid.UUID(str(i)) for i in ids])))}
        rows = [by_id[str(i)] for i in ids if str(i) in by_id]
    else:
        ex.ensure_seed(db, brand.key)   # the brand's starting examples, the first time they're needed
        rows = ex.suggest(db, brand.key, sector)
    if not rows:
        return "<p><em>No examples in the library for this brand yet.</em></p>"
    return "<ul>" + "".join(f"<li>{esc(r.label)}: <a href=\"{esc(r.url)}\">see it here</a></li>" for r in rows) + "</ul>"


def render(db: Session, kind: str, config: dict | None, *, title_id=None, lines: list[dict] | None = None, discount_pct: float = 0.0) -> str:
    """One block as HTML."""
    config = config or {}
    brand = brand_of(db, config.get("title_id") or title_id)
    if kind == "package":
        return package_html(lines or [], discount_pct)
    if kind == "prices":
        return prices_html(db, brand, config.get("rate_ids"), config.get("sections"))
    if kind == "stats":
        return stats_html(db, brand)
    if kind == "issues":
        return issues_html(db, config.get("title_id") or title_id, int(config.get("count") or 4))
    if kind == "events":
        return events_html(db, brand)
    if kind == "examples":
        return examples_html(db, brand, config.get("ids"), config.get("sector"))
    return ""


def all_brands() -> list[dict]:
    return [{"key": b.key, "name": b.name} for b in BRANDS]
