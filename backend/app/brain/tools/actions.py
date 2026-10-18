"""Phase 4 tools: the Brain offering to do something. None of these change anything - each checks the request and
puts a card in the chat (app/brain/actions.py); it runs only when the person presses Confirm."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.brain import access
from app.brain.actions import propose
from app.brain.registry import ToolEnv, ToolError, brain_tool
from app.brain.tools.crm import UUID_RE, _companies, _contacts, _email

UK = ZoneInfo("Europe/London")
CALL_TYPES = {"completed": "Call Completed", "left message": "Call Left Message", "no answer": "Call Attempted",
              "attempted": "Call Attempted", "received": "Call Received"}


def _pick(env: ToolEnv, client: str, people_only: bool = False) -> tuple[str, uuid.UUID, str]:
    """One contact or company the person can see, or a plain question back listing the choices."""
    client = (client or "").strip()
    if not client:
        raise ToolError("Ask who this is for (a contact or a company).")
    if UUID_RE.match(client):
        from app.core import visibility as vis
        cid = uuid.UUID(client)
        from app.models import Company, Contact
        if (c := env.db.get(Contact, cid)) and vis.can_see_contact(env.db, cid, env.identity):
            return "contact", c.id, c.full_name or "the contact"
        if not people_only and (co := env.db.get(Company, cid)) and vis.can_see_company(env.db, cid, env.identity):
            return "company", co.id, co.name
        raise ToolError("There's no contact or company with that id that they can see.")
    people = _contacts(env, client, 6)
    firms = [] if people_only else _companies(env, client, 6)
    exact = [("contact", p.id, p.full_name) for p in people if (p.full_name or "").lower() == client.lower()] + \
            [("company", f.id, f.name) for f in firms if (f.name or "").lower() == client.lower()]
    found = exact or [("contact", p.id, p.full_name) for p in people] + [("company", f.id, f.name) for f in firms]
    if len(found) == 1:
        return found[0]
    if not found:
        raise ToolError(f"No {'contact' if people_only else 'contact or company'} matches \"{client}\" for them. Ask them to check the name.")
    choices = "; ".join(f"{name} ({kind}, id {rid})" for kind, rid, name in found[:6])
    raise ToolError(f"More than one match - ask which one they mean (offer them as [[ask:...]] choices): {choices}")


def _href(kind: str, rid) -> str:
    return f"/{'contacts' if kind == 'contact' else 'companies'}/{rid}"


def _when(text: str) -> tuple[datetime, str]:
    t = (text or "").strip().replace("T", " ")
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?: (\d{1,2}):(\d{2}))?$", t)
    if not m:
        raise ToolError("Give the date as YYYY-MM-DD (and a time as HH:MM if they said one), worked out from today's date in the context.")
    d = date.fromisoformat(m.group(1))
    at = time(int(m.group(2)), int(m.group(3))) if m.group(2) else time(9, 0)
    due = datetime.combine(d, at, tzinfo=UK)
    if due < datetime.now(UK) - timedelta(minutes=5):
        raise ToolError("That date has already passed. Ask them for a date in the future.")
    return due, f"{due:%a} {due.day} {due:%b %Y}, {due:%H:%M}"


@brain_tool("Getting a reminder ready", read_only=False)
def propose_reminder(env: ToolEnv, when: str, note: str, client: str = "") -> dict:
    """Offer to set a reminder for the person asking (they confirm it on a card; nothing is saved until then).

    Args:
      when: the date as YYYY-MM-DD, plus " HH:MM" if they gave a time (UK time; 09:00 if not)
      note: what to be reminded about, in their words
      client: optional contact or company name (or id) the reminder is about
    """
    access.require(env, "reminders")
    due, label = _when(when)
    kind = rid = None
    name = None
    if client.strip():
        kind, rid, name = _pick(env, client)
    return propose(env, "reminder",
                   {"due_at": due.isoformat(), "when_label": label, "note": note.strip()[:2000],
                    "record_kind": kind, "record_id": str(rid) if rid else None},
                   title="Set a reminder", confirm="Set the reminder",
                   lines=[("When", label), ("About", name or ""), ("Note", note.strip()[:300])],
                   links=[{"label": name, "href": _href(kind, rid)}] if rid else [])


@brain_tool("Getting the note ready", read_only=False)
def propose_log(env: ToolEnv, client: str, text: str, what: str = "note", outcome: str = "", subject: str = "") -> dict:
    """Offer to add a note, or log a call or meeting, on a contact or company (they confirm it on a card first).

    Args:
      client: the contact or company name (or id)
      text: the note, or what was said / agreed, in their words
      what: "note", "call" or "meeting"
      outcome: for a call: "completed", "left message", "no answer" or "received"
      subject: optional short heading for a call or meeting
    """
    what = (what or "note").strip().lower()
    if what not in ("note", "call", "meeting"):
        raise ToolError('"what" must be note, call or meeting.')
    if not text.strip():
        raise ToolError("Ask what the note should say.")
    kind, rid, name = _pick(env, client)
    access.require(env, "contacts" if kind == "contact" else "companies")
    history_type = None
    if what == "call":
        history_type = CALL_TYPES.get(outcome.strip().lower(), "Call Completed")
    elif what == "meeting":
        history_type = "Meeting Held"
    title = "Add a note" if what == "note" else f"Log the {what}"
    return propose(env, "log",
                   {"what": what, "text": text.strip()[:8000], "subject": subject.strip()[:200] or None, "history_type": history_type,
                    "record_kind": kind, "record_id": str(rid), "record_label": name},
                   title=title, confirm="Save it",
                   lines=[("On", name), ("Type", history_type or "Note"), ("Subject", subject.strip()), ("Text", text.strip()[:600])],
                   links=[{"label": name, "href": _href(kind, rid)}])


@brain_tool("Writing the email", read_only=False)
def propose_email(env: ToolEnv, person: str, subject: str, body: str) -> dict:
    """Offer to send an email to a contact from the person's own Outlook. They see the whole email on a card and
    press Send; nothing is sent before that. Write the body in their voice, plain text, signed with their first name.

    Args:
      person: the contact's name or email (or id)
      subject: the subject line
      body: the email text (blank lines between paragraphs)
    """
    access.require(env, "contacts")
    from app.models import MailAccount
    if not env.db.scalar(select(MailAccount.id).where(MailAccount.user_id == env.user.id)):
        raise ToolError("Their Outlook isn't connected, so you can't send it. Give them the email text in your answer to copy, "
                        "and say they can connect Outlook in Settings to send from here.")
    kind, rid, name = _pick(env, person, people_only=True)
    to = _email(env, rid)
    if not to:
        raise ToolError(f"{name} has no email address on record. Say so; they can add one on the contact page.")
    return propose(env, "email",
                   {"to": to, "subject": subject.strip()[:300], "body": body.strip()[:20000],
                    "record_kind": "contact", "record_id": str(rid), "record_label": name},
                   title="Send an email", confirm="Send it",
                   lines=[("To", f"{name} <{to}>"), ("Subject", subject.strip()), ("Email", body.strip())],
                   links=[{"label": name, "href": _href("contact", rid)}])


@brain_tool("Getting a booking ready", read_only=False)
def propose_booking(env: ToolEnv, client: str, proposal: str = "") -> dict:
    """Offer to start a new booking for a client: on Confirm the booking form opens filled in with the client
    (and the proposal's products if one is given), for them to check and save as pencilled or confirm.

    Args:
      client: the company name (or id)
      proposal: optional proposal id to start from
    """
    access.require(env, "orders")
    kind, rid, name = _pick(env, client)
    q = f"{'company' if kind == 'company' else 'contact'}={rid}"
    if proposal.strip():
        if not UUID_RE.match(proposal.strip()):
            raise ToolError("Use the proposal's id (from the proposal link).")
        q += f"&proposal={proposal.strip()}"
    href = f"/sales/deals/new?{q}"
    return propose(env, "booking", {"href": href, "record_kind": kind, "record_id": str(rid)},
                   title="Start a booking", confirm="Open the booking form",
                   lines=[("Client", name), ("From", "the proposal" if proposal.strip() else "")],
                   links=[{"label": name, "href": _href(kind, rid)}])


@brain_tool("Getting the card decision ready", read_only=False)
def propose_review_decision(env: ToolEnv, card_id: str, button: str, note: str = "") -> dict:
    """Offer to press one of a Review Queue card's buttons for them (they confirm first).

    Args:
      card_id: the card's id (from review_items)
      button: the button's label exactly as review_items lists it
      note: optional note to save with the decision
    """
    access.require(env, "review_queue")
    from app.api.routes.review_queue import _is_visible
    from app.automations.registry import get_kind
    from app.models import ReviewQueueItem
    try:
        item = env.db.get(ReviewQueueItem, uuid.UUID(card_id.strip()))
    except ValueError:
        item = None
    if not item or not _is_visible(item, env.identity, env.db):
        raise ToolError("There's no waiting card with that id for them. Use review_items to find it.")
    if item.status != "pending":
        raise ToolError("That card has already been dealt with.")
    k = get_kind(item.kind)
    action = next((a for a in (k.actions if k else []) if a.label.lower() == button.strip().lower() or a.id == button.strip()), None)
    if not action:
        raise ToolError("That card has no such button. Its buttons are: " + ", ".join(a.label for a in (k.actions if k else [])))
    if action.requires_contact_picker or action.requires_related_entity_choice or any(f.required and f.field_type != "bool" for f in action.extra_fields):
        raise ToolError("That button needs choices only the card itself can take. Send them to the card: "
                        f"/automations/review?kind={quote(item.kind)}")
    if action.requires_note and not note.strip():
        raise ToolError("That button needs a note - ask them what to write.")
    summary = (item.payload or {}).get("summary") or (item.payload or {}).get("subject") or k.label
    href = f"/automations/review?kind={quote(item.kind)}"
    return propose(env, "review",
                   {"item_id": str(item.id), "action_id": action.id, "action_label": action.label, "note": note.strip() or None,
                    "queue_href": href},
                   title=f"{k.label}: {action.label}", confirm=action.label,
                   lines=[("Card", str(summary)[:300]), ("Button", action.label), ("Note", note.strip())],
                   links=[{"label": "See the card", "href": href}])


@brain_tool("Getting the switch ready", read_only=False)
def propose_automation_switch(env: ToolEnv, automation: str, on: bool) -> dict:
    """Offer to switch an automation on or off (administrators only; they confirm first).

    Args:
      automation: the automation's name as automations_overview shows it
      on: true to switch it on, false to switch it off
    """
    if env.identity.is_known and not env.identity.is_admin:
        raise ToolError("Only administrators can switch automations on or off. Say so kindly.")
    from app.automations import runtime_settings
    from app.automations.settings_registry import AUTOMATION_SETTING_DEFS
    words = automation.strip().lower()
    defs = [d for d in AUTOMATION_SETTING_DEFS if d.key.endswith("_enabled") and d.type == "bool"]
    hits = [d for d in defs if d.label.lower() == words] or [d for d in defs if words in d.label.lower() or words in d.key]
    if not hits:
        raise ToolError("No automation switch matches that. Use automations_overview to find its name.")
    if len(hits) > 1:
        raise ToolError("More than one matches - ask which: " + "; ".join(d.label for d in hits[:6]))
    d = hits[0]
    now_on = bool(runtime_settings.effective_value(env.db, d.key))
    if now_on == bool(on):
        raise ToolError(f"{d.label} is already {'on' if on else 'off'}. Tell them; nothing to do.")
    return propose(env, "automation", {"key": d.key, "label": d.label, "on": bool(on)},
                   title=f"Switch {d.label} {'on' if on else 'off'}", confirm=f"Switch it {'on' if on else 'off'}",
                   lines=[("Automation", d.label), ("Now", "On" if now_on else "Off"), ("After", "On" if on else "Off"),
                          ("What it does", d.description[:300] if d.description else "")],
                   links=[{"label": "Automation settings", "href": "/automations/settings"}])
