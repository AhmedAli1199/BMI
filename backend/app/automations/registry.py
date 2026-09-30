"""The plug-in point every automation uses to add itself to the review
queue, without the generic API route or the frontend needing to know
anything about what a "bounce" or a "departure" actually is.

Each automation module (bounce_handling.py, ooo.py, departure.py, ...)
calls `register()` once per *kind* of review item it can produce, at
import time. A kind carries:

- its own human-readable label/description (shown as a filter chip and
  card header - never a generic "Review item"),
- its own list of actions, each with its own label/style/required input
  (so "Confirm & unsubscribe" and "Confirm successor" and "Approve sales
  template" can all exist side by side without the frontend hardcoding
  any of them - it just renders whatever buttons this list says exist),
- and a handler function that actually performs the CRM write for
  whichever action was clicked.

The review_queue table itself stores completely generic rows (kind,
payload, status) - see review_queue.py's docstring. This registry is
what gives each kind its specific meaning on top of that generic shape.

Payload contract (what an automation should put in ReviewQueueItem.payload
so the generic UI can render it without per-kind frontend code):

    {
      "summary": "One line shown as the card's headline",
      "details": [{"key": "...", "label": "...", "value": "...", "editable": bool}],
      "original_text": "Raw source text (email body, OCR'd label, etc.), OR a drafted action a rep can see before confirming (a follow-up note) - the meaning varies by kind, both render the same way, optional",
      "source_context": "A separate raw-source excerpt, only used when original_text above means something else (a draft) and there's still real source material worth showing distinctly - optional",
      "related_entities": [{"type": "contact"|"company", "id": "...", "label": "..."}],
      "suggested_contact": {"id": "...", "label": "..."} | None,
      "confidence": 0.0-1.0 | None,
    }

None of these keys are enforced by the schema (payload is a plain JSONB
blob) - they're a convention the frontend's generic renderer expects,
documented here so every automation module follows it without needing
its own bespoke UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

from sqlalchemy.orm import Session

from app.models import ReviewQueueItem

ActionStyle = Literal["primary", "secondary", "destructive"]
ActionOutcome = Literal["approved", "rejected"]


@dataclass(frozen=True)
class ExtraField:
    """One additional input the UI must collect before this action can be
    submitted, beyond the note/contact-picker shortcuts below - e.g. a
    name+email pair for "create this as a new contact". `field_type`
    "text" (default) renders a plain text input in the generic review
    card; `required` blocks submission until it's non-empty. "bool"
    renders a checkbox instead (e.g. SALES-011's "subscribe to
    newsletter" toggle) and submits "true"/"false" as the field's string
    value - `required` has no effect on it, since an unchecked box is a
    valid answer, not a missing one."""
    key: str
    label: str
    placeholder: str = ""
    required: bool = True
    field_type: Literal["text", "bool"] = "text"


@dataclass(frozen=True)
class ReviewAction:
    id: str
    label: str
    # Controls button color/prominence - "primary" is the expected/likely
    # choice, "destructive" is red and always paired with confirm_message.
    style: ActionStyle = "secondary"
    # Which coarse bucket this action counts as, for the status filter and
    # any future reporting - "what fraction of bounces did we end up
    # confirming vs. dismissing" only works if every action declares this.
    outcome: ActionOutcome = "approved"
    # If set, the UI shows a text box and requires it non-empty before the
    # action can be submitted - e.g. "why are you overriding this?".
    requires_note: bool = False
    # If set, the UI shows a contact search/picker and requires a
    # selection before the action can be submitted - e.g. "pick who this
    # should actually be matched to".
    requires_contact_picker: bool = False
    # Arbitrary additional text inputs this action needs - see ExtraField.
    extra_fields: list[ExtraField] = field(default_factory=list)
    # If set, the UI must collect a choice among this item's own
    # payload["related_entities"] (contacts only) before the action can be
    # submitted, and sends it as chosen_entity_id - e.g. CS-004's merge
    # action uses this to let the reviewer pick which of the two contacts
    # survives, rather than the automation guessing.
    requires_related_entity_choice: bool = False
    # If set, shown in a confirm step before the action fires - use for
    # anything that writes to multiple records or can't be undone from
    # the UI (a merge, a multi-record successor update).
    confirm_message: str | None = None


@dataclass(frozen=True)
class ReviewKind:
    kind: str
    label: str
    description: str
    actions: list[ReviewAction]
    # (db, item, action_id, input_data) -> None. Raise ValueError with a
    # human-readable message for anything the reviewer should see as an
    # error (stale data, missing contact, etc.) rather than a 500.
    handler: Callable[[Session, ReviewQueueItem, str, dict], None]
    # Optional: (db, item, extra_instructions) -> new draft text, for a
    # kind whose payload["original_text"] is an AI-drafted action (a
    # follow-up note/email) rather than source material - see
    # signal_triggers.py/followup_queue.py's _redraft_* functions. Lets
    # the review-queue UI offer "regenerate with instructions" before the
    # reviewer commits, without resolving/mutating the item - only an
    # explicit approve action does that. None (the default) means this
    # kind has no re-draftable text, and POST .../redraft 400s for it.
    redraft: Callable[[Session, ReviewQueueItem, str], str] | None = None
    # Phase 1 of scoping automations by role (see app/roles.py's
    # CAN_USE_AUTOMATIONS and frontend/src/lib/access.ts) - "sales" for a
    # kind that's genuinely a salesperson's own work (a follow-up draft on
    # their own lead), "admin" for CRM-hygiene work (merges, departures,
    # bounce triage) that stays with admins/data managers regardless of
    # this flag. Not enforced yet on its own - Phase 2 wires this (plus
    # ReviewQueueItem.source_db) into real per-request access checks;
    # this field only records the intended audience now, decided
    # kind-by-kind, so that phase has something correct to enforce rather
    # than guessing it retroactively.
    audience: Literal["sales", "admin"] = "admin"


_REGISTRY: dict[str, ReviewKind] = {}


def register(kind_def: ReviewKind) -> None:
    if kind_def.kind in _REGISTRY:
        raise ValueError(f"Review kind {kind_def.kind!r} is already registered")
    _REGISTRY[kind_def.kind] = kind_def


def get_kind(kind: str) -> ReviewKind | None:
    return _REGISTRY.get(kind)


def get_action(kind: str, action_id: str) -> ReviewAction | None:
    kind_def = _REGISTRY.get(kind)
    if not kind_def:
        return None
    return next((a for a in kind_def.actions if a.id == action_id), None)


def all_kinds() -> list[ReviewKind]:
    return list(_REGISTRY.values())
