"""SALES-003 - "your page is live": when a new issue goes up on BMI's Issuu page, its advertisers are told.

A few times a day this reads BMI's public Issuu page ("Issues Online > Issuu pages to watch"); no login and no Brain
are needed. For each publication that's new and recent:
  1. It's matched to an issue in the editorial plan by its name, number and date (Issuu's "Selling Travel
     September-October 2026" to Selling Travel's September 2026 issue, "obh-107" to OBH issue 107). Free - words and
     dates, no Brain.
  2. One card, "New issue online", shows the publication and the issue it looks like, with the closest others to pick
     from. "Link it and tell the advertisers" saves the link on the issue - so renewal emails can show last year's
     issue too - and gives each salesperson a card for their advertisers in it.
  3. That card has a short "your advert is now live" note drafted with the link. "Open as a mail merge" opens it with
     those advertisers ticked, to change, preview and send from the salesperson's own Outlook.
"""
from __future__ import annotations

import html
import logging
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Company, Contact, Email, ReviewQueueItem, SalesEdition, SalesOrder, SalesRep, SalesTitle, User

logger = logging.getLogger("app.automations.issue_online")

KIND = "issue_online"
NOTES_KIND = "issue_live_notes"
STATE = "issue_online"
MAX_PAGE_BYTES = 3_000_000
CANDIDATES = 5
LIST_LIMIT = 15

_CARD = re.compile(r'href="(/[^"/]+/docs/[^"]+)"[^>]*>.*?data-testid="publication-card-title"[^>]*>(.*?)</p>.*?</a>\s*<div[^>]*>([^<]{4,40})</div>',
                   re.S | re.I)
_WORD = re.compile(r"[a-z0-9]+")
_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september",
                                       "october", "november", "december"], 1)}
_SEASONS = {"spring", "summer", "autumn", "winter"}
# A publication called one of these is something else (a guide, the awards, a supplement) - it only matches an issue
# whose own name says so too.
_OTHER = {"awards", "winners", "guide", "supplement", "map", "planner", "fam", "trip", "directory", "special"}
_BRAND_WORDS = {"obh": {"onboard", "obh", "hospitality"}, "tbtm": {"business", "tbtm", "mag", "magazine"},
                "stm": {"selling", "travel", "stm"}}


# ---- reading Issuu ----------------------------------------------------------------------------------------------

def parse_profile(page: str, base: str = "https://issuu.com") -> list[dict]:
    """The publications on an Issuu profile page: {url, slug, title, published}."""
    out, seen = [], set()
    for href, title, when in _CARD.findall(page or ""):
        if href in seen:
            continue
        seen.add(href)
        try:
            published = datetime.strptime(when.strip(), "%B %d, %Y").date()
        except ValueError:
            published = None
        out.append({"url": base + href, "slug": href.rsplit("/", 1)[-1],
                    "title": re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", title)).replace("\ufeff", "")).strip(),
                    "published": published})
    return out


def fetch(url: str) -> list[dict]:
    import httpx
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (BMI Brain issue check)"}) as c:
        r = c.get(url)
        r.raise_for_status()
        return parse_profile(r.text[:MAX_PAGE_BYTES])


# ---- matching a publication to an issue ------------------------------------------------------------------------------

def _words(text: str) -> set[str]:
    """Lower-case words, with month short forms written out ("jan", "sept" -> "january", "september")."""
    out = set()
    for w in _WORD.findall((text or "").lower().replace("_", " ").replace("-", " ")):
        full = next((m for m in _MONTHS if m.startswith(w)), None) if len(w) >= 3 and not w.isdigit() else None
        out.add(full or w)
    return out


def short_name(t: SalesTitle) -> str:
    """"OnBoard Hospitality (OBH)" -> "OnBoard Hospitality"."""
    return re.sub(r"\s*\(.*?\)", "", t.name)


def _months(words: set[str]) -> set[int]:
    return {_MONTHS[w] for w in words if w in _MONTHS}


