"""Writes the wording of a proposal. The model only writes sentences - every
price, date and figure comes from the rate card and order register. If its
text contains a figure that isn't in that source data, we throw the AI text
away and use the standard wording instead.
"""
from __future__ import annotations

import re
import uuid

from app.proposals.context import gbp
from app.sales.editorial import issue_sentence

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
        parts += [str(ln["qty"]), gbp(ln["unit_price"]), str(ln["unit_price"]), str(abs(ln["unit_price"])), ln["product"],
                  *(ln.get("issue_labels") or []), ln.get("option") or ""]
        if ln.get("discount_pct"):
            from app.proposals.pricing import line_total
            parts += [f"{float(ln['discount_pct']) * 100:g}%", gbp(line_total(ln)), str(line_total(ln))]
    for t in ctx.get("totals") or []:
        parts += [t.get("option") or "", gbp(t["total_gbp"]), str(t["total_gbp"]), gbp(t["subtotal_gbp"]), gbp(t["discount_gbp"])]
    if ctx.get("discount_pct"):
        parts.append(f"{float(ctx['discount_pct']) * 100:g}%")
    for f in ctx.get("issues") or []:
        parts += [f.get("label") or "", f.get("name") or "", f.get("publication_text") or "", f.get("ad_deadline_text") or "",
                  f.get("theme") or "", *(f.get("features") or [])]
    issue = ctx.get("issue") or {}
    if issue:
        parts += [issue.get("label") or "", issue.get("name") or "", issue.get("publication_text") or "", issue.get("ad_deadline_text") or "",
                  issue.get("publication") or "", issue.get("ad_deadline") or "", issue.get("theme") or "", issue.get("distribution") or "",
                  issue.get("period") or "", *(issue.get("features") or [])]
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
    names = list(dict.fromkeys(ln["product"] for ln in lines if ln.get("source") != "offer"))
    products = _join(names) if names else "a package tailored to your goals"
    offers = [ln["product"].removeprefix("Offer: ") for ln in lines if ln.get("source") == "offer"]
    proposal = f"We propose the following for {campaign_name}: {products}."
    next_steps = "- Let us know which of these options suits you\n- We'll confirm availability and send the booking form\n- We'll agree copy and artwork deadlines"
    issues = ctx.get("issues") or []
    issue = ctx.get("issue") if len(issues) <= 1 else None
    kind = ctx.get("kind") or "issue"
    titles = ctx.get("titles") or []
    if len(titles) > 1:
        proposal = f"We propose a package across {_join(titles)} for {campaign_name}: {products}."
    if kind == "annual":
        proposal = f"We propose a year-round programme for {campaign_name}, keeping {ctx.get('company', 'you')} in front of readers in every issue: {products}."
    elif kind == "digital":
        proposal = f"We propose a digital campaign for {campaign_name} across our website, newsletters and social channels: {products}."
    elif kind == "sponsorship":
        proposal = f"We propose a sponsorship for {campaign_name}, putting {ctx.get('company', 'your brand')} at the heart of the event: {products}."
    if offers:
        proposal += f" This includes our offer: {'; '.join(offers)}."
    if len(issues) > 1:
        proposal += " It runs in " + _join([f"{f['label']}" + (f" ({f['publication_text']})" if f.get("publication_text") else "") for f in issues]) + "."
        feats = list(dict.fromkeys(x for f in issues for x in (f.get("sponsorable") or f.get("features") or [])))
        if feats:
            proposal += f" Features planned across these issues include {_join(feats[:5])}."
    tots = ctx.get("totals") or []
    if len(tots) > 1:
        proposal += " We've set out " + ("two options" if len(tots) == 2 else f"{len(tots)} options") + " below, so you can choose what suits you best."
    if issue:
        proposal = f"{issue_sentence(issue)} {proposal}"
        feats = issue.get("sponsorable") or issue.get("features") or []
        if feats:
            proposal += f" Features planned for this issue include {_join(feats[:4])}."
        if issue.get("ad_deadline_text"):
            next_steps = (f"- Let us know which of these options suits you\n- We'll confirm your space and send the booking form\n"
                          f"- Copy and artwork are needed by {issue['ad_deadline_text']}")
    return {
        "intro": f"Thank you for your time. We'd like to set out how {title} can help {ctx.get('company', 'your business')} reach the right audience.",
        "history": history,
        "proposal": proposal,
        "next_steps": next_steps,
    }


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


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
            f"Booking history: {ctx.get('history')}\nProducts proposed: {lines}\n"
            f"Issue it's for (from the editorial plan - mention its date, theme and relevant features if given): {ctx.get('issue')}\n"
            f"Kind of proposal: {ctx.get('kind_label') or 'A single issue'}\nAll issues it runs in: {ctx.get('issues') or 'just the one above'}\n"
            f"Titles: {ctx.get('titles')}\nOptions and totals (if more than one, the client chooses one): {ctx.get('totals')}\n\nFACTS (the only figures you may use): {facts}")
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


