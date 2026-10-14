"""How each salesperson writes ("Teach the Brain how you write") - parts 3 and 4 of the proposal plan (14 Oct 2026).

One structure for everyone, filled in per person:
  - situations: the kinds of proposal they write (agency brief, PR pitch, general enquiry, referral, after a call or
    event, existing client, full proposal), each with what goes in it, in their order, and how they open and close;
  - tone and length, greeting and sign-off, email or Word document, tables or not;
  - things they always or never do ("I never put prices in the first email");
  - prices: agencies at the rate card (they take their commission from it), direct clients at the rate card or at
    the person's own "introductory" level, as a % off.
The AI drafts it from their past proposals (uploaded, pasted, or found in their Outlook Sent Items) and a note in
their own words; they correct it and save it. Without AI, everyone starts from the standard profile below.

Learning (part 4): each time a drafted reply or proposal is sent, what was taken out is compared with what was
drafted. Something taken out in 3 of the last 6 is left out from then on, and a sign-off they keep typing replaces
the profile's. Each of these shows on their profile page with a switch to undo it.

Figures never come from here: prices, issues and numbers always come from the rate card, editorial plan and
brand facts. The profile only decides what to include, in what order and in what voice.
"""
from __future__ import annotations

import copy
import io
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, WritingProfile

logger = logging.getLogger("app.proposals.style")

ITEMS = {
    "free_options": "Free ways to work with us",
    "stats": "Audience numbers",
    "prices": "Prices",
    "issues": "Coming issues",
    "examples": "Examples of our work",
    "events": "Events and awards",
    "media_pack": "Media pack link",
    "call_offer": "Offer a call",
}
SITUATIONS = {
    "agency_brief": "Agency brief", "pr_pitch": "PR pitch", "general": "General enquiry", "referral": "Referral",
    "follow_up": "After a call or event", "existing_client": "Existing client", "full_proposal": "Full proposal",
}
# The bold headings a drafted reply uses for each item - also how an edit is spotted.
HEADINGS = {"free_options": "Free ways to work with us", "stats": "Key statistics", "prices": "Prices (before VAT)",
            "issues": "Coming issues", "examples": "Examples of our work", "events": "Events and awards"}

DEFAULT_PROFILE: dict = {
    "summary": "The standard BMI style: friendly and professional, prices and the next issues first, then an offer to talk it through.",
    "tone": "Friendly and professional, British English, warm but to the point.",
    "length": "medium",
    "greeting": "Hi {first_name},",
    "sign_off": "Kind regards,\n{my_first_name}",
    "output": "email",
    "uses_tables": True,
    "always": [],
    "never": [],
    "prices": {"agency": "rate_card", "direct_discount_pct": 0.0, "round_to": 50},
    "situations": {
        "agency_brief": {"include": ["prices", "examples", "stats", "issues", "events", "media_pack", "call_offer"],
                         "opening": "Thank you for the brief{for_client}. Below are the options that fit what you're looking for, with prices.",
                         "closing": "I'll happily shape these into a package that fits your budget and timings. Would a quick Teams call help to talk it through?"},
        "pr_pitch": {"include": ["prices", "issues", "media_pack", "call_offer"],
                     "opening": "Thank you for getting in touch{for_client}. Pieces like this run with us as sponsored content, so here are the options and prices.",
                     "closing": "Let me know if you'd like to go ahead, or if a quick call would help."},
        "general": {"include": ["prices", "examples", "stats", "media_pack", "call_offer"],
                    "opening": "Thank you for your email - it would be great to work with you{for_client}. Here's an overview of what we offer, with prices.",
                    "closing": "If you let me know your budget and timings, I'll put together a package that fits. Would a quick Teams call help?"},
        "referral": {"include": ["free_options", "stats", "prices", "examples", "call_offer"],
                     "opening": "Lovely to be introduced. Here's a quick overview of how we could work together{for_client}.",
                     "closing": "Once you've had a look, shall we get a Teams call in the diary to talk through your objectives?"},
        "follow_up": {"include": ["free_options", "stats", "prices", "examples", "events", "call_offer"],
                      "opening": "Great to speak with you. As promised, here's an overview of the options{for_client}.",
                      "closing": "Let me know what you think, and I'll shape it into a package."},
        "existing_client": {"include": ["prices", "issues", "call_offer"],
                            "opening": "Thank you for coming back to us. Here are the current options and prices{for_client}.",
                            "closing": "Let me know what you'd like to book and I'll send the confirmation."},
        "full_proposal": {"include": ["stats", "prices", "examples", "issues", "events"], "opening": "", "closing": ""},
    },
}

