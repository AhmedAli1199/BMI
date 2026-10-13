"""All settings come from environment variables, read once at start-up."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", "sqlite:///./notetaker.db"))
    # The address other services use to reach this one (for Attendee's webhooks and transcription calls).
    public_url: str = field(default_factory=lambda: _env("PUBLIC_URL", "http://localhost:8080").rstrip("/"))
    admin_token: str = field(default_factory=lambda: _env("ADMIN_TOKEN"))

    # Meeting bot (Attendee, self-hosted)
    bot_provider: str = field(default_factory=lambda: _env("BOT_PROVIDER", "attendee"))   # attendee | fake
    attendee_url: str = field(default_factory=lambda: _env("ATTENDEE_URL", "http://attendee-app:8000").rstrip("/"))
    attendee_api_key: str = field(default_factory=lambda: _env("ATTENDEE_API_KEY"))
    attendee_webhook_secret: str = field(default_factory=lambda: _env("ATTENDEE_WEBHOOK_SECRET"))
    # How the bot transcribes: "captions" (the meeting's own live captions, free, real names)
    # or "gemini" (Attendee sends each speaker's audio to /internal/transcribe).
    transcription_mode: str = field(default_factory=lambda: _env("TRANSCRIPTION_MODE", "captions"))
    default_bot_name: str = field(default_factory=lambda: _env("DEFAULT_BOT_NAME", "Notetaker"))
    max_concurrent_bots: int = field(default_factory=lambda: int(_env("MAX_CONCURRENT_BOTS", "2")))

    # AI (summaries, and transcription in "gemini" mode)
    ai_provider: str = field(default_factory=lambda: _env("AI_PROVIDER", "gemini"))   # gemini | fake
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _env("GEMINI_MODEL", "gemini-3.6-flash"))
    internal_token: str = field(default_factory=lambda: _env("INTERNAL_TOKEN"))

    # Outgoing webhooks to client apps
    webhook_max_attempts: int = field(default_factory=lambda: int(_env("WEBHOOK_MAX_ATTEMPTS", "12")))
    worker_interval_seconds: float = field(default_factory=lambda: float(_env("WORKER_INTERVAL_SECONDS", "3")))


settings = Settings()
