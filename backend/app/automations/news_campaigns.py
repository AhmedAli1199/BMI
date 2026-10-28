"""SALES-031 - campaigns started by the news.

Some of the best selling moments arrive as news: when the government's travel advice reopened a set of destinations,
a salesperson spent the next day emailing every tourist board and airline involved by hand. This watches the news
feeds in "News campaigns > News feeds to watch" (GOV.UK's travel advice to start with) and, when something is a reason
for companies to advertise, puts a ready campaign in the Review Queue:
  1. New items in the feeds are read every couple of hours. A free word check keeps only news that sounds like good
     news for someone (advice lifted or eased, a destination reopening, flights resuming, a new route...), up to
     "Most news items the Brain checks per run".
  2. The Brain decides whether it really is a selling moment and for whom: the destinations, the kinds of business
     (tourist boards, airlines, hotels, tour operators), the magazine it suits, and the angle. Without the Brain
     nothing is queued - the judgement is the point.
  3. The CRM is searched for companies linked to those destinations (in their name, industry, category, region or
     address), the kinds of business it named first, each with one person to email - marketing or trade people ahead
     of others - up to "Most companies in one campaign".
  4. One card per moment, for any salesperson to pick up, with the email drafted. "Open as a mail merge" opens the
     mail merge screen with those people and the draft filled in, to change, preview and send from their own Outlook.
The Brain writes the email from the news alone and may not add any figure; the media pack link comes from the brand's
settings page in Editorial.
"""
from __future__ import annotations

import html
import logging
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Address, Company, Contact, Email, ReviewQueueItem

logger = logging.getLogger("app.automations.news_campaigns")

KIND = "news_campaign"
STATE = "news_campaigns"
MAX_FEED_BYTES = 2_000_000
FRESH_DAYS = 3          # older news is no longer a moment
LIST_LIMIT = 15
FEED_NAMES = {"www.gov.uk": "GOV.UK travel advice"}

_GOOD_NEWS = re.compile(
    r"\b(no longer advis\w*|removed|lift\w*|reopen\w*|re-open\w*|resum\w*|eas(e|ed|es|ing)|relax\w*|launch\w*|"
    r"new (route|service|flights?|hotel|ship)|restart\w*|return\w*|back on sale|open(s|ed|ing)? (to|for)|welcom\w*)\b", re.I)
_BUDGET_ROLE = re.compile(r"market\w*|trade|partner\w*|commercial|sales|brand|business development", re.I)

_PROMPT = (
    "You work for BMI Publishing, a UK publisher of magazines for travel agents (Selling Travel), business travel buyers "
    "(The Business Travel Magazine) and airline and rail catering and retail (Onboard Hospitality). Read one news item "
    "and decide whether it is a selling moment: a reason for particular companies to advertise with us right now "
    "(a destination reopening or advice easing, flights resuming, a new route, a reopening hotel or attraction). "
    "Warnings, disasters, strikes and closures are not. Return JSON: {\"selling_moment\": bool, \"why\": one sentence, "
    "\"headline\": the moment in under 10 words, \"destinations\": [countries, regions or cities it's about], "
    "\"search_terms\": [words a company linked to it would have in its name, e.g. the country, its adjective, its main "
    "cities], \"sectors\": [the kinds of business that would want to advertise, e.g. tourist board, airline, hotel, tour "
    "operator, cruise], \"magazine\": Selling Travel|The Business Travel Magazine|Onboard Hospitality, \"angle\": one "
    "sentence on why they should tell our readers now}. Never invent a value - use null or []."
)

_EMAIL_PROMPT = (
    "Write the middle of a short email from a magazine salesperson to a company linked to the news below. Two or three "
    "sentences: mention the news, why now is the moment to tell the magazine's readers, and offer to talk. British "
    "English, plain text. No greeting line, no sign-off, and no prices, figures or dates."
)


