"""Importing this package registers every automation's review kinds (see
registry.py) as a side effect - main.py imports it once at startup. Add a
new automation module here so it actually gets registered.
"""
from app.automations import bounce_handling, business_card, dedupe, departure, followup_queue, returned_copy  # noqa: F401
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, all_kinds, get_action, get_kind, register

__all__ = [
    "ExtraField",
    "ReviewAction",
    "ReviewKind",
    "all_kinds",
    "get_action",
    "get_kind",
    "register",
]
