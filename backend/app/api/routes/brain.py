"""The AI Hub chat and the "Ask AI" button (app/brain, docs/ai-hub-plan.md).

POST /brain/chat streams one answer in the AG-UI protocol (docs.ag-ui.com, spec 1.0 - `data: {json}` server-sent
events, encoded with the official `ag-ui-protocol` package):
  RUN_STARTED (threadId = conversation, metadata.message_id = the saved question)
  STEP_STARTED / STEP_FINISHED   what it's doing ("Looking at the booking")
  TEXT_MESSAGE_START / CONTENT / END   the answer's words as they arrive
  TOOL_CALL_START / ARGS / END   one "confirm_action" call per card the Brain proposed (Phase 4, app/brain/actions.py)
  RUN_FINISHED  result.message = the saved answer; outcome "interrupt" (one per card) or "success"
  RUN_ERROR     a plain sentence (not switched on, or it failed) - the answer is still saved
Confirm / Cancel on a card is the next POST with `resume: [{interruptId, status: "resolved" | "cancelled"}]`: it runs
the action (or not) and streams RUN_STARTED, TOOL_CALL_RESULT per card, a short TEXT_MESSAGE and RUN_FINISHED.
The request body is ours (question, page context, screenshots) plus AG-UI's `resume`; our own runner drives ADK.
"""
from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from ag_ui.core import (Interrupt, ResumeEntry, RunErrorEvent, RunFinishedEvent, RunFinishedInterruptOutcome, RunFinishedSuccessOutcome,
                        RunStartedEvent, StepFinishedEvent, StepStartedEvent, TextMessageContentEvent, TextMessageEndEvent,
                        TextMessageStartEvent, ToolCallArgsEvent, ToolCallEndEvent, ToolCallResultEvent, ToolCallStartEvent)
from ag_ui.encoder import EventEncoder
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.brain import actions, knowledge, runner
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import BrainAction, BrainConversation, BrainImage, BrainMessage, Feedback, User
from app.services.notify import create_notification

router = APIRouter(prefix="/brain", tags=["brain"])

DATA_URL = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,(.+)$", re.S)
MAX_IMAGES = 3
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_QUESTION = 4000


class ImageIn(BaseModel):
    data: str
    label: str | None = None
    width: int | None = None
    height: int | None = None