MAX_SAMPLE_CHARS = 20000
MAX_SAMPLES = 12


def normalise(raw: dict | None) -> dict:
    """A complete, safe profile: anything missing comes from the standard one; anything odd is dropped."""
    out = copy.deepcopy(DEFAULT_PROFILE)
    raw = raw if isinstance(raw, dict) else {}
    for k in ("summary", "tone", "greeting", "sign_off"):
        if isinstance(raw.get(k), str) and raw[k].strip():
            out[k] = raw[k].strip()[:600]
    if raw.get("length") in ("short", "medium", "long"):
        out["length"] = raw["length"]
    if raw.get("output") in ("email", "word"):
        out["output"] = raw["output"]
    if isinstance(raw.get("uses_tables"), bool):
        out["uses_tables"] = raw["uses_tables"]
    for k in ("always", "never"):
        if isinstance(raw.get(k), list):
            out[k] = [str(x).strip()[:200] for x in raw[k] if str(x).strip()][:12]
    pr = raw.get("prices") if isinstance(raw.get("prices"), dict) else {}
    try:
        out["prices"]["direct_discount_pct"] = min(max(float(pr.get("direct_discount_pct") or 0), 0.0), 0.5)
    except (TypeError, ValueError):
        pass
    if pr.get("round_to") in (1, 5, 10, 25, 50, 100):
        out["prices"]["round_to"] = pr["round_to"]
    sits = raw.get("situations") if isinstance(raw.get("situations"), dict) else {}
    for key, s in sits.items():
        if key not in SITUATIONS or not isinstance(s, dict):
            continue
        cur = out["situations"].setdefault(key, {"include": [], "opening": "", "closing": ""})
        if isinstance(s.get("include"), list):
            cur["include"] = [i for i in dict.fromkeys(s["include"]) if i in ITEMS]
        for k in ("opening", "closing"):
            if isinstance(s.get(k), str):
                cur[k] = s[k].strip()[:800]
    return out


def get(db: Session, user_id) -> WritingProfile | None:
    return db.scalars(select(WritingProfile).where(WritingProfile.user_id == user_id)).first() if user_id else None


def get_or_create(db: Session, user_id) -> WritingProfile:
    wp = get(db, user_id)
    if not wp:
        wp = WritingProfile(id=uuid.uuid4(), user_id=user_id, samples=[], profile={}, status="draft", learned=[], edits=[])
        db.add(wp)
        db.flush()
    return wp


def effective(db: Session, user_id) -> dict:
    """The profile drafts actually use: theirs once saved (else the standard one), with what's been learned applied."""
    wp = get(db, user_id)
    prof = normalise(wp.profile if wp and wp.status == "ready" else None)
    prof["_personal"] = bool(wp and wp.status == "ready")
    for item in (wp.learned if wp else []) or []:
        if not item.get("active"):
            continue
        key = item.get("key", "")
        if key.startswith("omit:"):
            what = key.split(":", 1)[1]
            for s in prof["situations"].values():
                s["include"] = [i for i in s["include"] if i != what]
        elif key == "sign_off" and item.get("value"):
            prof["sign_off"] = item["value"]
    return prof


def situation(prof: dict, key: str | None) -> dict:
    return prof["situations"].get(key or "general") or prof["situations"]["general"]


def sign_off(prof: dict, user: User | None) -> str:
    first = ((user.name if user else "") or "").split(" ")[0]
    return prof["sign_off"].replace("{my_first_name}", first).replace("{my_name}", (user.name if user else "") or "")


def direct_price(prof: dict, price: float) -> float:
    """A direct client's price at the person's introductory level, rounded the way they quote."""
    pct = float(prof["prices"].get("direct_discount_pct") or 0)
    if not pct:
        return price
    step = prof["prices"].get("round_to") or 50
    return max(step, round(price * (1 - pct) / step) * step)


