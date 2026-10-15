"""What the Brain knows about using BMI Brain: the help guides and the screen map.

Guides are Markdown files in app/brain/help/<area>/<slug>.md, one per screen (or group of screens), with a
small header:

    ---
    title: Booking page
    screens: ["/sales/deals/[id]"]
    summary: One sentence for the catalogue.
    sources: ["frontend/src/..."]        # the code the guide describes (for keeping it current)
    ---

The screen map (help/ui_map.json) is built from the frontend code by frontend/scripts/build-help-map.mjs:
every screen's buttons, links and hints with the file and line they come from. It lets the Brain match what
someone clicked to the right guide, and only "Show me" things that really exist.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

HELP_DIR = Path(__file__).parent / "help"
WORD = re.compile(r"[a-z0-9]+")
STOP = {"the", "a", "an", "to", "of", "and", "or", "is", "it", "in", "on", "for", "how", "do", "i", "my", "what", "why", "can",
        "this", "that", "with", "be", "does", "you", "your", "when", "where", "which", "are", "if", "me", "not", "t"}


@dataclass
class Section:
    heading: str
    level: int
    text: str


@dataclass
class Guide:
    id: str                    # "sales-orders/booking-page"
    area: str
    title: str
    summary: str
    screens: list[str]
    sources: list[str]
    body: str
    sections: list[Section] = field(default_factory=list)


def _front(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    head, _, body = raw[3:].partition("\n---")
    meta: dict = {}
    for line in head.strip().splitlines():
        key, _, value = line.partition(":")
        value = value.split(" #", 1)[0].strip() if value.strip().startswith("[") else value.strip()
        try:
            meta[key.strip()] = json.loads(value) if value.startswith("[") else value
        except json.JSONDecodeError:
            meta[key.strip()] = value
    return meta, body.lstrip("\n")


def _sections(body: str) -> list[Section]:
    out: list[Section] = []
    cur: Section | None = None
    for line in body.splitlines():
        m = re.match(r"^(#{2,3})\s+(.*)$", line)
        if m:
            cur = Section(heading=m.group(2).strip(), level=len(m.group(1)), text="")
            out.append(cur)
        elif cur:
            cur.text += line + "\n"
    return out


@lru_cache(maxsize=1)
def guides() -> tuple[Guide, ...]:
    out = []
    for path in sorted(HELP_DIR.glob("*/*.md")):
        meta, body = _front(path.read_text(encoding="utf-8"))
        area = path.parent.name
        out.append(Guide(id=f"{area}/{path.stem}", area=area, title=meta.get("title") or path.stem.replace("-", " ").title(),
                         summary=meta.get("summary") or "", screens=list(meta.get("screens") or []),
                         sources=list(meta.get("sources") or []), body=body.strip(), sections=_sections(body)))
    return tuple(out)


def guide(guide_id: str) -> Guide | None:
    gid = guide_id.strip().strip("/").lower()
    return next((g for g in guides() if g.id == gid or g.id.split("/")[-1] == gid), None)


def _pattern(screen: str) -> re.Pattern:
    parts = [r"[^/]+" if p.startswith("[") else re.escape(p) for p in screen.strip("/").split("/")]
    return re.compile("^/" + "/".join(parts) + "/?$")


def guides_for_path(path: str | None) -> list[Guide]:
    """The guides that explain the page at `path` (most specific screen first)."""
    if not path:
        return []
    path = path.split("?")[0].split("#")[0]
    hits = []
    for g in guides():
        for s in g.screens:
            if _pattern(s).match(path):
                hits.append((s.count("/") * 10 - s.count("["), g))
    return [g for _, g in sorted(hits, key=lambda h: -h[0])]


def _terms(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 1}


def search(query: str, limit: int = 4) -> list[tuple[Guide, Section]]:
    """Plain keyword search over guide sections (headings count double)."""
    want = _terms(query)
    if not want:
        return []
    scored = []
    for g in guides():
        for s in g.sections:
            head, words = _terms(s.heading), _terms(s.text)
            score = 2 * len(want & head) + len(want & words)
            if score:
                scored.append((score, g, s))
    scored.sort(key=lambda x: -x[0])
    return [(g, s) for _, g, s in scored[:limit]]


# ---- the screen map ---------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def ui_map() -> dict:
    p = HELP_DIR / "ui_map.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"elements": []}


def elements_for_path(path: str | None) -> list[dict]:
    """Buttons, links and hints that can appear on that page (from its screen files)."""
    if not path:
        return []
    files = set()
    for screen in ui_map().get("screens", []):
        if _pattern(screen["route"]).match(path.split("?")[0]):
            files.update(screen.get("files", []))
    return [e for e in ui_map().get("elements", []) if e.get("file") in files]


def labels_for_path(path: str | None) -> set[str]:
    return {e["label"].strip().lower() for e in elements_for_path(path) if e.get("label")}


def element_by_src(src: str | None) -> dict | None:
    if not src:
        return None
    return next((e for e in ui_map().get("elements", []) if e.get("src") == src), None)


def reload() -> None:
    guides.cache_clear()
    ui_map.cache_clear()