REVISE_SYSTEM = (
    "You revise a sales proposal for BMI Publishing, a UK travel and hospitality publisher, following the salesperson's instruction. "
    "You may change anything the instruction asks for: headings, wording, tone, length, order of sections, add or remove sections. "
    "Write plain, warm, professional British English. Never invent prices, dates, figures, circulation, audience numbers or claims: "
    "only use figures that appear in the FACTS, the current proposal, or the instruction. Keep exactly one section with kind 'investment' "
    "(its price table is added automatically - its body is a short note under the table). Use **double asterisks** for bold and start a "
    "line with '- ' for a bullet. Return JSON: {\"sections\": [{\"kind\": \"intro|history|proposal|investment|next_steps|custom\", "
    "\"heading\": \"...\", \"body\": \"...\"}], \"summary\": \"one short sentence saying what you changed\"}."
)

MAX_SECTIONS = 14


class RevisionRefused(Exception):
    """A plain sentence for the salesperson saying why nothing was changed."""


def revise_sections(ctx: dict, lines: list[dict], campaign_name: str, sections: list[dict], instruction: str) -> tuple[list[dict], str]:
    """(new sections, what changed). Raises RevisionRefused with a plain reason when it can't be done safely."""
    from app.automations import llm
    if not llm.is_configured():
        raise RevisionRefused("The AI isn't switched on for this account, so changes can't be made from an instruction. Edit the sections directly instead.")
    facts = facts_text(ctx, lines, campaign_name)
    current = "\n\n".join(f"[{s.get('kind', 'custom')}] {s.get('heading', '')}\n{s.get('body', '')}" for s in sections)
    user = (f"INSTRUCTION FROM THE SALESPERSON:\n{instruction}\n\nCURRENT PROPOSAL (kind in brackets, then heading, then text):\n{current}\n\n"
            f"Client: {ctx.get('company')}\nTitle: {ctx.get('title')}\nIssue: {ctx.get('issue')}\nProducts and prices: {lines}\n\n"
            f"FACTS (the only figures you may add): {facts}")
    out = llm.extract_json(REVISE_SYSTEM, user, max_tokens=3000, purpose="proposal_revise")
    raw = out.get("sections") if isinstance(out, dict) else None
    if not isinstance(raw, list) or not raw:
        raise RevisionRefused("The AI didn't come back with a usable version. Try again, or say what to change in a different way.")
    allowed = numbers_in(facts) | numbers_in(current) | numbers_in(instruction)
    new: list[dict] = []
    for s in raw[:MAX_SECTIONS]:
        if not isinstance(s, dict):
            continue
        heading, body = str(s.get("heading") or "").strip()[:200], str(s.get("body") or "").strip()
        kind = s.get("kind") if s.get("kind") in (*SECTION_ORDER, "custom") else "custom"
        if not heading and not body:
            continue
        bad = numbers_in(f"{heading} {body}") - allowed
        if bad:
            raise RevisionRefused(f"The new version mentioned figures we can't check against the rate card or booking history "
                                  f"({', '.join(sorted(bad)[:4])}), so nothing was changed. Put the figure in your instruction if it's right.")
        new.append({"id": str(uuid.uuid4()), "kind": kind, "heading": heading, "body": body})
    if not new:
        raise RevisionRefused("The AI didn't come back with a usable version. Try again, or say what to change in a different way.")
    inv = [s for s in new if s["kind"] == "investment"]
    if not inv:  # the price table hangs off the investment section, so it can't disappear
        old = next((s for s in sections if s.get("kind") == "investment"), None)
        new.append({"id": str(uuid.uuid4()), "kind": "investment", "heading": (old or {}).get("heading") or DEFAULT_HEADINGS["investment"],
                    "body": (old or {}).get("body") or "All prices are before VAT."})
    for extra in inv[1:]:
        extra["kind"] = "custom"
    summary = str(out.get("summary") or "").strip()[:300] or "Proposal updated."
    if numbers_in(summary) - allowed:
        summary = "Proposal updated."
    return new, summary