# ---- learning from past proposals --------------------------------------------------------------------

def read_file(name: str, data: bytes) -> str:
    """Text from a Word document, PDF, email or text file (tables included)."""
    low = (name or "").lower()
    if low.endswith(".docx") or data[:2] == b"PK":
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs if p.text.strip()]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return "\n".join(parts)
    if low.endswith(".pdf") or data[:4] == b"%PDF":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages[:20])
    text = data.decode("utf-8", errors="ignore")
    if "<html" in text.lower() or "<p" in text.lower():
        from app.services.mail_merge import to_text
        text = to_text(text)
    return text


def add_sample(wp: WritingProfile, name: str, text: str, source: str) -> dict:
    text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())[:MAX_SAMPLE_CHARS]
    if len(text) < 80:
        raise ValueError("That doesn't have enough text in it to learn from. Try a longer proposal.")
    if len(wp.samples or []) >= MAX_SAMPLES:
        raise ValueError(f"That's {MAX_SAMPLES} already, which is plenty. Remove one to add another.")
    s = {"id": uuid.uuid4().hex[:12], "name": (name or "Proposal").strip()[:120], "source": source, "text": text,
         "added_at": datetime.now(timezone.utc).isoformat()}
    wp.samples = [*(wp.samples or []), s]
    return s


SENT_SEARCH = "proposal OR rates OR media pack OR sponsored OR advertising OR package"


def find_in_sent(mailbox: str, limit: int = 8) -> list[dict]:
    """Past proposals from someone's Outlook Sent Items: emails that read like proposals (prices, packages, media pack)
    and are long enough to learn from."""
    from app.automations.proposal_requests import keyword_hits
    from app.graph_client import list_sent_messages

    found = []
    for m in list_sent_messages(mailbox, SENT_SEARCH, top=40):
        body = ((m.get("body") or {}).get("content") or "").strip()
        body = body.split("\nFrom:")[0].split("\n-----Original Message")[0].strip()   # drop the quoted email below
        if len(body) < 400 or keyword_hits(body) < 2 or "£" not in body:
            continue
        found.append({"name": (m.get("subject") or "Sent proposal")[:120], "text": body[:MAX_SAMPLE_CHARS], "score": keyword_hits(body) + len(body) / 4000})
    found.sort(key=lambda x: -x["score"])
    return found[:limit]


_BUILD_PROMPT = (
    "You study how one magazine salesperson at BMI Publishing writes proposals and replies to enquiries, from examples "
    "of their real emails and documents and a note in their own words. Describe their way of working so a system can "
    "draft in the same style. The kinds of proposal (situations) are: "
    + ", ".join(f"{k} ({v})" for k, v in SITUATIONS.items())
    + ". The parts a proposal can include are: " + ", ".join(f"{k} ({v})" for k, v in ITEMS.items())
    + ". Return JSON: {\"summary\": two or three plain sentences describing how they write, \"tone\": a few words, "
    "\"length\": short|medium|long, \"greeting\": how they greet, with {first_name} for the client's name, "
    "\"sign_off\": how they sign off, with {my_first_name} for their own name and \\n for a new line, "
    "\"output\": email|word (how they usually send proposals), \"uses_tables\": bool, \"always\": [things they always do], "
    "\"never\": [things they never do], \"prices\": {\"direct_discount_pct\": the usual % below the rate card they offer "
    "direct clients as a fraction (0 if they quote the rate card, null if you can't tell)}, \"situations\": {situation key: "
    "{\"include\": [part keys in the order they use them], \"opening\": their usual opening sentence for it, with {for_client} "
    "where they name the client, \"closing\": their usual closing}}}. Only include situations the examples or note show. "
    "Never copy prices, figures, dates or client names into the openings and closings - keep them general."
)


