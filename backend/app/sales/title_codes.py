"""Short codes for publications (Craig, feedback #25): BMI calls issues "OBH108", "TBTM Events", so the booking form
lists them that way. Set per publication on the Rate card page (Online links and codes); these are the starting guesses."""
from __future__ import annotations

import re

GUESSES = {
    "obh": "OBH", "obh-awards": "OBH Awards", "obh-web": "OBH Web", "obh-forum-asia": "OBH Forum Asia",
    "selling-travel": "ST", "selling-travel-online": "ST Online", "selling-travel-supplements": "ST Supplements",
    "selling-travel-guides": "ST Guides", "selling-travel-events": "ST Events", "selling-canada": "SC",
    "selling-australia": "SA", "stm-connect-events": "STM Connect", "tbtm": "TBTM", "tbtm-events": "TBTM Events",
    "visit-usa-online": "VUSA Online", "visit-usa-planner": "VUSA Planner", "travel-for-every-body-awards": "TFEB Awards",
}


def guess(slug: str, name: str) -> str:
    if slug in GUESSES:
        return GUESSES[slug]
    bracket = re.search(r"\(([A-Z]{2,6})\)", name or "")
    if bracket:
        return bracket.group(1)
    words = [w for w in re.findall(r"[A-Za-z]+", name or "") if w.lower() not in {"the", "and", "of", "for"}]
    return "".join(w[0].upper() for w in words)[:6] or (name or slug)[:6]


def coded_label(code: str | None, edition_name: str) -> str:
    """OBH + "108" -> "OBH108"; OBH Web + "Jan 2027" -> "OBH Web Jan 2027"."""
    name = str(edition_name or "").strip()
    if not code:
        return f"Issue {name}" if name.isdigit() else name
    return f"{code}{name}" if name.isdigit() and " " not in code else f"{code} {name}"
