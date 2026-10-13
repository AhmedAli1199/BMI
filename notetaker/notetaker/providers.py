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


@lru_cache
def get_ai():
    if settings.ai_provider == "fake":
        from notetaker.transcribe.fake import FakeAI
        return FakeAI()
    from notetaker.transcribe.gemini import GeminiAI
    return GeminiAI()
