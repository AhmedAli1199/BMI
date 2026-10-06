"""Writes the wording of a proposal. The model only writes sentences - every
price, date and figure comes from the rate card and order register. If its
text contains a figure that isn't in that source data, we throw the AI text
away and use the standard wording instead.
"""
from __future__ import annotations

import re
import uuid

from app.proposals.context import gbp

_NUMBER = re.compile(r"£\s?[\d,]+(?:\.\d+)?|\d+(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?")

DEFAULT_HEADINGS = {
    "intro": "Introduction",
    "history": "Your history with us",
    "proposal": "What we propose",
    "investment": "Investment",
    "next_steps": "Next steps",
}
SECTION_ORDER = ["intro", "history", "proposal", "investment", "next_steps"]


def numbers_in(text: str) -> set[str]:
    out = set()
    for m in _NUMBER.findall(text or ""):
        n = re.sub(r"[£\s,%]", "", m)
        out.add(n[:-2] if n.endswith(".0") else n)
        out.add(n)
    return out


def facts_text(ctx: dict, lines: list[dict], campaign_name: str) -> str:
    """Everything the model is allowed to quote, as one string."""
    parts = [campaign_name, str(ctx.get("year", ""))]
    h = ctx.get("history") or {}
    parts += [str(h.get("count", "")), gbp(h.get("total_gbp", 0)), str(h.get("total_gbp", ""))]
    for y, v in (h.get("by_year") or {}).items():
        parts += [y, gbp(v), str(v)]
    for b in h.get("bookings") or []:
        parts += [str(b["year"]), str(b["edition"]), gbp(b["value_gbp"]), str(b["value_gbp"]), b.get("size") or "", b.get("booked_on") or ""]
    for r in ctx.get("rates") or []:
        parts += [r["product"], gbp(r["price_gbp"]), str(r["price_gbp"])]
    for ln in lines:
        parts += [str(ln["qty"]), gbp(ln["unit_price"]), str(ln["unit_price"]), ln["product"]]
    return " ".join(parts)


def guard(text: str, allowed: set[str]) -> bool:
    """True when every figure in the text is in the source data."""
    return numbers_in(text) <= allowed


def template_wording(ctx: dict, lines: list[dict], campaign_name: str) -> dict[str, str]:
    h = ctx.get("history") or {}
    title = ctx.get("title") or "our titles"
    if h.get("count"):
        years = sorted((h.get("by_year") or {}).keys())
        span = f"since {years[0]}" if years else "over the years"
        history = (f"We have worked together {span}, with {h['count']} booking{'s' if h['count'] != 1 else ''} "
                   f"worth {gbp(h['total_gbp'])} in total (before VAT).")
    else:
        history = "We haven't worked together before, and we would love the chance to start."
    products = ", ".join(ln["product"] for ln in lines) or "a package tailored to your goals"
    return {
        "intro": f"Thank you for your time. We'd like to set out how {title} can help {ctx.get('company', 'your business')} reach the right audience.",
        "history": history,
        "proposal": f"We propose the following for {campaign_name}: {products}.",
        "next_steps": "- Let us know which of these options suits you\n- We'll confirm availability and send the booking form\n- We'll agree copy and artwork deadlines",
    }


SYSTEM = (
    "You write the wording of a sales proposal for BMI Publishing, a UK travel and hospitality publisher. "
    "Write in plain, warm, professional British English. Never invent prices, dates, figures, circulation, "
    "audience numbers or claims. Only use figures from the FACTS given. If something isn't in the facts, leave it out. "
    "Return JSON with exactly these string keys: intro, history, proposal, next_steps. "
    "Keep each to 1-4 short sentences; next_steps may be 2-4 lines each starting with '- '."
)


def draft_sections(ctx: dict, lines: list[dict], campaign_name: str, *, use_ai: bool = True) -> tuple[dict[str, str], str]:
    """(wording by section kind, 'ai'|'template')."""
    fallback = template_wording(ctx, lines, campaign_name)
    if not use_ai:
        return fallback, "template"
    from app.automations import llm
    if not llm.is_configured():
        return fallback, "template"
    facts = facts_text(ctx, lines, campaign_name)
    user = (f"Client: {ctx.get('company')}\nCampaign: {campaign_name}\nTitle: {ctx.get('title')}\n"
            f"Booking history: {ctx.get('history')}\nProducts proposed: {lines}\n\nFACTS (the only figures you may use): {facts}")
    out = llm.extract_json(SYSTEM, user, max_tokens=700, purpose="proposal_draft")
    if not isinstance(out, dict):
        return fallback, "template"
    allowed = numbers_in(facts)
    result = dict(fallback)
    used = False
    for k in ("intro", "history", "proposal", "next_steps"):
        text = out.get(k)
        if isinstance(text, str) and text.strip() and guard(text, allowed):
            result[k] = text.strip()
            used = True
    return result, "ai" if used else "template"


def default_sections(wording: dict[str, str]) -> list[dict]:
    secs = []
    for kind in SECTION_ORDER:
        body = "All prices are before VAT." if kind == "investment" else wording.get(kind, "")
        secs.append({"id": str(uuid.uuid4()), "kind": kind, "heading": DEFAULT_HEADINGS[kind], "body": body})
    return secs
