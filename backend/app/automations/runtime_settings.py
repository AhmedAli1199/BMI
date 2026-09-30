"""Resolves one automation setting's *effective* value: a DB override if
one exists (app/models/automation_setting.py, set via the Automations
Settings UI), else the env var default already on app.core.config.settings.
Every automation scan reads its tunables through here instead of `settings`
directly, so a UI edit takes effect on the very next run - no restart, no
redeploy.

Deliberately a fresh DB read per call rather than a process-wide cache:
these are only ever read once or twice per scan run (a handful of times an
hour, at most), so the cost is negligible, and a cache would mean an admin
changing a setting in the UI wouldn't take effect until some invalidation
event - simpler and more predictable to just always read current state.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.automations.settings_registry import get_def
from app.core.config import settings
from app.models import AutomationSetting


def _raw_override(db: Session, key: str):
    row = db.get(AutomationSetting, key)
    return row.value["v"] if row else None


def get_bool(db: Session, key: str) -> bool:
    raw = _raw_override(db, key)
    return bool(raw) if raw is not None else bool(getattr(settings, key))


def get_int(db: Session, key: str) -> int:
    raw = _raw_override(db, key)
    return int(raw) if raw is not None else int(getattr(settings, key))


def get_float(db: Session, key: str) -> float:
    raw = _raw_override(db, key)
    return float(raw) if raw is not None else float(getattr(settings, key))


def get_str(db: Session, key: str) -> str:
    raw = _raw_override(db, key)
    return str(raw) if raw is not None else str(getattr(settings, key))


def get_csv(db: Session, key: str) -> list[str]:
    """A comma-separated setting (a mailbox list) as a clean list - callers
    that need the raw string (to log it, say) should use get_str instead."""
    raw = get_str(db, key)
    return [v.strip() for v in raw.split(",") if v.strip()]


def effective_value(db: Session, key: str):
    """Typed by the setting's own registry definition - what the API/UI
    reads to show "what's actually in effect right now", regardless of
    whether that's the env default or a stored override."""
    setting_def = get_def(key)
    if not setting_def:
        raise KeyError(f"No registered automation setting {key!r}")
    if setting_def.type == "bool":
        return get_bool(db, key)
    if setting_def.type == "int":
        return get_int(db, key)
    if setting_def.type == "float":
        return get_float(db, key)
    return get_str(db, key)  # csv/text - the UI edits/shows this as its raw string


def set_override(db: Session, key: str, value) -> None:
    setting_def = get_def(key)
    if not setting_def:
        raise KeyError(f"No registered automation setting {key!r}")
    # Validate/coerce before ever writing - a bad value from the UI should
    # fail the request, never silently corrupt what a scan reads next run.
    if setting_def.type == "bool":
        value = bool(value)
    elif setting_def.type == "int":
        value = int(value)
        if setting_def.min is not None and value < setting_def.min:
            raise ValueError(f"{setting_def.label} must be at least {setting_def.min}")
        if setting_def.max is not None and value > setting_def.max:
            raise ValueError(f"{setting_def.label} must be at most {setting_def.max}")
    elif setting_def.type == "float":
        value = float(value)
        if setting_def.min is not None and value < setting_def.min:
            raise ValueError(f"{setting_def.label} must be at least {setting_def.min}")
        if setting_def.max is not None and value > setting_def.max:
            raise ValueError(f"{setting_def.label} must be at most {setting_def.max}")
    else:
        value = str(value)

    row = db.get(AutomationSetting, key)
    if row:
        row.value = {"v": value}
    else:
        db.add(AutomationSetting(key=key, value={"v": value}))


def clear_override(db: Session, key: str) -> bool:
    """Removes a stored override, reverting to the env var default. Returns
    False if there was nothing to remove."""
    row = db.get(AutomationSetting, key)
    if not row:
        return False
    db.delete(row)
    return True
