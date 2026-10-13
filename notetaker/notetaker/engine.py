"""Where the meeting bot's credentials come from.

Normally from /shared/attendee.json, written by the attendee-bootstrap container on every deploy (so
nobody copies keys). ATTENDEE_API_KEY / ATTENDEE_WEBHOOK_SECRET in the environment still win if set -
handy for pointing at an Attendee you run somewhere else.
"""
from __future__ import annotations

import json
import os

from notetaker.config import settings

_cache: dict = {"mtime": None, "data": {}}


def _file() -> dict:
    path = settings.attendee_credentials_file
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    if _cache["mtime"] != mtime:
        try:
            with open(path) as f:
                _cache["data"] = json.load(f)
            _cache["mtime"] = mtime
        except (OSError, ValueError):
            return _cache["data"]
    return _cache["data"]


def api_key() -> str:
    return settings.attendee_api_key or _file().get("api_key", "")


def webhook_secret() -> str:
    return settings.attendee_webhook_secret or _file().get("webhook_secret", "")


def admin_login() -> dict:
    d = _file()
    return {"email": d.get("admin_email"), "password": d.get("admin_password")} if d.get("admin_email") else {}