def score(pub: dict, ed: SalesEdition, title: SalesTitle) -> int:
    """How alike a publication and an issue are. 0 unless the publication's name has the magazine's name or the issue's
    number in it - months and dates alone match too many issues."""
    from app.sales.brands import brand_for_title_slug
    pw = _words(f"{pub['title']} {pub['slug']}")
    abbrev = (re.search(r"\((\w+)\)", title.name) or [None, ""])[1].lower()
    tw = _words(short_name(title)) | ({abbrev} if abbrev else set())
    b = brand_for_title_slug(title.slug)
    named = 0
    if tw and _words(short_name(title)) <= pw:
        named = 4                                 # the whole title is in the name
    elif abbrev and abbrev in pw:
        named = 4                                 # "obh-107", "tbtm-105"
    elif b and title.slug == b.title_slugs[0] and len(_BRAND_WORDS.get(b.key, set()) & pw) >= 2:
        named = 3                                 # "The Business Travel Mag" for The Business Travel Magazine
    number = 5 if re.fullmatch(r"\d{2,4}", (ed.name or "").strip()) and ed.name.strip() in pw else 0
    ew = _words(f"{ed.name} {ed.period_label or ''}")
    if (not named and not number) or (pw & _OTHER) - ew:
        return 0
    when = 2 * len(_months(pw) & _months(ew)) + 2 * len(ew & pw & _SEASONS)
    close = 0
    if pub.get("published") and ed.edition_date:
        gap = (pub["published"] - ed.edition_date).days
        close = 2 if -45 <= gap <= 45 else (-2 if abs(gap) > 150 else 0)
    if not number and not when and close <= 0:
        return 0                                  # nothing specific: the right magazine, but which issue?
    return named + number + when + close + (1 if ed.year and str(ed.year) in pw else 0)


def candidates(db: Session, pub: dict) -> list[tuple[int, SalesEdition, SalesTitle]]:
    """The issues it could be, best first (issues and guides within a few months of the publication date)."""
    when = pub.get("published") or date.today()
    rows = db.execute(select(SalesEdition, SalesTitle).join(SalesTitle, SalesTitle.id == SalesEdition.title_id)
                      .where(SalesEdition.kind.in_(("issue", "guide")), SalesEdition.edition_date.isnot(None),
                             SalesEdition.edition_date >= when - timedelta(days=200), SalesEdition.edition_date <= when + timedelta(days=120))).all()
    scored = [(score(pub, ed, t), ed, t) for ed, t in rows]
    return sorted((x for x in scored if x[0] >= 4), key=lambda x: (-x[0], abs(((pub.get("published") or when) - x[1].edition_date).days)))[:CANDIDATES]


def _label(ed: SalesEdition, t: SalesTitle) -> str:
    from app.sales.editorial import issue_label
    return f"{short_name(t)}: {issue_label(ed)}" + (f" ({ed.edition_date:%-d %b %Y})" if ed.edition_date else "")


def queue(db: Session, pub: dict, source: str) -> ReviewQueueItem:
    found = candidates(db, pub)
    best = found[0] if found else None
    sure = bool(best and best[0] >= 7 and (len(found) == 1 or best[0] - found[1][0] >= 3))
    details = [{"label": "Publication", "value": pub["title"], "href": pub["url"]},
               {"label": "Put online", "value": f"{pub['published']:%-d %B %Y}" if pub.get("published") else "Not shown"},
               {"label": "Looks like", "value": _label(best[1], best[2]) if best else "No issue in the editorial plan looks like this one",
                **({"href": f"/sales/editions/{best[1].id}"} if best else {})}]
    if best and not sure:
        details.append({"label": "Worth knowing", "value": "Not a sure match - check the issue before linking it."})
    if best:
        n = db.query(SalesOrder).filter(SalesOrder.edition_id == best[1].id, SalesOrder.status == "booked").count()
        details.append({"label": "Advertisers in it", "value": str(n)})
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=best[2].crm_source_db if best else None, status="pending",
        payload={
            "summary": f"New issue online: {pub['title']}", "details": details,
            "publication": {**pub, "published": pub["published"].isoformat() if pub.get("published") else None},
            "open_href": None,
            "field_options": {"edition_id": [{"value": str(ed.id), "label": _label(ed, t)} for _, ed, t in found]},
            "field_defaults": {"edition_id": str(best[1].id)} if best else {},
            "hidden_actions": [] if found else ["link", "link_only"],
            "facets": {"magazine": short_name(best[2]) if best else "Not sure",
                       "match": "Sure match" if sure else "Check the match" if best else "No match", "source": source},
            "sort_date": (pub.get("published") or date.today()).isoformat(),
        },
    )
    db.add(item)
    return item