def build(db: Session, wp: WritingProfile, user: User | None) -> str:
    """Drafts the profile from the samples and note. Returns "ai" or "standard"."""
    from app.automations import llm

    if not llm.is_configured() or not (wp.samples or wp.notes):
        wp.profile, wp.built_by = normalise(wp.profile or None), "standard"
        wp.built_at = datetime.now(timezone.utc)
        return "standard"
    budget, chunks = 40000, []
    for s in wp.samples or []:
        piece = f"--- EXAMPLE: {s['name']} ---\n{s['text'][:9000]}"
        if budget - len(piece) < 0:
            break
        chunks.append(piece)
        budget -= len(piece)
    user_prompt = (f"Salesperson: {user.name if user else ''}\n\nTHEIR NOTE ABOUT HOW THEY WORK:\n{wp.notes or '(none)'}\n\n"
                   + "\n\n".join(chunks))
    out = llm.extract_json(_BUILD_PROMPT, user_prompt, max_tokens=2500, purpose="proposal_style.build")
    if not isinstance(out, dict):
        wp.profile, wp.built_by = normalise(wp.profile or None), "standard"
        wp.built_at = datetime.now(timezone.utc)
        return "standard"
    from app.proposals.drafting import numbers_in
    # Openings and closings must not carry figures from someone else's deal.
    for s in (out.get("situations") or {}).values():
        if isinstance(s, dict):
            for k in ("opening", "closing"):
                if isinstance(s.get(k), str) and numbers_in(s[k]):
                    s[k] = ""
    prof = normalise(out)
    if (out.get("prices") or {}).get("direct_discount_pct") is None:
        prof["prices"]["direct_discount_pct"] = 0.0
    # Keep the standard wording for any situation the AI left without an opening or closing.
    for key, s in prof["situations"].items():
        for k in ("opening", "closing"):
            if not s.get(k) and key != "full_proposal":
                s[k] = DEFAULT_PROFILE["situations"].get(key, {}).get(k, "")
    wp.profile, wp.built_by, wp.built_at = prof, "ai", datetime.now(timezone.utc)
    return "ai"


# ---- learning from edits (part 4) --------------------------------------------------------------------

def _items_in(text: str) -> set[str]:
    found = set()
    low = (text or "").lower()
    for key, heading in HEADINGS.items():
        h = heading.lower().replace(" (before vat)", "")
        if f"**{h}" in low or (key == "prices" and re.search(r"\*\*[^*\n]*prices", low)):
            found.add(key)
    if "media pack" in low:
        found.add("media_pack")
    return found


def _last_lines(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").strip().split("\n") if ln.strip()]
    return "\n".join(lines[-2:]) if len(lines) >= 2 else ""


def record_edit(db: Session, user_id, *, kind: str, situation: str | None, drafted: str | None = None, sent: str | None = None,
                removed: list[str] | None = None) -> None:
    """Remembers what was taken out of a draft before it was sent, then updates what's been learned."""
    if not user_id:
        return
    wp = get_or_create(db, user_id)
    gone = sorted(set(removed or []) | (_items_in(drafted or "") - _items_in(sent or "")))
    entry = {"at": datetime.now(timezone.utc).isoformat(), "kind": kind, "situation": situation, "removed": gone,
             "sign_off": _last_lines(sent or "") if kind == "reply" else ""}
    wp.edits = [*(wp.edits or []), entry][-30:]
    learn(wp)


def learn(wp: WritingProfile) -> None:
    recent = (wp.edits or [])[-6:]
    learned = {x["key"]: x for x in (wp.learned or [])}
    now = datetime.now(timezone.utc).isoformat()
    for item in ITEMS:
        n = sum(1 for e in recent if item in (e.get("removed") or []))
        key = f"omit:{item}"
        if n >= 3 and key not in learned:
            learned[key] = {"key": key, "active": True, "at": now,
                            "text": f"You usually take out “{ITEMS[item]}”, so new drafts leave it out."}
    signs = [e.get("sign_off") for e in recent if e.get("kind") == "reply" and e.get("sign_off")]
    if len(signs) >= 3:
        common = max(set(signs), key=signs.count)
        if signs.count(common) >= 3 and (learned.get("sign_off") or {}).get("value") != common:
            learned["sign_off"] = {"key": "sign_off", "active": True, "at": now, "value": common,
                                   "text": f"You sign off as “{common.replace(chr(10), ' / ')}”, so drafts do too."}
    wp.learned = list(learned.values())
