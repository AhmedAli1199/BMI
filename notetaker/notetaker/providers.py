"""Picks the bot and AI implementations from settings (one place, so tests can swap them)."""
from __future__ import annotations

from functools import lru_cache

from notetaker.config import settings


@lru_cache
def get_bot():
    if settings.bot_provider == "fake":
        from notetaker.bots.fake import FakeBot
        return FakeBot()
    from notetaker.bots.attendee import AttendeeBot
    return AttendeeBot()


@lru_cache(maxsize=64)
def get_ai(api_key: str):
    """The notes writer for one app's own Gemini key (apps never share the server's)."""
    if settings.ai_provider == "fake":
        from notetaker.transcribe.fake import FakeAI
        return FakeAI(api_key)
    from notetaker.transcribe.gemini import GeminiAI
    return GeminiAI(api_key)


def app_ai(client):
    """None when the app hasn't added a Gemini key yet."""
    from notetaker.security import decrypt
    if not client.gemini_key_enc:
        return None
    return get_ai(decrypt(client.gemini_key_enc))
