"""Phase 4: things the Brain can do for you - always with a confirmation card first.

The Brain never changes anything itself. An action tool (app/brain/tools/actions.py) checks the request, works out
exactly what would happen and saves it here as a *pending* BrainAction; the chat shows it as a card. Only when the
person presses Confirm does `decide()` run it - as that person, with their permissions checked again (they may have
changed since the card was made). Cancel, a new question, or a day passing leaves everything as it was.

On the wire this is AG-UI's interrupt: the answer ends with RUN_FINISHED outcome "interrupt" (one interrupt per
card), and the Confirm/Cancel click comes back as the next run's `resume` (app/api/routes/brain.py).
"""
from __future__ import annotations

import html
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.brain.registry import ToolEnv, ToolError
from app.core import visibility as vis
from app.core.identity import Identity
from app.models import BrainAction

log = logging.getLogger("app.brain")

EXPIRES_AFTER = timedelta(days=1)
# session id -> ids of the cards proposed during that turn (read by the runner, like registry.TRACES)
PROPOSALS: dict[str, list[str]] = {}


class ActionError(Exception):
    """A plain sentence saying why it couldn't be done."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def propose(env: ToolEnv, kind: str, args: dict, title: str, lines: list[tuple[str, str]],
            links: list[dict] | None = None, confirm: str = "Confirm") -> dict:
    """Saves a card for the person to confirm and tells the model what to say next."""
    if not env.user:
        raise ToolError("Only a signed-in person can be offered that.")
    conv = None
    try:
        conv = uuid.UUID(str(env.conversation_id)) if env.conversation_id else None
    except ValueError:
        conv = None
    a = BrainAction(id=uuid.uuid4(), user_id=env.user.id, conversation_id=conv, kind=kind, args=args, status="pending",
                    preview={"title": title, "lines": [[k, v] for k, v in lines if v], "links": links or [], "confirm": confirm},
                    created_at=_now(), expires_at=_now() + EXPIRES_AFTER)
    env.db.add(a)
    env.db.commit()
    if env.session_id:
        PROPOSALS.setdefault(env.session_id, []).append(str(a.id))
    return {"card": title, "status": "waiting for them to press Confirm or Cancel on the card below your answer",
            "say": "Nothing has been done yet. In one short sentence, tell them it's on the card for them to check and confirm."}


def card(a: BrainAction) -> dict:
    """What the chat shows (kept on the answer's context, so a reopened chat shows the card as it ended)."""
    p = a.preview or {}
    return {"id": str(a.id), "kind": a.kind, "title": p.get("title"), "lines": p.get("lines") or [], "links": p.get("links") or [],
            "confirm": p.get("confirm") or "Confirm", "status": a.status, "result": a.result or {},
            "expires_at": a.expires_at.isoformat() if a.expires_at else None}


def decide(db: Session, identity: Identity, user, action_id: str, confirmed: bool) -> BrainAction:
    try:
        a = db.get(BrainAction, uuid.UUID(str(action_id)))
    except ValueError:
        a = None
    if not a or a.user_id != user.id:
        raise ActionError("That card isn't there any more.")
    if a.status != "pending":
        return a   # already decided (a double click, or another tab): nothing happens twice
    a.decided_at = _now()
    if a.expires_at and a.expires_at < _now():
        a.status, a.result = "expired", {"text": "That card had expired, so nothing was changed. Ask again and I'll make a new one."}
    elif not confirmed:
        a.status, a.result = "cancelled", {"text": "Cancelled - nothing was changed."}
    else:
        try:
            a.result = EXECUTORS[a.kind](db, identity, user, a.args)
            a.status = "done"
        except ActionError as e:
            db.rollback()
            a = db.get(BrainAction, a.id)
            a.status, a.result, a.decided_at = "failed", {"text": str(e)}, _now()
        except Exception:
            log.exception("brain action %s failed", a.kind)
            db.rollback()
            a = db.get(BrainAction, a.id)
            a.status, a.result, a.decided_at = "failed", {"text": "That didn't work just now, so nothing was changed. Please try again."}, _now()
    db.commit()
    return a


def cancel_waiting(db: Session, conversation_id) -> None:
    """A new question moves the chat on: cards still waiting in it are cancelled (nothing was done)."""
    for a in db.query(BrainAction).filter(BrainAction.conversation_id == conversation_id, BrainAction.status == "pending"):
        a.status, a.decided_at, a.result = "cancelled", _now(), {"text": "Not confirmed - nothing was changed."}


# ---- what runs on Confirm ---------------------------------------------------------------------------------------

def _record(db: Session, identity: Identity, args: dict) -> tuple[str | None, uuid.UUID | None]:
    kind, rid = args.get("record_kind"), args.get("record_id")
    if not kind or not rid:
        return None, None
    rid = uuid.UUID(rid)
    ok = vis.can_see_contact(db, rid, identity) if kind == "contact" else vis.can_see_company(db, rid, identity)
    if not ok:
        raise ActionError("You can't open that record any more, so nothing was changed.")
    return kind, rid


def _reminder(db: Session, identity: Identity, user, args: dict) -> dict:
    from app.models import Reminder
    kind, rid = _record(db, identity, args)
    r = Reminder(id=uuid.uuid4(), user_id=user.id, contact_id=rid if kind == "contact" else None,
                 company_id=rid if kind == "company" else None, due_at=datetime.fromisoformat(args["due_at"]),
                 note=args.get("note") or None, email_me=True, status="open")
    db.add(r)
    db.commit()
    return {"text": f"Reminder set for {args['when_label']}.", "links": [{"label": "Your reminders", "href": "/reminders"}]}


def _log(db: Session, identity: Identity, user, args: dict) -> dict:
    from app.api.schemas import HistoryCreate, NoteCreate
    kind, rid = _record(db, identity, args)
    href = f"/{'contacts' if kind == 'contact' else 'companies'}/{rid}"
    if args["what"] == "note":
        body = NoteCreate(body=args["text"], created_by_user_id=user.id)
        if kind == "contact":
            from app.api.routes.contacts import add_contact_note
            add_contact_note(rid, body, db)
        else:
            from app.api.routes.companies import add_company_note
            add_company_note(rid, body, db)
        return {"text": "Note added.", "links": [{"label": args["record_label"], "href": href}]}
    h = HistoryCreate(history_type=args["history_type"], subject=args.get("subject"), details=args["text"],
                      occurred_at=_now(), created_by_user_id=user.id)
    if kind == "contact":
        from app.api.routes.contacts import add_contact_history
        add_contact_history(rid, h, db)
    else:
        from app.api.routes.companies import add_company_history
        add_company_history(rid, h, db)
    return {"text": f"Logged: {args['history_type']}.", "links": [{"label": args["record_label"], "href": href}]}


def _email(db: Session, identity: Identity, user, args: dict) -> dict:
    from sqlalchemy import select

    from app.models import MailAccount
    from app.services import outlook
    kind, rid = _record(db, identity, args)
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id))
    if not acct:
        raise ActionError("Your Outlook isn't connected, so nothing was sent. Connect it in Settings, then ask again.")
    body = "<p>" + html.escape(args["body"]).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    try:
        outlook.send_mail(db, acct, to=[args["to"]], subject=args["subject"], html_body=body)
    except outlook.OutlookAuthError:
        raise ActionError("Your Outlook connection needs renewing, so nothing was sent. Reconnect it in Settings, then try again.")
    except outlook.RateLimited:
        raise ActionError("Outlook asked us to slow down, so nothing was sent. Try again in a minute.")
    except RuntimeError:
        raise ActionError("Outlook didn't accept the email, so nothing was sent. Please try again.")
    if kind == "contact":   # same record of it as mail merge keeps
        from app.api.routes.contacts import add_contact_history
        from app.api.schemas import HistoryCreate
        add_contact_history(rid, HistoryCreate(history_type="E-mail Sent", subject=args["subject"], details=args["body"][:4000],
                                               occurred_at=_now(), created_by_user_id=user.id), db)
    return {"text": f"Sent to {args['to']} from your Outlook.", "links": [{"label": args["record_label"], "href": f"/contacts/{rid}"}] if rid else []}