class ChatIn(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = ""
    context: dict = Field(default_factory=dict)
    images: list[ImageIn] = Field(default_factory=list)
    run_id: str | None = None
    resume: list[ResumeEntry] = Field(default_factory=list)   # AG-UI: the answer to the cards (Confirm / Cancel)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_context(ctx: dict) -> dict:
    """Only what the Brain uses, trimmed (it's shown back and kept)."""
    out: dict = {}
    for k in ("page_path", "page_title", "mode"):
        if isinstance(ctx.get(k), str):
            out[k] = ctx[k][:500]
    rec = ctx.get("record")
    if isinstance(rec, dict) and rec.get("id"):
        out["record"] = {k: str(rec.get(k))[:200] for k in ("kind", "id", "label") if rec.get(k)}
    els = []
    for e in (ctx.get("elements") or [])[:4]:
        if isinstance(e, dict):
            els.append({k: (e.get(k)[:300] if isinstance(e.get(k), str) else e.get(k)) for k in ("label", "role", "text", "heading", "selector")
                        if e.get(k)} | {"source": [str(s)[:200] for s in (e.get("source") or [])[:3]]})
    if els:
        out["elements"] = els
    errs = [{"message": str(x.get("message"))[:300]} for x in (ctx.get("errors") or [])[-5:] if isinstance(x, dict) and x.get("message")]
    if errs:
        out["errors"] = errs
    return out


def _message_out(m: BrainMessage, images: list[BrainImage] | None = None) -> dict:
    return {"id": str(m.id), "role": m.role, "text": m.text, "context": m.context or {},
            "rating": m.rating, "feedback_id": str(m.feedback_id) if m.feedback_id else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "images": [{"id": str(i.id), "label": i.label} for i in images or []]}


def _conversation(db: Session, user: User, cid: uuid.UUID) -> BrainConversation:
    c = db.get(BrainConversation, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "We couldn't find that conversation.")
    return c


ENCODER = EventEncoder()


def _ev(event) -> str:
    return ENCODER.encode(event)


def _stream(gen) -> StreamingResponse:
    return StreamingResponse(gen, media_type=ENCODER.get_content_type(), headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _card_calls(cards: list[dict], parent_id: str) -> list[str]:
    """Each proposed card as an AG-UI tool call the screen renders (the tool is the confirmation itself)."""
    out = []
    for c in cards:
        out += [_ev(ToolCallStartEvent(tool_call_id=c["id"], tool_call_name="confirm_action", parent_message_id=parent_id)),
                _ev(ToolCallArgsEvent(tool_call_id=c["id"], delta=json.dumps(c, default=str))),
                _ev(ToolCallEndEvent(tool_call_id=c["id"]))]
    return out


def _plain(text: str) -> str:
    """An answer without its formatting marks, for previews."""
    t = re.sub(r"\[\[[a-z]+:[^\]]*\]\]", "", text)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[*`>#]+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _title(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip().rstrip("?.!")
    return (t[:60].rsplit(" ", 1)[0] + "…") if len(t) > 64 else (t or "New chat")


@router.post("/chat")
async def chat(p: ChatIn, db: Session = Depends(get_db), user: User = Depends(current_user), identity: Identity = Depends(get_identity)):
    if p.resume:
        return await _resume(p, db, user, identity)
    question = p.message.strip()
    if not question and not p.images and not p.context.get("elements"):
        raise HTTPException(422, "Type a question, point at something or add a screenshot first.")
    if len(question) > MAX_QUESTION:
        raise HTTPException(422, "That's a very long question. Try asking it in a few shorter parts.")
    if len(p.images) > MAX_IMAGES:
        raise HTTPException(422, f"Add up to {MAX_IMAGES} screenshots.")
    pics = []
    for img in p.images:
        m = DATA_URL.match(img.data.strip())
        if not m:
            raise HTTPException(422, "One of the screenshots couldn't be read. Try taking it again.")
        raw = base64.b64decode(m.group(2), validate=False)
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(422, "One of the screenshots is too big. Try a smaller area.")
        pics.append((m.group(1), raw, img))
    ctx = _clean_context(p.context)
    question = question or "What is this and how do I use it?"

    def prepare():
        from app.sales import accounts
        if p.conversation_id:
            conv = _conversation(db, user, p.conversation_id)
            actions.cancel_waiting(db, conv.id)   # a new question moves on from any card left unanswered
        else:
            conv = BrainConversation(id=uuid.uuid4(), user_id=user.id, title=_title(question), started_on=ctx.get("page_path"))
            db.add(conv)
            db.flush()
        prior = db.scalars(select(BrainMessage).where(BrainMessage.conversation_id == conv.id)
                           .order_by(BrainMessage.created_at.desc()).limit(_history_limit())).all()[::-1]
        history = [(m.role, m.model_text or m.text) for m in prior if (m.model_text or m.text)]
        if history and history[0][0] != "user":
            history = history[1:]
        from app.brain import access
        ctx["is_accounts"] = bool(identity.user_uuid and accounts.can_approve(db, identity.user_uuid))
        ctx["cannot_open"] = access.blocked_labels(db, identity)
        model_text = (f"{question}\n\n{runner.context_block(user, identity, ctx, len(pics))}"
                      + runner.page_guide(ctx.get("page_path"), access.blocked(db, identity), history))
        ctx.pop("is_accounts", None)
        ctx.pop("cannot_open", None)
        msg = BrainMessage(id=uuid.uuid4(), conversation_id=conv.id, role="user", text=question, model_text=model_text, context=ctx,
                           created_at=_now())
        db.add(msg)
        db.flush()
        for mime, raw, img in pics:
            db.add(BrainImage(id=uuid.uuid4(), message_id=msg.id, mime=mime, data=raw, label=(img.label or "Screenshot")[:200],
                              width=img.width, height=img.height))
        conv.updated_at = _now()
        db.commit()
        return conv.id, msg.id, history, model_text

    conv_id, msg_id, history, model_text = await run_in_threadpool(prepare)
    asked = runner.Asked(question=question, context=ctx, images=[(m, b) for m, b, _ in pics])

    answer_id, run_id = uuid.uuid4(), p.run_id or str(uuid.uuid4())

    def save(final: dict) -> tuple[dict, list[dict]]:
        # times set here, not by the database, so a question always sorts before its answer
        cards = []
        for aid in final.get("actions") or []:
            a = db.get(BrainAction, uuid.UUID(aid))
            if a and a.user_id == user.id:
                a.message_id = answer_id
                cards.append(actions.card(a))
        extras = {**final["extras"], **({"actions": cards} if cards else {}), **({"error": True} if final.get("error") else {})}
        a = BrainMessage(id=answer_id, conversation_id=conv_id, role="assistant", text=final["text"], context=extras,
                         trace=final["trace"], created_at=_now())
        db.add(a)
        conv = db.get(BrainConversation, conv_id)
        conv.updated_at = _now()
        db.commit()
        db.refresh(a)
        return _message_out(a), cards

    async def stream():
        yield _ev(RunStartedEvent(thread_id=str(conv_id), run_id=run_id, metadata={"message_id": str(msg_id)}))
        step: str | None = None
        talking = False
        async for ev in runner.run(user, identity, history, asked, model_text, conversation_id=str(conv_id)):
            if ev["type"] == "step":
                if step:
                    yield _ev(StepFinishedEvent(step_name=step))
                step = ev["label"]
                yield _ev(StepStartedEvent(step_name=step))
                continue
            if step:
                yield _ev(StepFinishedEvent(step_name=step))
                step = None
            if ev["type"] == "text":
                if not talking:
                    talking = True
                    yield _ev(TextMessageStartEvent(message_id=str(answer_id), role="assistant"))
                yield _ev(TextMessageContentEvent(message_id=str(answer_id), delta=ev["delta"]))
            elif ev["type"] == "done":
                if talking:
                    yield _ev(TextMessageEndEvent(message_id=str(answer_id)))
                out, cards = await run_in_threadpool(save, ev)
                _log_usage(ev["trace"])
                if ev.get("error"):
                    yield _ev(RunErrorEvent(message=ev["text"], code=ev["error"]))
                    return
                for chunk in _card_calls(cards, str(answer_id)):
                    yield chunk
                outcome = (RunFinishedInterruptOutcome(interrupts=[
                    Interrupt(id=c["id"], reason="confirm_action", message=c["title"], tool_call_id=c["id"], expires_at=c["expires_at"])
                    for c in cards]) if cards else RunFinishedSuccessOutcome())
                yield _ev(RunFinishedEvent(thread_id=str(conv_id), run_id=run_id, result={"message": out}, outcome=outcome))

    return _stream(stream())


async def _resume(p: ChatIn, db: Session, user: User, identity: Identity):
    """Confirm / Cancel on the cards: run each (or not), note it in the chat, and stream the outcome."""
    if not p.conversation_id:
        raise HTTPException(422, "That card isn't part of a chat any more.")
    conv_id = p.conversation_id
    run_id = p.run_id or str(uuid.uuid4())
    answer_id = uuid.uuid4()

    def decide() -> tuple[list[dict], dict, uuid.UUID]:
        _conversation(db, user, conv_id)
        done = [actions.decide(db, identity, user, r.interrupt_id, r.status == "resolved") for r in p.resume]
        cards = [actions.card(a) for a in done]
        # the answer that showed the cards shows how each one ended
        for a in done:
            m = db.get(BrainMessage, a.message_id) if a.message_id else None
            if m and m.context.get("actions"):
                m.context = {**m.context, "actions": [actions.card(a) if c.get("id") == str(a.id) else c for c in m.context["actions"]]}
        said = "; ".join(f"{'Confirmed' if r.status == 'resolved' else 'Cancelled'}: {(a.preview or {}).get('title')}"
                         for a, r in zip(done, p.resume))
        q = BrainMessage(id=uuid.uuid4(), conversation_id=conv_id, role="user", text=said,
                         model_text=f"[On the card{'s' if len(done) > 1 else ''}: {said}]", context={"mode": "card"}, created_at=_now())
        db.add(q)
        text = "\n\n".join((a.result or {}).get("text") or "" for a in done).strip() or "Nothing was changed."
        links = [ln for a in done for ln in (a.result or {}).get("links") or []]
        ans = BrainMessage(id=answer_id, conversation_id=conv_id, role="assistant", text=text,
                           context={"links": links, "action_results": cards}, trace={"route": "card", "steps": []}, created_at=_now())
        db.add(ans)
        db.get(BrainConversation, conv_id).updated_at = _now()
        db.commit()
        db.refresh(ans)
        return cards, _message_out(ans), q.id

    cards, out, q_id = await run_in_threadpool(decide)

    async def stream():
        yield _ev(RunStartedEvent(thread_id=str(conv_id), run_id=run_id, metadata={"message_id": str(q_id)}))
        for c in cards:
            yield _ev(ToolCallResultEvent(message_id=str(answer_id), tool_call_id=c["id"], role="tool", content=json.dumps(c, default=str)))
        yield _ev(TextMessageStartEvent(message_id=str(answer_id), role="assistant"))
        yield _ev(TextMessageContentEvent(message_id=str(answer_id), delta=out["text"]))
        yield _ev(TextMessageEndEvent(message_id=str(answer_id)))
        yield _ev(RunFinishedEvent(thread_id=str(conv_id), run_id=run_id, result={"message": out, "cards": cards},
                                   outcome=RunFinishedSuccessOutcome()))

    return _stream(stream())


def _history_limit() -> int:
    from app.core.config import settings
    return max(2, settings.brain_history_messages)


def _log_usage(trace: dict) -> None:
    if not trace.get("llm_calls"):
        return
    from app.automations import llm
    try:
        cfg = llm._runtime_llm_settings()
        llm._log_usage(provider="gemini", model=trace.get("model") or "", call_type="chat", purpose="brain_chat",
                       prompt_tokens=trace.get("input_tokens", 0), completion_tokens=trace.get("output_tokens", 0),
                       cost_rates=llm._resolve_cost_rates(cfg, "gemini", trace.get("model") or ""), success=not trace.get("error"),
                       error_type=trace.get("error"), cached_tokens=trace.get("cached_tokens", 0))
    except Exception:
        pass


# ---- Conversations -----------------------------------------------------------------------------------

@router.get("/conversations")
def conversations(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    rows = db.scalars(select(BrainConversation).where(BrainConversation.user_id == user.id)
                      .order_by(BrainConversation.updated_at.desc()).limit(50)).all()
    return {"conversations": [{"id": str(c.id), "title": c.title, "started_on": c.started_on,
                               "updated_at": c.updated_at.isoformat() if c.updated_at else None} for c in rows]}


@router.get("/conversations/{cid}")
def conversation(cid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    c = _conversation(db, user, cid)
    msgs = db.scalars(select(BrainMessage).where(BrainMessage.conversation_id == c.id).order_by(BrainMessage.created_at)).all()
    imgs: dict = {}
    for i in db.scalars(select(BrainImage).where(BrainImage.message_id.in_([m.id for m in msgs]))) if msgs else []:
        imgs.setdefault(i.message_id, []).append(i)
    return {"id": str(c.id), "title": c.title, "messages": [_message_out(m, imgs.get(m.id)) for m in msgs]}


class RenameIn(BaseModel):
    title: str


@router.patch("/conversations/{cid}")
def rename(cid: uuid.UUID, p: RenameIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    c = _conversation(db, user, cid)
    c.title = p.title.strip()[:200] or c.title
    db.commit()
    return {"id": str(c.id), "title": c.title}


@router.delete("/conversations/{cid}", status_code=204)
def delete(cid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> None:
    db.delete(_conversation(db, user, cid))
    db.commit()


@router.get("/images/{iid}")
def image(iid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    i = db.get(BrainImage, iid)
    m = db.get(BrainMessage, i.message_id) if i else None
    c = db.get(BrainConversation, m.conversation_id) if m else None
    if not c or (c.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "We couldn't find that screenshot.")
    return Response(i.data, media_type=i.mime, headers={"Cache-Control": "private, max-age=86400"})


# ---- Was it helpful? --------------------------------------------------------------------------------

def _own_answer(db: Session, user: User, mid: uuid.UUID) -> tuple[BrainMessage, BrainConversation]:
    m = db.get(BrainMessage, mid)
    c = db.get(BrainConversation, m.conversation_id) if m else None
    if not m or not c or c.user_id != user.id or m.role != "assistant":
        raise HTTPException(404, "We couldn't find that answer.")
    return m, c


class RatingIn(BaseModel):
    rating: int | None = None    # 1 helpful, -1 not, None clears
    note: str | None = None


@router.post("/messages/{mid}/rating")
def rate(mid: uuid.UUID, p: RatingIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    m, _ = _own_answer(db, user, mid)
    if p.rating not in (1, -1, None):
        raise HTTPException(422, "Choose helpful or not helpful.")
    m.rating, m.rating_note = p.rating, (p.note or "").strip()[:2000] or None
    db.commit()
    return {"id": str(m.id), "rating": m.rating}


class ToFeedbackIn(BaseModel):
    note: str | None = None


@router.post("/messages/{mid}/feedback")
def to_feedback(mid: uuid.UUID, p: ToFeedbackIn, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """"This didn't help": the question and answer become a feedback item, so the team can fix the guide (or the screen)."""
    from app.api.routes import feedback as fb
    m, c = _own_answer(db, user, mid)
    if m.feedback_id:
        f = db.get(Feedback, m.feedback_id)
        if f:
            return {"feedback_id": str(f.id), "number": f.number}
    q = db.scalar(select(BrainMessage).where(BrainMessage.conversation_id == c.id, BrainMessage.role == "user",
                                             BrainMessage.created_at <= m.created_at).order_by(BrainMessage.created_at.desc()).limit(1))
    ctx = (q.context if q else {}) or {}
    note = (p.note or "").strip()
    message = (f"{note}\n\n" if note else "") + f"Asked the assistant: {q.text if q else ''}\n\nIt answered:\n{m.text}"
    f = Feedback(id=uuid.uuid4(), user_id=user.id, user_name=user.name, user_role=user.role, kind="confusing", message=message[:8000],
                 page_path=(ctx.get("page_path") or c.started_on or "/")[:500], page_title=ctx.get("page_title"),
                 elements=ctx.get("elements") or [], context={"source": "assistant", "errors": ctx.get("errors") or []},
                 status="new", me_too=[], comments=[])
    db.add(f)
    db.flush()
    m.feedback_id = f.id
    m.rating = -1
    for uid in db.scalars(select(User.id).where(User.role == "admin", User.is_active.is_(True), User.id != user.id)):
        create_notification(db, uid, "feedback", f"The assistant couldn't help {user.name} (#{f.number})", (q.text if q else "")[:200] or None,
                            link=f"/feedback?open={f.id}")
    db.commit()
    db.refresh(f)
    background.add_task(fb._sync_later, f.id)
    return {"feedback_id": str(f.id), "number": f.number}


# ---- Voice: speak a question -----------------------------------------------------------------------

@router.post("/transcribe")
async def transcribe(request: Request, user: User = Depends(current_user)) -> dict:
    from app.automations import llm
    audio = await request.body()
    if not audio:
        raise HTTPException(422, "We didn't hear anything. Try again, a bit closer to the microphone.")
    if len(audio) > 8 * 1024 * 1024:
        raise HTTPException(422, "That recording is too long. Try a shorter question.")
    mime = (request.headers.get("Content-Type") or "audio/webm").split(";")[0]
    text = await run_in_threadpool(llm.transcribe_audio, audio, mime, purpose="brain_voice")
    if not text:
        raise HTTPException(503, "We couldn't turn that into words just now. Please type your question instead.")
    return {"text": text}


# ---- What the panel shows before you ask -------------------------------------------------------------

@router.get("/suggestions")
def suggestions(page: str | None = None, user: User = Depends(current_user)) -> dict:
    """A few questions people ask on this page (from the guide's common questions)."""
    from app.brain import agent
    qs: list[str] = []
    for g in knowledge.guides_for_path(page)[:1] or []:
        for s in g.sections:
            if s.heading.lower().startswith("common questions"):
                qs += [q.strip() for q in re.findall(r"\*\*Q:\s*(.+?)\*\*", s.text)]
    if not qs:
        qs = ["How much have we booked so far this year?", "What did our biggest client last buy?", "What's on my list this week?",
              "How do I make a new booking?"]
    guide = (knowledge.guides_for_path(page) or [None])[0]
    return {"configured": agent.configured(), "questions": qs[:4], "guide": guide.title if guide else None}


# ---- Admin: what it's doing and costing ---------------------------------------------------------------

@router.get("/activity")
def activity(days: int = 14, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Only an administrator can see this.")
    since = _now() - timedelta(days=min(max(days, 1), 90))
    rows = db.execute(select(BrainMessage, BrainConversation).join(BrainConversation, BrainConversation.id == BrainMessage.conversation_id)
                      .where(BrainMessage.role == "assistant", BrainMessage.created_at >= since)
                      .order_by(BrainMessage.created_at.desc()).limit(300)).all()
    names = {u.id: u.name for u in db.scalars(select(User))}
    qs = {}
    if rows:
        for q in db.scalars(select(BrainMessage).where(BrainMessage.role == "user", BrainMessage.conversation_id.in_({c.id for _, c in rows}))):
            qs.setdefault(q.conversation_id, []).append(q)
    items = []
    tot_in = tot_cached = tot_ms = 0
    for m, c in rows:
        t = m.trace or {}
        prev = [q for q in qs.get(c.id, []) if q.created_at <= m.created_at]
        q = max(prev, key=lambda x: x.created_at) if prev else None
        tot_in += t.get("input_tokens", 0)
        tot_cached += t.get("cached_tokens", 0)
        tot_ms += t.get("ms", 0)
        items.append({"id": str(m.id), "at": m.created_at.isoformat(), "who": names.get(c.user_id, "Someone"),
                      "question": q.text if q else "", "page": (q.context or {}).get("page_path") if q else None,
                      "answer": _plain(m.text)[:400], "rating": m.rating, "feedback_id": str(m.feedback_id) if m.feedback_id else None,
                      "route": t.get("route"), "steps": [s.get("label") for s in t.get("steps", [])], "ms": t.get("ms"),
                      "input_tokens": t.get("input_tokens"), "cached_tokens": t.get("cached_tokens"), "output_tokens": t.get("output_tokens"),
                      "problem": bool(t.get("error"))})
    n = len(items)
    from app.brain import search as brain_search
    idx = brain_search.stats(db)
    return {"items": items, "index": {"chunks": idx["chunks"], "embedded": idx["embedded"], "meaning_search": idx["meaning_search"],
                                      "last_indexed": idx["last_indexed"].isoformat() if idx["last_indexed"] else None}, "summary": {
        "answers": n, "helpful": sum(1 for i in items if i["rating"] == 1), "not_helpful": sum(1 for i in items if i["rating"] == -1),
        "avg_seconds": round(tot_ms / n / 1000, 1) if n else None,
        "cache_hit_pct": round(100 * tot_cached / tot_in) if tot_in else None}}


# --- The Brain as a coach: tips, the welcome tour, celebrations (app/brain/coach.py) ---------------------------------

class DismissIn(BaseModel):
    tip_id: str = Field(min_length=1, max_length=120)
    forever: bool = False


class TourIn(BaseModel):
    tour: str = Field(min_length=1, max_length=40)
    done: bool = True


@router.get("/coach")
def coach_state(path: str = "/", db: Session = Depends(get_db), user: User = Depends(current_user), identity: Identity = Depends(get_identity)) -> dict:
    """Whether tips and celebrations are on, which tours are finished, and at most one tip for this page."""
    from app.brain import coach
    return coach.state(db, identity, user, path[:300])


@router.post("/coach/dismiss")
def coach_dismiss(p: DismissIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    from app.brain import coach
    coach.dismiss(db, user, p.tip_id, p.forever)
    return {"ok": True}


@router.post("/coach/tour")
def coach_tour(p: TourIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """Marks a welcome tour finished (or, with done=false, unfinished so it plays again)."""
    from app.brain import coach
    coach.tour_done(db, user, p.tour, p.done)
    return {"ok": True}