def scan() -> None:
    db = SessionLocal()
    try:
        pages = runtime_settings.get_csv(db, "issuu_profiles")
        recent = runtime_settings.get_int(db, "issue_online_recent_days")
        st = get_state(db, STATE)
        seen = list(st.get("seen") or [])
        known = set(seen) | {r[0] for r in db.execute(select(SalesEdition.digital_url).where(SalesEdition.digital_url.isnot(None)))}
        queued = 0
        for page in pages:
            try:
                pubs = fetch(page)
            except Exception as exc:   # one page being down never stops the others
                logger.warning("issue online: %s couldn't be read (%s)", page, type(exc).__name__)
                continue
            for pub in pubs:
                if pub["url"] in known:
                    continue
                known.add(pub["url"])
                seen.append(pub["url"])
                if pub.get("published") and pub["published"] < date.today() - timedelta(days=recent):
                    continue   # older than "recent" - put online before we were watching
                queue(db, pub, "Issuu")
                queued += 1
        set_state(db, STATE, {"seen": seen[-3000:]})
        db.commit()
        logger.info("issue online: %d new", queued)
    finally:
        db.close()


# ---- the cards' buttons ----------------------------------------------------------------------------------------------

def _person(db: Session, o: SalesOrder) -> Contact | None:
    """Who to tell at an advertiser: the booking's contact, or someone at the company (marketing people first)."""
    from app.models import SalesDeal
    deal = db.get(SalesDeal, o.deal_id) if o.deal_id else None
    if deal and deal.contact_id:
        c = db.get(Contact, deal.contact_id)
        if c and not c.is_unsubscribed:
            return c
    if not o.company_id:
        return None
    people = db.execute(select(Contact).join(Email, Email.contact_id == Contact.id)
                        .where(Contact.company_id == o.company_id, Contact.is_unsubscribed.is_(False), Contact.has_bounced.is_(False))
                        .order_by(Email.is_primary.desc())).scalars().all()
    return next((p for p in people if re.search(r"market|brand|trade|partner|commercial", p.job_title or "", re.I)), people[0] if people else None)


def note_text(ed: SalesEdition, t: SalesTitle, url: str) -> tuple[str, str]:
    from app.sales.editorial import issue_label
    name = short_name(t)
    subject = f"Your advert in {name} {issue_label(ed)} is now live online"
    body = (f"Dear {{{{salutation|colleague}}}},\n\nThe {issue_label(ed)} issue of {name} is now live online, including your "
            f"advert. You can see it here:\n{url}\n\nPlease feel free to share the link with your team and on social media.\n\n"
            "Kind regards,\n{{my_name}}")
    return subject, body


def tell_advertisers(db: Session, ed: SalesEdition, url: str) -> list[ReviewQueueItem]:
    """One card per salesperson with advertisers in the issue."""
    t = db.get(SalesTitle, ed.title_id)
    by_rep: dict = defaultdict(list)
    for o in db.scalars(select(SalesOrder).where(SalesOrder.edition_id == ed.id, SalesOrder.status == "booked")):
        by_rep[o.rep_id].append(o)
    subject, body = note_text(ed, t, url)
    cards = []
    for rep_id, orders in by_rep.items():
        rep = db.get(SalesRep, rep_id) if rep_id else None
        owner = db.get(User, rep.user_id) if rep and rep.user_id else None
        people, nobody, seen = [], [], set()
        for o in orders:
            p = _person(db, o)
            if p and p.id not in seen:
                seen.add(p.id)
                people.append((o, p))
            elif not p:
                nobody.append(o.client_name)
        if not people and not nobody:
            continue
        details = [{"label": "Issue", "value": _label(ed, t), "href": f"/sales/editions/{ed.id}"},
                   {"label": "Online", "value": url, "href": url}]
        for o, p in people[:LIST_LIMIT]:
            details.append({"label": o.client_name, "value": p.full_name or "Contact", "href": f"/contacts/{p.id}"})
        if len(people) > LIST_LIMIT:
            details.append({"label": "And", "value": f"{len(people) - LIST_LIMIT} more - all listed in the mail merge"})
        if nobody:
            details.append({"label": "No one to email at", "value": ", ".join(sorted(set(nobody)))[:500]})
        card = ReviewQueueItem(
            id=uuid.uuid4(), kind=NOTES_KIND, source_db=t.crm_source_db, status="pending",
            payload={
                "summary": f"{short_name(t)} {ed.name} is online - tell {len(people)} advertiser{'s' if len(people) != 1 else ''}",
                "details": details, "original_text": f"Subject: {subject}\n\n{body}", "original_label": "Drafted note",
                "edition_id": str(ed.id), "owner_user_id": str(owner.id) if owner else None,
                "merge": {"contact_ids": [str(p.id) for _, p in people], "subject": subject, "body": body,
                          "label": f"Live online: {t.name} {ed.name}"[:300]},
                "hidden_actions": [] if people else ["open_merge"],
                "related_entities": [{"type": "contact", "id": str(p.id), "label": p.full_name or o.client_name} for o, p in people[:LIST_LIMIT]],
                "facets": {"magazine": short_name(t), "salesperson": (owner.name or owner.email) if owner else "No one"},
                "sort_date": (ed.edition_date or date.today()).isoformat(),
            })
        db.add(card)
        cards.append(card)
    return cards