# ---- the feeds ------------------------------------------------------------------------------------------

def _text(el) -> str:
    raw = "".join(el.itertext()) if el is not None else ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def _when(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            d = parsedate_to_datetime(s.strip())
        except (TypeError, ValueError):
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse_feed(data: bytes) -> list[dict]:
    """The items in an RSS or Atom feed: {id, title, summary, link, published}. A feed that declares its own entities is
    refused rather than read."""
    if len(data) > MAX_FEED_BYTES or re.search(rb"<!(DOCTYPE|ENTITY)", data[:4000], re.I):
        return []
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    atom = "{http://www.w3.org/2005/Atom}"
    items = []
    for e in root.iter(f"{atom}entry"):
        link = next((l.get("href") for l in e.findall(f"{atom}link") if l.get("rel", "alternate") == "alternate"), None)
        items.append({"id": _text(e.find(f"{atom}id")) or link, "title": _text(e.find(f"{atom}title")),
                      "summary": _text(e.find(f"{atom}summary")) or _text(e.find(f"{atom}content")), "link": link,
                      "published": _when(_text(e.find(f"{atom}updated")) or _text(e.find(f"{atom}published")))})
    for e in root.iter("item"):
        link = _text(e.find("link"))
        items.append({"id": _text(e.find("guid")) or link, "title": _text(e.find("title")), "summary": _text(e.find("description")),
                      "link": link, "published": _when(_text(e.find("pubDate")))})
    return [i for i in items if i["id"] and i["title"]]


def fetch(url: str) -> list[dict]:
    import httpx
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "BMI Brain news check"}) as c:
        r = c.get(url)
        r.raise_for_status()
        return parse_feed(r.content[:MAX_FEED_BYTES + 1])


def feed_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return FEED_NAMES.get(host, host.removeprefix("www.") or "News feed")


def worth_a_look(item: dict) -> bool:
    return bool(_GOOD_NEWS.search(f"{item['title']} {item['summary']}"))


def judge(item: dict) -> dict | None:
    from app.automations.llm import extract_json, is_configured
    if not is_configured():
        return None
    out = extract_json(_PROMPT, f"NEWS ({item['source']}):\n{item['title']}\n\n{item['summary'][:3000]}", max_tokens=500,
                       purpose="news_campaigns.judge")
    if not isinstance(out, dict) or not out.get("selling_moment"):
        return None
    for k in ("destinations", "search_terms", "sectors"):
        out[k] = [str(x).strip() for x in (out.get(k) or []) if str(x).strip() and len(str(x).strip()) >= 3][:10]
    return out


# ---- who to email -----------------------------------------------------------------------------------------

def companies_for(db: Session, moment: dict, limit: int) -> list[tuple[Company, Contact, str]]:
    """(company, the person to email, their address) for companies linked to the moment's places, the kinds of business it
    named first. One person per company, marketing or trade people first; unsubscribed or bounced people never."""
    terms = list(dict.fromkeys([*moment.get("search_terms", []), *moment.get("destinations", [])]))
    if not terms:
        return []
    likes = [f"%{t}%" for t in terms]
    fields = (Company.name, Company.industry, Company.category, Company.region, Company.territory, Company.description)
    by_text = or_(*[f.ilike(p) for f in fields for p in likes])
    by_place = select(Address.company_id).where(Address.company_id.isnot(None),
                                                or_(*[a.ilike(p) for a in (Address.country, Address.city) for p in likes]))
    found = list(db.scalars(select(Company).where(or_(by_text, Company.id.in_(by_place))).limit(limit * 4)))
    sectors = [s.lower() for s in moment.get("sectors", [])]
    words = {w for s in sectors for w in re.findall(r"[a-z]{4,}", s)}

    def fits(c: Company) -> int:
        text = " ".join(x or "" for x in (c.name, c.industry, c.category, c.description)).lower()
        return -sum(1 for w in words if w in text)

    out = []
    for co in sorted(found, key=lambda c: (fits(c), c.name.lower())):
        people = db.execute(select(Contact, Email.address).join(Email, Email.contact_id == Contact.id)
                            .where(Contact.company_id == co.id, Contact.is_unsubscribed.is_(False), Contact.has_bounced.is_(False),
                                   Email.address.isnot(None))
                            .order_by(Email.is_primary.desc())).all()
        if not people:
            continue
        person, address = next(((p, a) for p, a in people if _BUDGET_ROLE.search(p.job_title or "")), people[0])
        out.append((co, person, address))
        if len(out) >= limit:
            break
    return out


