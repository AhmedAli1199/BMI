"""One turn of a conversation: the question (with what's on screen) in; live steps, streamed words and the
final answer out; the trace saved.

Keeping it fast and cheap:
- History is replayed as plain text only - earlier questions exactly as the model first saw them, and the
  answers - never the old tool results (they're dropped once answered, the simplest form of compaction).
  So each request is the previous one plus a bit at the end, which keeps the prompt cache warm.
- What changes (today's date, who's asking, the page, what was pointed at) goes in a <context> block at the
  END of the question, never in the fixed instructions.
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import AsyncIterator

from app.brain import agent, knowledge, registry
from app.core.identity import Identity
from app.roles import ROLE_DEFS

ROLE_LABELS = {r.value: r.label for r in ROLE_DEFS}

log = logging.getLogger("app.brain")

SHOW = re.compile(r"\[\[show:([^\]]+)\]\]")
ASK = re.compile(r"\[\[ask:([^\]]+)\]\]")
LINK = re.compile(r"\[([^\]]+)\]\((/[^)\s]+)\)")
NOT_ON = "The assistant isn't switched on yet. An administrator needs to add the Gemini key."
FAILED = "Sorry - I couldn't answer that just now. Please try again in a minute."


@dataclass
class Asked:
    question: str
    context: dict = field(default_factory=dict)          # page_path, page_title, record, elements, errors, mode
    images: list[tuple[str, bytes]] = field(default_factory=list)   # (mime, bytes)


def context_block(user, identity: Identity, ctx: dict, images: int = 0, today: date | None = None) -> str:
    today = today or date.today()
    role = ROLE_LABELS.get(identity.role or "", identity.role or "")
    if ctx.get("is_accounts"):
        role += ", does the Accounts work"
    lines = [f"Today: {today:%A} {today.day} {today:%B %Y}", f"Asked by: {getattr(user, 'name', None) or 'someone'} ({role})"]
    page = ctx.get("page_path")
    if page:
        title = ctx.get("page_title")
        gs = knowledge.guides_for_path(page)
        lines.append(f"Page: {title + ' - ' if title else ''}{page}" + (f" (guide: {gs[0].id})" if gs else ""))
    rec = ctx.get("record")
    if rec and rec.get("id"):
        lines.append(f"Record on screen: {rec.get('kind', 'record')} {rec.get('label') or ''} id={rec['id']}".replace("  ", " "))
    for e in (ctx.get("elements") or [])[:4]:
        bits = [f"{e.get('role') or 'element'} \"{(e.get('label') or e.get('text') or '').strip()[:80]}\""]
        if e.get("heading"):
            bits.append(f"in section \"{e['heading'][:60]}\"")
        known = knowledge.element_by_src((e.get("source") or [None])[0]) if e.get("source") else None
        if known and known.get("hint"):
            bits.append(f"(its hint says: {known['hint'][:200]})")
        lines.append("Pointed at: " + " ".join(bits))
    if ctx.get("cannot_open"):
        lines.append("This person can't open (answer \"You don't have permission to view that.\" to anything about these): "
                     + ", ".join(ctx["cannot_open"]))
    errs = [x.get("message") for x in (ctx.get("errors") or [])[-3:] if x.get("message")]
    if errs:
        lines.append("Recent messages on screen: " + " | ".join(m[:160] for m in errs))
    if images:
        lines.append(f"Screenshot{'s' if images > 1 else ''} attached: {images} (look at {'them' if images > 1 else 'it'})")
    return "<context>\n" + "\n".join(lines) + "\n</context>"


def page_guide(page_path: str | None, blocked: set[str], history: list[tuple[str, str]]) -> str:
    """The guide for the page the question was asked on, in full - unless this conversation already has it or the
    person can't open that page. Added after <context>, so the fixed start of the request stays cached, and later
    turns replay it from history (cached too)."""
    from app.brain import access
    gs = knowledge.guides_for_path(page_path)
    if not gs:
        return ""
    g = gs[0]
    sec = access.section_for(page_path)
    if sec and sec in blocked:
        return ""
    tag = f'<guide id="{g.id}"'
    if any(tag in text for role, text in history if role == "user"):
        return ""
    return f'\n\n{tag} title="{g.title}">\n{g.body}\n</guide>'


def finish(text: str, page_path: str | None) -> tuple[str, dict]:
    """Pull out the follow-up questions; keep "Show me" only for labels that exist on that page."""
    asks = [a.strip() for a in ASK.findall(text)][:3]
    text = ASK.sub("", text)
    known = knowledge.labels_for_path(page_path)
    shows: list[str] = []

    def exists(label: str) -> bool:
        low = label.lower()
        # labels with a changing end ("Email the …" on screen) match on how they start
        return low in known or any(len(k) >= 4 and (low.startswith(k) or k.startswith(low)) for k in known)

    def keep(m: re.Match) -> str:
        label = m.group(1).strip()
        if known and not exists(label):
            return ""
        if label not in shows:
            shows.append(label)
        return f"[[show:{label}]]"
    text = SHOW.sub(keep, text)
    links = [{"label": a, "href": h} for a, h in LINK.findall(text)]
    text = re.sub(r"[ \t]+\n", "\n", text).strip()
    return text, {"suggestions": asks, "show": shows, "links": links}


def _usage(u) -> dict:
    g = lambda k: int(getattr(u, k, 0) or 0)  # noqa: E731
    return {"input_tokens": g("prompt_token_count"), "cached_tokens": g("cached_content_token_count"),
            "output_tokens": g("candidates_token_count") + g("thoughts_token_count")}


async def run(user, identity: Identity, history: list[tuple[str, str]], asked: Asked, model_text: str) -> AsyncIterator[dict]:
    """Yields {"type": "step", "label"} / {"type": "text", "delta"} / {"type": "done", "text", "extras", "trace"}.

    history: [(role, text)] oldest first - user turns as the model first saw them, assistant answers as shown.
    """
    started = time.monotonic()
    r = agent.route(asked.question, asked.context)
    trace: dict = {"route": r.name, "thinking": r.thinking, "model": agent.model_name(), "steps": [],
                   "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "llm_calls": 0}
    if not agent.configured():
        yield {"type": "done", "text": NOT_ON, "extras": {}, "trace": {**trace, "error": "not_configured"}}
        return

    from google.adk.agents.run_config import RunConfig, StreamingMode
    from google.adk.events import Event
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    svc = InMemorySessionService()
    session = await svc.create_session(app_name="bmi_brain", user_id=str(user.id), state=registry.identity_state(identity))
    for role, text in history:
        await svc.append_event(session, Event(invocation_id="history", author="user" if role == "user" else "brain",
                                              content=types.Content(role="user" if role == "user" else "model", parts=[types.Part(text=text)])))
    parts = [types.Part(text=model_text)] + [types.Part.from_bytes(data=b, mime_type=m) for m, b in asked.images]
    runner = Runner(app=agent.app_for(r), session_service=svc)
    answer: list[str] = []
    announced: set[str] = set()
    try:
        async for ev in runner.run_async(user_id=str(user.id), session_id=session.id,
                                         new_message=types.Content(role="user", parts=parts),
                                         run_config=RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=12)):
            if ev.usage_metadata and not ev.partial:
                u = _usage(ev.usage_metadata)
                for k, v in u.items():
                    trace[k] += v
                trace["llm_calls"] += 1
            for call in ev.get_function_calls() or []:
                label = registry.label_for(call.name)
                if label not in announced:
                    announced.add(label)
                    yield {"type": "step", "label": label}
            if not ev.content or not ev.content.parts:
                continue
            texts = [p.text for p in ev.content.parts if p.text and not getattr(p, "thought", False)]
            if not texts:
                continue
            if ev.partial:
                yield {"type": "text", "delta": "".join(texts)}
            else:
                answer.append("".join(texts))
    except Exception as exc:
        log.exception("brain turn failed")
        trace.update(steps=registry.TRACES.pop(session.id, []), ms=int((time.monotonic() - started) * 1000), error=exc.__class__.__name__)
        yield {"type": "done", "text": FAILED, "extras": {}, "trace": trace}
        return
    trace["steps"] = registry.TRACES.pop(session.id, [])
    trace["ms"] = int((time.monotonic() - started) * 1000)
    text, extras = finish("\n\n".join(a.strip() for a in answer if a.strip()) or FAILED, asked.context.get("page_path"))
    yield {"type": "done", "text": text, "extras": extras, "trace": trace}


def new_id() -> uuid.UUID:
    return uuid.uuid4()
