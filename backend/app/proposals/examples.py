"""The examples library: links a salesperson drops into a proposal - past pages that show what a format looks
like ("Spotlight on JetBlue, page 38") and resources (media pack, features list, awards site).

Shared by everyone on a brand, so one person's good examples help the rest. Each link is tagged by format and
sector, so a proposal for an airline can be offered airline examples first. The links are checked weekly, and a
broken one is flagged instead of quietly going out to a client.

The first set is The Business Travel Magazine's, taken from Kirsty's proposals (Oct 2026), with the email
security scanner's wrapping (urldefense.proofpoint.com) taken off so clients see the real address.
"""
from __future__ import annotations

import logging
import re
import urllib.parse
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ProposalExample

logger = logging.getLogger("app.proposals.examples")

SECTORS = {"airline": "Airlines", "hotel": "Hotels and accommodation", "tech": "Travel technology", "tmc": "TMCs",
           "tourism": "Tourist offices and destinations", "rail": "Rail and ground transport", "travel_services": "Travel services",
           "other": "Other"}

ISSUU = "https://issuu.com/bmipublishingltd/docs/"
# (kind, label, url, format, sector, client)
TBTM_SEED: list[tuple[str, str, str, str | None, str | None, str | None]] = [
    ("resource", "Media information pack 2026 (print, digital and events)", "https://thebusinesstravelmag.com/wp-content/uploads/2025/12/TBTM-Media-PACK-2026-1.pdf", "Media pack", None, None),
    ("resource", "Forward features for 2026", "https://thebusinesstravelmag.com/wp-content/uploads/2025/11/TBTM-FF-2026.pdf", "Features list", None, None),
    ("resource", "The Business Travel Magazine website", "https://thebusinesstravelmag.com/", "Website", None, None),
    ("resource", "People Awards 2026 sponsorship information", "https://thebusinesstravelmag.com/wp-content/uploads/2025/11/TBTPA-Sponsorship-2026.pdf", "Awards", None, None),
    ("resource", "The Business Travel People Awards website", "https://awards.thebusinesstravelmag.com/", "Awards", None, None),
    ("resource", "Event galleries", "https://thebusinesstravelmag.com/category/galleries/", "Events", None, None),
    ("resource", "Tech Hotlist 2025", "https://thebusinesstravelmag.com/tech-hotlist-2025/", "Tech Hotlist", "tech", None),
    ("resource", "Tech Hotlist 2024", "https://thebusinesstravelmag.com/the-2024-tech-hotlist/", "Tech Hotlist", "tech", None),
    ("example", "Double page focus on SAF by easyJet", ISSUU + "the_business_travel_mag_spring_issue_2025/26", "Double page sponsored", "airline", "easyJet"),
    ("example", "Double page from Virgin: hybrid display and advertorial", ISSUU + "the_business_travel_mag_spring_issue_2025/28", "Double page sponsored", "airline", "Virgin Atlantic"),
    ("example", "Double page: Lufthansa anniversary", ISSUU + "the_business_travel_mag_summer_2026/22", "Double page sponsored", "airline", "Lufthansa"),
    ("example", "Double page: Virgin full page advert with advertorial", ISSUU + "tbtm-98/26", "Double page sponsored", "airline", "Virgin Atlantic"),
    ("example", "Meeting In… Budapest: we write the full page facing your advert", ISSUU + "tbtm-99/52", "Meeting In…", "tourism", "Budapest"),
    ("example", "Insight (page 8)", ISSUU + "tbtm-99/8", "Insight", None, None),
    ("example", "Insight (page 9)", ISSUU + "tbtm-104/9", "Insight", None, None),
    ("example", "Insight (page 21)", ISSUU + "the_business_travel_mag_summer_2026/21", "Insight", None, None),
    ("example", "Spotlight on JetBlue (page 38)", ISSUU + "tbtm-99/38", "Spotlight on", "airline", "JetBlue"),
    ("example", "Spotlight on Virgin (page 21)", ISSUU + "tbtm-101/21", "Spotlight on", "airline", "Virgin Atlantic"),
    ("example", "Spotlight on Holiday Extras for Business", ISSUU + "the_business_travel_mag_summer_2025/10", "Spotlight on", "travel_services", "Holiday Extras"),
    ("example", "Ask the Expert: full page with a full page advert (pages 8-9)", ISSUU + "tbtm-96/8", "Ask the Expert", None, None),
    ("example", "Ask the Expert: single page (page 13)", ISSUU + "tbtm-98/13", "Ask the Expert", None, None),
    ("example", "Ask the Expert: double page (page 10)", ISSUU + "tbtm-95/10", "Ask the Expert", None, None),
    ("example", "Q&A with ATPI (pages 38-39)", ISSUU + "tbtm-102/38", "Q&A", "tmc", "ATPI"),
    ("example", "Q&A with Lufthansa (page 28)", ISSUU + "the_business_travel_mag_winter_2025/28", "Q&A", "airline", "Lufthansa"),
    ("example", "Q&A with Atriis", ISSUU + "the_business_travel_mag_autumn_2025/12", "Q&A", "tech", "Atriis"),
    ("example", "Wings (page 27)", ISSUU + "the_business_travel_mag_summer_2026/27", "Q&A", None, "Wings"),
    ("example", "Meet the Team (page 18)", ISSUU + "tbtm-102/18", "Meet the Team", None, None),
    ("example", "Team Talk (page 8)", ISSUU + "serviced_accommodation_guide_2025", "Meet the Team", "hotel", None),
    ("example", "Travel Counsellors (page 44)", ISSUU + "the_business_travel_mag_summer_2026/44", "Meet the Team", "tmc", "Travel Counsellors"),
    ("example", "Five tips on… (page 44)", ISSUU + "tbtm-101/10", "Five tips", None, None),
    ("example", "Take five with Front (page 33)", ISSUU + "the_business_travel_mag_summer_2026/33", "Take five", "tech", "Front"),
    ("example", "Guest column: Jack's Journal (page 15)", ISSUU + "the_business_travel_mag_summer_2026/15", "Guest column", None, None),
    ("example", "Guest columns: On the Road and Sustainability Unfiltered", ISSUU + "the_business_travel_mag_summer_2026/16", "Guest column", None, None),
    ("example", "Guest columns: TMC View and Ask Alister", ISSUU + "the_business_travel_mag_summer_2026/18", "Guest column", "tmc", None),
    ("example", "The Big Interview with Oversee (page 34)", ISSUU + "the_business_travel_mag_summer_2026/34", "The Big Interview", "tech", "Oversee"),
    ("example", "The Big Interview with Talma (page 38)", ISSUU + "the_business_travel_mag_summer_2026/38", "The Big Interview", None, "Talma"),
    ("example", "The Conversation: Jo Layton (pages 10-11)", ISSUU + "tbtm-100/10", "The Conversation", None, None),
    ("example", "The Conversation: Steve Singh (pages 10-11)", ISSUU + "tbtm-104", "The Conversation", "tech", None),
    ("example", "The Conversation: Jamie Pherous (pages 10-11)", ISSUU + "tbtm-105/10", "The Conversation", "tmc", None),
    ("example", "Digital only: 'Study highlights rail productivity' in the newsletter", "https://r.mail.bmipublishing.co.uk/mk/mr/sh/1f8JAEm0cwRgRzFb839d9erEzz/NWnPcU--8I2l", "Digital only", "rail", None),
    ("example", "Digital only: breaking news for Thrust Carbon", "https://r.mail.bmipublishing.co.uk/mk/mr/sh/7nVTPdm3ThWmaOcumuUFWF9YYGJSbWF/KlZADbGvDcJb", "Digital only", "tech", "Thrust Carbon"),
    ("example", "Digital only: Inntel launches strategic roadmap", "https://thebusinesstravelmag.com/inntel-launches-bold-strategic-roadmap-following-record-growth/", "Digital only", "tmc", "Inntel"),
    ("example", "Digital only: In Conversation with Kevin Harrison", "https://thebusinesstravelmag.com/kevin-harrison-the-good-travel-collective/", "Digital only", "tmc", "The Good Travel Collective"),
    ("example", "Lunch Forum write-up: ground transportation", ISSUU + "the_business_travel_mag_autumn_2025/50", "Event write-up", "rail", None),
    ("example", "Lunch Forum write-up: technology", ISSUU + "the_business_travel_mag_winter_2025/56", "Event write-up", "tech", None),
]