def _title(db: Session, magazine: str | None):
    from app.automations.press_releases import _main_title
    from app.automations.proposal_requests import _title_for
    return _main_title(db, _title_for(db, magazine, None)) if magazine else None


def draft(db: Session, item: dict, moment: dict, title) -> tuple[str, str, bool]:
    """(subject, body with merge fields, ai_used)."""
    from app.automations.llm import draft_text, is_configured
    from app.automations.press_releases import media_pack
    from app.proposals.drafting import numbers_in

    brand, link, _ = media_pack(db, title)
    brand = brand or "our magazine"
    headline = (moment.get("headline") or item["title"]).strip().rstrip(".")
    text = (f"With the news - {headline} - now is a great moment to remind {brand}'s readers what you offer. "
            "I'd be happy to share some ideas for getting in front of them while it's fresh - just reply to this email.")
    ai = False
    if is_configured():
        got = draft_text(_EMAIL_PROMPT + f" The magazine is {brand}.",
                         f"THE NEWS:\n{item['title']}\n{item['summary'][:2000]}\n\nANGLE: {moment.get('angle') or ''}",
                         max_tokens=200, purpose="news_campaigns.draft")
        if got and not numbers_in(got) and len(got) < 900:
            text, ai = got.strip(), True
    pack = f"\n\nOur media pack has the details: {link}" if link else ""
    body = f"Dear {{{{salutation|colleague}}}},\n\n{text}{pack}\n\nKind regards,\n{{{{my_name}}}}"
    return f"{headline} - {brand}", body, ai


def queue(db: Session, item: dict, moment: dict, limit: int) -> ReviewQueueItem:
    from app.automations.press_releases import media_pack
    from app.automations.proposal_requests import short_name

    title = _title(db, moment.get("magazine"))
    picked = companies_for(db, moment, limit)
    subject, body, ai = draft(db, item, moment, title)
    _, link, _ = media_pack(db, title)
    details = [{"label": "The news", "value": item["title"], **({"href": item["link"]} if item.get("link") else {})},
               {"label": "From", "value": item["source"]}]
    if item["summary"]:
        details.append({"label": "What changed", "value": item["summary"][:400]})
    for k, label in (("why", "Why it's a moment"), ("angle", "The angle")):
        if moment.get(k):
            details.append({"label": label, "value": moment[k]})
    if moment.get("sectors"):
        details.append({"label": "Who'd want to advertise", "value": ", ".join(moment["sectors"])})
    if title:
        details.append({"label": "Magazine", "value": title.name})
    details.append({"label": "Companies found", "value": f"{len(picked)} in the CRM" if picked else
                    "None in the CRM yet - search for companies linked to " + (", ".join(moment.get("destinations") or []) or "this news")})
    for co, person, address in picked[:LIST_LIMIT]:
        details.append({"label": co.name, "value": f"{person.full_name or address} ({address})", "href": f"/companies/{co.id}"})
    if len(picked) > LIST_LIMIT:
        details.append({"label": "And", "value": f"{len(picked) - LIST_LIMIT} more - all listed in the mail merge"})
    if not link:
        details.append({"label": "Worth knowing", "value": "No media pack link is saved for this magazine, so the email doesn't include one - add it as Media pack link on the brand's settings page in Editorial."})
    when = item.get("published") or datetime.now(timezone.utc)
    rqi = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=None, status="pending",
        payload={
            "summary": f"News: {moment.get('headline') or item['title']} - {len(picked)} {'company' if len(picked) == 1 else 'companies'} to email",
            "details": details, "original_text": f"Subject: {subject}\n\n{body}", "original_label": "Drafted email",
            "news_id": item["id"], "news_link": item.get("link"), "moment": moment, "title_id": str(title.id) if title else None,
            "merge": {"contact_ids": [str(p.id) for _, p, _ in picked], "subject": subject, "body": body,
                      "label": f"News: {moment.get('headline') or item['title']}"[:300]},
            "hidden_actions": [] if picked else ["open_merge"],
            "related_entities": [{"type": "company", "id": str(co.id), "label": co.name} for co, _, _ in picked[:LIST_LIMIT]],
            "ai_drafted": ai,
            "facets": {"magazine": short_name(title) if title else "Not sure", "source": item["source"],
                       "companies": "Companies found" if picked else "None found"},
            "sort_date": when.date().isoformat(),
        },
    )
    db.add(rqi)
    return rqi


