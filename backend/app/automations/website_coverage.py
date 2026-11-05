"""SALES-004 coverage forwarding, website side ("Brevo > Spot clients in the newsletters" covers the newsletters).

Every three hours, new stories on BMI's own websites are read for the names of BMI's clients (companies with a booking
in the last two years). Each salesperson gets one card per story for their clients in it, with a short "you're in
the news" note drafted, opened as a mail merge to check and send - the same card as a newsletter mention.

The sites are WordPress, which lists its newest stories publicly at /wp-json/wp/v2/posts; no key or login needed.
"""
from __future__ import annotations

import html
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

from app.automations import runtime_settings
from app.automations.brevo_sync import coverage_cards
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal

logger = logging.getLogger("app.automations.website_coverage")

KIND = "website_coverage"
STATE = "website_coverage"
SITE_NAME = {"thebusinesstravelmag.com": "The Business Travel Magazine", "sellingtravel.co.uk": "Selling Travel",
             "onboardhospitality.com": "Onboard Hospitality"}


def site_name(url: str) -> str:
    host = urlparse(url if "//" in url else f"https://{url}").netloc.lower().removeprefix("www.")
    return SITE_NAME.get(host, host)


def new_stories(site: str, since: datetime) -> list[dict]:
    """[{"id", "title", "link", "published", "html"}] published after `since`, newest last. Raises httpx.HTTPError."""
    base = (site if "//" in site else f"https://{site}").rstrip("/")
    r = httpx.get(f"{base}/wp-json/wp/v2/posts", timeout=30, follow_redirects=True,
                  headers={"User-Agent": "BMI Brain (BMI Publishing)"},
                  params={"after": since.strftime("%Y-%m-%dT%H:%M:%S"), "per_page": 50, "orderby": "date", "order": "asc",
                          "_fields": "id,date_gmt,link,title,content"})
    r.raise_for_status()
    out = []
    for p in r.json() if isinstance(r.json(), list) else []:
        out.append({"id": f"{base}#{p.get('id')}", "title": html.unescape((p.get("title") or {}).get("rendered") or "").strip(),
                    "link": p.get("link") or "", "published": (p.get("date_gmt") or "")[:19],
                    "html": (p.get("content") or {}).get("rendered") or ""})
    return out


def scan() -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        st = get_state(db, STATE)
        since_by_site = dict(st.get("since") or {})
        seen = set(st.get("seen") or [])
        made = read = 0
        for site in runtime_settings.get_csv(db, "coverage_sites"):
            site = site.strip()
            if not site:
                continue
            since = datetime.fromisoformat(since_by_site[site]) if site in since_by_site else now - timedelta(days=2)
            try:
                stories = new_stories(site, since)
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("website coverage: %s couldn't be read (%s)", site, type(exc).__name__)
                continue
            where = f"a story on {site_name(site)}'s website"
            for s in stories:
                read += 1
                if s["id"] in seen:
                    continue
                seen.add(s["id"])
                made += len(coverage_cards(db, {"id": s["id"], "subject": s["title"] or "a story", "shareLink": s["link"],
                                                "htmlContent": s["html"], "sentDate": s["published"]}, kind=KIND, where=where))
                if s["published"]:
                    since = max(since, datetime.fromisoformat(s["published"]).replace(tzinfo=timezone.utc))
            since_by_site[site] = since.isoformat()
            db.commit()
        set_state(db, STATE, {"since": since_by_site, "seen": sorted(seen)[-2000:]})
        db.commit()
        logger.info("website coverage: %d stories read, %d cards", read, made)
    finally:
        db.close()


def _handle(db, item, action_id: str, input_data: dict) -> None:
    if action_id == "open_merge":
        item.payload = {**item.payload, "open_href": f"/mail-merge?review={item.id}"}
    elif action_id != "not_needed":
        raise ValueError("That button isn't available on this card.")


register(ReviewKind(
    kind=KIND,
    label="Clients in a website story",
    description="Your clients named in a new story on one of BMI's websites, with a short note drafted to tell them, sent as a mail merge.",
    actions=[
        ReviewAction(id="open_merge", label="Open as a mail merge", style="primary", outcome="approved", keeps_open=True),
        ReviewAction(id="not_needed", label="No need this time", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("salesperson", "Salesperson"), ("reach", "Contact")),
    date_sort_label="date published",
))

register_job(ScheduledJob(
    id="website_coverage_scan",
    label="Clients in a website story",
    description="Every three hours, reads new stories on BMI's websites for the names of BMI's clients, and drafts a note to tell them.",
    cron="20 */3 * * *",
    func=scan,
    enabled_flag="automations_website_coverage_enabled",
))