SEEDS = {"tbtm": TBTM_SEED}


def clean_url(url: str) -> str:
    """Takes off an email security scanner's wrapping (urldefense.proofpoint.com/v2/url?u=...), so the client sees
    and gets the real address."""
    url = (url or "").strip()
    if "urldefense.proofpoint.com/v2/url" in url:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("u", [""])[0]
        if q:
            # v2 encoding: "-" + two hex digits is a character, "_" is "/".
            url = re.sub(r"-([0-9A-F]{2})", lambda m: chr(int(m.group(1), 16)), q.replace("_", "/"))
    elif "urldefense.com/v3/__" in url:
        url = url.split("__")[1] if "__" in url else url
    return url


def ensure_seed(db: Session, brand: str) -> int:
    """Loads the brand's starting examples once (only into an empty library)."""
    seed = SEEDS.get(brand)
    if not seed or db.scalar(select(func.count()).select_from(ProposalExample).where(ProposalExample.brand == brand)):
        return 0
    for i, (kind, label, url, fmt, sector, client) in enumerate(seed):
        db.add(ProposalExample(id=uuid.uuid4(), brand=brand, kind=kind, label=label, url=url, format=fmt, sector=sector,
                               client=client, sort_order=i))
    db.flush()
    return len(seed)


def suggest(db: Session, brand: str, sector: str | None = None, limit: int = 6) -> list[ProposalExample]:
    """Examples to offer first: the client's sector, then one of each other format, never a broken link."""
    rows = list(db.scalars(select(ProposalExample).where(ProposalExample.brand == brand, ProposalExample.kind == "example",
                                                          ProposalExample.archived.is_(False), ProposalExample.link_ok.isnot(False))
                           .order_by(ProposalExample.sort_order)))
    picked: list[ProposalExample] = [r for r in rows if sector and r.sector == sector][:limit]
    formats = {r.format for r in picked}
    for r in rows:
        if len(picked) >= limit:
            break
        if r not in picked and r.format not in formats:
            picked.append(r)
            formats.add(r.format)
    return picked


def check_link(url: str) -> bool:
    if url.startswith("mailto:"):
        return True
    try:
        with httpx.Client(timeout=10, follow_redirects=True, headers={"User-Agent": "BMI Brain link check"}) as c:
            r = c.head(url)
            if r.status_code >= 400 or r.status_code == 405:
                r = c.get(url)
            return r.status_code < 400
    except httpx.HTTPError:
        return False


def check_links(db: Session, rows: list[ProposalExample]) -> int:
    """Checks each link and returns how many are broken."""
    broken = 0
    now = datetime.now(timezone.utc)
    for r in rows:
        r.link_ok, r.checked_at = check_link(r.url), now
        broken += 0 if r.link_ok else 1
    return broken