def scan() -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        feeds = runtime_settings.get_csv(db, "news_campaign_feeds")
        cap = runtime_settings.get_int(db, "news_campaign_llm_max_per_run")
        limit = runtime_settings.get_int(db, "news_campaign_max_companies")
        st = get_state(db, STATE)
        seen = list(st.get("seen") or [])
        known = set(seen)
        used = queued = 0
        for url in feeds:
            try:
                items = fetch(url)
            except Exception as exc:   # one feed being down never stops the others
                logger.warning("news campaigns: feed %s couldn't be read (%s)", url, type(exc).__name__)
                continue
            for it in sorted(items, key=lambda i: i["published"] or now):
                if it["id"] in known:
                    continue
                if it["published"] and it["published"] < now - timedelta(days=FRESH_DAYS):
                    known.add(it["id"]); seen.append(it["id"])
                    continue
                if not worth_a_look(it):
                    known.add(it["id"]); seen.append(it["id"])
                    continue
                if used >= cap:
                    break
                used += 1
                it["source"] = feed_name(url)
                moment = judge(it)
                known.add(it["id"]); seen.append(it["id"])
                if moment:
                    queue(db, it, moment, limit)
                    queued += 1
        set_state(db, STATE, {"seen": seen[-3000:]})
        db.commit()
        logger.info("news campaigns: %d checked by the Brain, %d cards", used, queued)
    finally:
        db.close()


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "open_merge":
        if not (item.payload.get("merge") or {}).get("contact_ids"):
            raise ValueError("No one in the CRM was found for this news, so there's no one to email yet.")
        item.payload = {**item.payload, "open_href": f"/mail-merge?review={item.id}"}
    elif action_id not in ("not_now", "not_moment"):
        raise ValueError("That button isn't available on this card.")


register(ReviewKind(
    kind=KIND,
    label="News campaigns",
    description="News that's a reason for companies to advertise now - a destination reopening, flights resuming - with the companies to email and the email drafted.",
    actions=[
        ReviewAction(id="open_merge", label="Open as a mail merge", style="primary", outcome="approved"),
        ReviewAction(id="not_now", label="Not now", style="secondary", outcome="dismissed", reopenable=True),
        ReviewAction(id="not_moment", label="Not a selling moment", style="secondary", outcome="rejected", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("magazine", "Magazine"), ("source", "News from"), ("companies", "Companies")),
    date_sort_label="date of the news",
))

register_job(ScheduledJob(
    id="news_campaign_scan",
    label="News campaigns",
    description="Reads the news feeds for selling moments, finds the companies to email and drafts the campaign.",
    cron="25 */2 * * *",
    func=scan,
    enabled_flag="automations_news_campaigns_enabled",
))
