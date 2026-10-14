"""How a piece of feedback reads as text: for the download (Markdown) and for its GitHub issue."""
from __future__ import annotations

from app.core.config import settings
from app.models import Feedback

KIND_LABEL = {"broken": "Something's broken", "confusing": "I don't understand this", "idea": "I wish it could...",
              "looks_wrong": "Looks wrong"}
STATUS_LABEL = {"new": "New", "looking": "Looking at it", "fixed": "Fixed", "wont_do": "Won't do"}


def title(f: Feedback) -> str:
    first = " ".join((f.message or "").split())[:80]
    if not first and f.elements:
        first = f"About {f.elements[0].get('label') or 'something on the page'}"
    return f"[Feedback #{f.number}] {KIND_LABEL.get(f.kind, f.kind)}: {first or f.page_path}"


def element_lines(f: Feedback) -> list[str]:
    out = []
    for i, e in enumerate(f.elements or [], 1):
        bits = [f"**{e.get('label') or 'Something on the page'}**"]
        if e.get("heading"):
            bits.append(f"under “{e['heading']}”")
        out.append(f"{i}. " + " ".join(bits))
        if e.get("source"):
            out.append(f"   - Code: `{'` → `'.join(e['source'][:4])}`")
        if e.get("selector"):
            out.append(f"   - Selector: `{e['selector']}`")
        if e.get("text") and e.get("text") != e.get("label"):
            out.append(f"   - Text: {e['text'][:200]}")
    return out


def markdown(f: Feedback, image_links: list[tuple[str, str]], app_url: str | None = None) -> str:
    """image_links: (label, url) for each screenshot."""
    base = (app_url or settings.app_base_url).rstrip("/")
    ctx = f.context or {}
    lines = [
        f"**{KIND_LABEL.get(f.kind, f.kind)}** · from {f.user_name or 'someone'}{f' ({f.user_role})' if f.user_role else ''} · "
        f"{f.created_at:%d %b %Y %H:%M} · status: {STATUS_LABEL.get(f.status, f.status)}",
        "",
        f"**Page:** [{f.page_title or f.page_path}]({base}{f.page_path})  `{f.page_path}`",
        "",
        "### What they said",
        (f.message or "_(no words, see what they pointed at)_").strip(),
    ]
    els = element_lines(f)
    if els:
        lines += ["", "### What they pointed at", *els]
    if image_links:
        lines += ["", "### Screenshots"] + [f"![{label}]({url})" for label, url in image_links]
    errs = ctx.get("errors") or []
    if errs:
        lines += ["", "### Errors on the page just before", *[f"- {e.get('at', '')} {e.get('kind', '')}: `{str(e.get('message', ''))[:300]}`" for e in errs[-10:]]]
    tech = [f"{k}: {ctx[k]}" for k in ("browser", "viewport", "screen", "zoom", "theme", "time_zone", "app_version") if ctx.get(k)]
    if tech:
        lines += ["", "<details><summary>Browser and screen</summary>", "", *[f"- {t}" for t in tech], "", "</details>"]
    if f.me_too:
        lines += ["", f"**Me too:** {', '.join(m.get('name') or 'someone' for m in f.me_too)}"]
    if f.comments:
        lines += ["", "### Comments", *[f"- **{c.get('name')}** ({str(c.get('at', ''))[:16].replace('T', ' ')}): {c.get('text')}" for c in f.comments]]
    if f.status_note:
        lines += ["", f"**Note on status:** {f.status_note}"]
    lines += ["", f"[Open in BMI Brain]({base}/feedback?open={f.id})"]
    return "\n".join(lines)
