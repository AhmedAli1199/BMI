"""The registry every app-wide preference is declared in, so the Settings
page (and any code that needs to *read* a preference, like the dashboard)
never hardcodes a preference's label, description, or choices - it all
renders/behaves entirely from what's registered here. Same plug-in shape as
app/automations/registry.py, deliberately: adding a new setting later means
adding one PreferenceDef below, nothing in the frontend.

Each user's actual choices live in users.preferences, a sparse JSONB dict
of {key: value}. A key absent from that dict means "use this def's
default" - so a brand-new preference silently applies its default to
every existing user instead of needing a backfill migration.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreferenceOption:
    value: str
    label: str
    description: str


@dataclass(frozen=True)
class PreferenceDef:
    key: str
    label: str
    description: str
    group: str  # section heading on the Settings page
    options: list[PreferenceOption]
    default: str


PREFERENCE_DEFS: list[PreferenceDef] = [
    PreferenceDef(
        key="recent_activity_sort",
        label="“Recently Active” sort",
        description="What counts as “active” on your dashboard's Recently Active cards.",
        group="Dashboard",
        options=[
            PreferenceOption(
                value="record_edit",
                label="Last record edit",
                description="Shows a record as soon as any of its details change.",
            ),
            PreferenceOption(
                value="engagement",
                label="Last note or call",
                description="Shows a record only after a note, call, or meeting is logged.",
            ),
        ],
        default="record_edit",
    ),
    PreferenceDef(
        key="email_notifications",
        label="Email me notifications",
        description="Reminders and other notifications always appear under the bell; this also emails them to you from the automation mailbox.",
        group="Notifications",
        options=[
            PreferenceOption(value="on", label="On", description="Email each notification as well."),
            PreferenceOption(value="off", label="Off", description="In-app only."),
        ],
        default="on",
    ),
    PreferenceDef(
        key="calendar_recording",
        label="Record my meetings",
        description="What the notetaker does with meetings on your connected calendar that have a Meet or Teams link.",
        group="Call notes",
        options=[
            PreferenceOption(value="auto", label="Join automatically", description="BMI Notetaker joins and takes notes - you can still skip any meeting."),
            PreferenceOption(value="remind", label="Just remind me", description="A reminder before each meeting, with a button to send the notetaker."),
            PreferenceOption(value="off", label="Off", description="Nothing happens unless you send the notetaker yourself."),
        ],
        default="auto",
    ),
    PreferenceDef(
        key="brain_tips",
        label="Tips from the Brain",
        description="Now and then the Brain points out something worth doing on the page you're on - a confirmation not sent yet, a deadline coming up. One at a time, and you can dismiss each.",
        group="The Brain",
        options=[
            PreferenceOption(value="on", label="On", description="Show a tip when there's something useful."),
            PreferenceOption(value="off", label="Off", description="No tips."),
        ],
        default="on",
    ),
    PreferenceDef(
        key="brain_celebrations",
        label="Small celebrations",
        description="A quick cheer from the Brain when you confirm a booking, send a confirmation or clear your Review Queue.",
        group="The Brain",
        options=[
            PreferenceOption(value="on", label="On", description="Show them."),
            PreferenceOption(value="off", label="Off", description="Just the usual message."),
        ],
        default="on",
    ),
]

_BY_KEY: dict[str, PreferenceDef] = {p.key: p for p in PREFERENCE_DEFS}


def get_def(key: str) -> PreferenceDef | None:
    return _BY_KEY.get(key)


def default_preferences() -> dict[str, str]:
    return {p.key: p.default for p in PREFERENCE_DEFS}


def resolve(stored: dict) -> dict[str, str]:
    """Merge a user's stored (possibly sparse, possibly stale-keyed)
    preferences dict over the registry's current defaults - so a
    preference removed from the registry silently disappears instead of
    leaking a dead key, and a new one silently appears with its default."""
    resolved = default_preferences()
    for key, value in (stored or {}).items():
        pref_def = _BY_KEY.get(key)
        if pref_def and any(o.value == value for o in pref_def.options):
            resolved[key] = value
    return resolved
