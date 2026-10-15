"""Automations and the Review Queue, live: what's on or off, when each last ran and how it went, its settings,
and what's waiting for whom. Only for people who can open those screens (app/brain/access.py); the Review Queue
counts are scoped exactly like the queue itself (a salesperson sees only their own kinds and items)."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from sqlalchemy import func, select

from app.brain import access
from app.brain.registry import ToolEnv, ToolError, brain_tool


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("_", " ").replace("-", " ").split())


@brain_tool("Checking the automations")
def automations_overview(env: ToolEnv, area: str = "") -> dict:
    """Every automation right now: on or off, how often it runs, when it last ran and whether that went well,
    and how many review cards it has waiting. Use for "what automations are live?", "is anything broken?".

    Args:
      area: optional - only one group, e.g. "Revenue & Orders", "CRM Data Hygiene", "Sales & Follow-ups"
    """
    access.require(env, "automations_hub")
    from app.automations.status import overview
    rows = overview(env.db)
    if area.strip():
        a = _norm(area)
        rows = [r for r in rows if a in _norm(r["area"]) or a in _norm(r["name"])] or rows
    on = [r for r in rows if r["on"] and r["id"] != "made_by_people"]
    return {
        "summary": f"{len(on)} of {len([r for r in rows if r['id'] != 'made_by_people'])} automations are switched on; "
                   f"{sum(c['waiting'] for r in rows for c in r['cards'])} review cards are waiting.",
        "automations": [{k: r[k] for k in ("name", "area", "on", "schedule", "last_run", "problems_this_week", "link")}
                        | {"waiting": sum(c["waiting"] for c in r["cards"]), "id": r["id"]} for r in rows],
        "see_all": "/automations",
    }


@brain_tool("Looking at the automation")
def automation_detail(env: ToolEnv, name: str) -> dict:
    """One automation in depth: what it does, the setting that switches it on, its schedule, its recent runs,
    every setting with its current value and default, and the review cards it makes (with their buttons and how
    many were approved or rejected in the last 30 days). Use for "how does X work?", "why didn't X run?".

    Args:
      name: the automation's name or a word from it, its card's name (e.g. "Uninvoiced Bookings") or its id
    """
    access.require(env, "automations_hub")
    from app.automations.status import detail, overview
    rows = [r for r in overview(env.db) if r["id"] != "made_by_people"]
    want = _norm(name)
    exact = [r for r in rows if want in (_norm(r["id"]), _norm(r["name"]))]
    hits = exact or [r for r in rows if want in _norm(r["name"]) or want in _norm(r["id"]) or want in _norm(r["what_it_does"])
                     or any(want in _norm(c["card"]) for c in r["cards"]) or want in _norm(r["area"])]
    if not hits:
        raise ToolError("No automation matches that. Use automations_overview to see their names.")
    if len(hits) > 1:
        return {"which_one": [{"id": r["id"], "name": r["name"], "area": r["area"]} for r in hits[:8]],
                "note": "Several match - pick the closest, or ask which one they mean."}
    return detail(env.db, hits[0]["id"])


def _queue_scope(env: ToolEnv, stmt):
    from app.api.routes.review_queue import _apply_scope
    return _apply_scope(stmt, env.identity, env.db)


@brain_tool("Checking the Review Queue")
def review_queue_status(env: ToolEnv, card: str = "") -> dict:
    """What's waiting in the Review Queue for this person: how many cards of each kind, the oldest one, and what
    was handled in the last 7 days. Salespeople only ever see their own.

    Args:
      card: optional - one kind of card, e.g. "Ready to invoice" or "Follow-ups"
    """
    access.require(env, "review_queue")
    from datetime import timedelta

    from app.automations.registry import all_kinds
    from app.models import ReviewQueueItem
    kinds = {k.kind: k for k in all_kinds()}
    now = datetime.now(timezone.utc)
    stmt = _queue_scope(env, select(ReviewQueueItem.kind, func.count(), func.min(ReviewQueueItem.created_at))
                        .where(ReviewQueueItem.status == "pending").group_by(ReviewQueueItem.kind))
    done = dict(env.db.execute(_queue_scope(env, select(ReviewQueueItem.kind, func.count())
                                            .where(ReviewQueueItem.status.in_(("approved", "rejected")),
                                                   ReviewQueueItem.reviewed_at >= now - timedelta(days=7))
                                            .group_by(ReviewQueueItem.kind))).all())
    rows = []
    for kind, n, oldest in env.db.execute(stmt).all():
        k = kinds.get(kind)
        rows.append({"card": k.label if k else kind, "kind": kind, "waiting": n,
                     "oldest_waiting_days": (now - oldest).days if oldest else None,
                     "handled_last_7_days": done.get(kind, 0), "link": f"/automations/review?kind={quote(kind)}"})
    if card.strip():
        c = _norm(card)
        rows = [r for r in rows if c in _norm(r["card"]) or c in _norm(r["kind"])] or rows
    rows.sort(key=lambda r: -r["waiting"])
    return {"total_waiting": sum(r["waiting"] for r in rows), "by_card": rows, "see_all": "/automations/review",
            "note": None if rows else "Nothing waiting."}


@brain_tool("Looking at the waiting cards")
def review_items(env: ToolEnv, card: str, limit: int = 8) -> dict:
    """The waiting cards of one kind, oldest first: their one-line summary and how long they've waited.

    Args:
      card: the kind of card, e.g. "Ready to invoice", "Duplicate contact" (or its id from review_queue_status)
      limit: how many (up to 20)
    """
    access.require(env, "review_queue")
    from app.automations.registry import all_kinds
    from app.models import ReviewQueueItem
    c = _norm(card)
    kinds = [k for k in all_kinds() if c in (_norm(k.kind), _norm(k.label))] or [k for k in all_kinds() if c in _norm(k.label)]
    if not kinds:
        raise ToolError("No card kind matches that. Use review_queue_status to see the kinds.")
    k = kinds[0]
    now = datetime.now(timezone.utc)
    items = env.db.scalars(_queue_scope(env, select(ReviewQueueItem).where(ReviewQueueItem.kind == k.kind, ReviewQueueItem.status == "pending"))
                           .order_by(ReviewQueueItem.created_at).limit(max(1, min(limit, 20)))).all()
    return {"card": k.label, "about": k.description, "buttons": [a.label for a in k.actions],
            "items": [{"summary": (i.payload or {}).get("summary") or (i.payload or {}).get("subject") or k.label,
                       "waiting_days": (now - i.created_at).days if i.created_at else None} for i in items],
            "link": f"/automations/review?kind={quote(k.kind)}"}