def _link(db: Session, item: ReviewQueueItem, input_data: dict, tell: bool) -> None:
    from app.services.field_audit import record_field_changes
    p = item.payload
    eid = (input_data.get("edition_id") or (p.get("field_defaults") or {}).get("edition_id") or "").strip()
    ed = db.get(SalesEdition, uuid.UUID(eid)) if re.fullmatch(r"[0-9a-f-]{36}", eid) else None
    if not ed:
        raise ValueError("Choose the issue this publication is.")
    url = (p.get("publication") or {}).get("url")
    actor = input_data.get("_actor_user_id")
    record_field_changes(db, entity_type="sales_edition", entity_id=ed.id, before={"digital_url": ed.digital_url},
                         updates={"digital_url": url}, changed_by_user_id=uuid.UUID(actor) if actor else None)
    ed.digital_url = url
    made = tell_advertisers(db, ed, url) if tell else []
    t = db.get(SalesTitle, ed.title_id)
    done = f"Linked to {_label(ed, t)}" + (f"; {len(made)} card{'s' if len(made) != 1 else ''} for the salespeople to tell their advertisers" if tell else "")
    item.payload = {**p, "details": [{"label": "Done", "value": done, "href": f"/sales/editions/{ed.id}"}, *p["details"]]}


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "link":
        _link(db, item, input_data, tell=True)
    elif action_id == "link_only":
        _link(db, item, input_data, tell=False)
    elif action_id != "not_ours":
        raise ValueError("That button isn't available on this card.")


def _handle_notes(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "open_merge":
        item.payload = {**item.payload, "open_href": f"/mail-merge?review={item.id}"}
    elif action_id != "not_needed":
        raise ValueError("That button isn't available on this card.")


ISSUE = ExtraField(key="edition_id", label="Which issue is it?", field_type="select")

register(ReviewKind(
    kind=KIND,
    label="New issues online",
    description="A new publication on BMI's Issuu page, matched to its issue, ready to link and tell the advertisers in it.",
    actions=[
        ReviewAction(id="link", label="Link it and tell the advertisers", style="primary", outcome="approved", extra_fields=[ISSUE]),
        ReviewAction(id="link_only", label="Just link it", style="secondary", outcome="approved", extra_fields=[ISSUE]),
        ReviewAction(id="not_ours", label="Not one of our issues", style="secondary", outcome="rejected", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("magazine", "Magazine"), ("match", "Match"), ("source", "Found on")),
    date_sort_label="date put online",
))

register(ReviewKind(
    kind=NOTES_KIND,
    label="Tell advertisers they're live",
    description="Your advertisers in an issue that's just gone online, with a short note drafted with the link to send as a mail merge.",
    actions=[
        ReviewAction(id="open_merge", label="Open as a mail merge", style="primary", outcome="approved"),
        ReviewAction(id="not_needed", label="No need this time", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle_notes,
    audience="sales",
    facets=(("magazine", "Magazine"), ("salesperson", "Salesperson")),
    date_sort_label="issue date",
))

register_job(ScheduledJob(
    id="issue_online_scan",
    label="New issues online",
    description="Reads BMI's Issuu page for new publications and matches each one to its issue.",
    cron="35 */6 * * *",
    func=scan,
    enabled_flag="automations_issue_online_enabled",
))