def _booking(db: Session, identity: Identity, user, args: dict) -> dict:
    _record(db, identity, args)
    return {"text": "The booking form is ready, filled in for the client. Check it, then save it as pencilled or confirm it.",
            "links": [{"label": "Open the new booking", "href": args["href"]}]}


def _review(db: Session, identity: Identity, user, args: dict) -> dict:
    from app.api.routes.review_queue import resolve_review_item
    from app.api.schemas import ReviewActionRequest
    try:
        resolve_review_item(uuid.UUID(args["item_id"]), args["action_id"], ReviewActionRequest(note=args.get("note") or None), db, identity)
    except HTTPException as e:
        raise ActionError(e.detail if isinstance(e.detail, str) and e.status_code < 500 else "That card couldn't be updated, so nothing changed.")
    except ValueError as e:
        raise ActionError(str(e))
    return {"text": f"Done: {args['action_label']}.", "links": [{"label": "Review Queue", "href": args["queue_href"]}]}


def _automation(db: Session, identity: Identity, user, args: dict) -> dict:
    from app.automations import runtime_settings
    if identity.is_known and not identity.is_admin:
        raise ActionError("Only administrators can switch automations on or off.")
    runtime_settings.set_override(db, args["key"], bool(args["on"]))
    db.commit()
    return {"text": f"{args['label']} is now {'on' if args['on'] else 'off'}.",
            "links": [{"label": "Automation settings", "href": "/automations/settings"}]}


EXECUTORS: dict[str, Callable[[Session, Identity, object, dict], dict]] = {
    "reminder": _reminder, "log": _log, "email": _email, "booking": _booking, "review": _review, "automation": _automation,
}
