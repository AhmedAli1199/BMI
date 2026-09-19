"""Thin OpenAI wrapper, used by the Follow-up Engine (followup_queue.py)
to draft follow-up text and by the vision-based intake automations
(business_card.py, returned_copy.py, via vision_intake.py) to read a
photographed card or mailing label - written generically enough for any
later automation to reuse without its own client-setup code.

WHERE TO PUT THE API KEY: set the OPENAI_API_KEY environment variable
wherever this backend actually runs (its .env file locally, or the
environment-variable panel in Render/Dokploy in production) - see
app/core/config.py's `openai_api_key` field and .env.example. Nothing else
needs to change; this module reads it from `settings` at call time, not at
import time, so adding the key and restarting the container is the entire
integration step.

Deliberately fails soft, not loud: every caller in this codebase treats a
missing key or an API error as "no AI draft available this time," never as
a reason to crash the scan job or drop the underlying automation
opportunity - see draft_text()'s docstring.
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("app.automations.llm")

_client = None
_client_checked = False


def _get_client():
    """Lazily constructs the OpenAI client on first real use, not at
    import time - so importing this module (e.g. transitively, via
    app.automations.__init__) never fails or does network/env work just
    because openai_api_key happens to be unset in this environment."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True
    if not settings.openai_api_key:
        logger.info("OPENAI_API_KEY not set - AI drafting disabled, callers fall back to templated text.")
        return None
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=settings.openai_api_key)
    except Exception:
        logger.exception("Failed to construct the OpenAI client - AI drafting disabled for this run.")
        _client = None
    return _client


def is_configured() -> bool:
    """Whether a real AI draft is available right now - callers use this to
    decide whether to label a draft "AI-drafted" vs "templated" in the
    review queue, not to decide whether to call draft_text() (that's
    always safe to call either way)."""
    return _get_client() is not None


def draft_text(system_prompt: str, user_prompt: str, *, max_tokens: int = 400) -> str | None:
    """Returns the model's plain-text reply, or None if no key is
    configured or the call fails for any reason (rate limit, network,
    malformed response, ...) - callers must have a non-AI fallback ready
    and use it on None, never propagate the exception up into a scheduled
    job (see scheduler.py's _run_guarded, which would otherwise treat a
    single bad OpenAI call as reason to log the whole job as failed)."""
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=max_tokens,
            temperature=0.4,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        logger.exception("OpenAI draft_text call failed - falling back to templated text.")
        return None


def extract_json(system_prompt: str, user_prompt: str, *, max_tokens: int = 400) -> dict | None:
    """Same idea as extract_json_from_image() but for plain text - used by
    the bounce/OOO mailbox scan (bounce_handling.py) to classify a message
    it couldn't confidently place with cheap heuristics alone (see
    mail_parsing.py's looks_like_bounce/looks_like_ooo), and to pull a
    named replacement contact out of an out-of-office reply's body text.
    Returns None on any failure - callers must queue the item for manual
    review rather than guess when this comes back empty, same fail-soft
    contract as every other AI helper here."""
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=max_tokens,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            return None
        import json
        return json.loads(text)
    except Exception:
        logger.exception("OpenAI extract_json call failed.")
        return None


def extract_json_from_image(
    system_prompt: str, image_data_url: str, *, max_tokens: int = 1000
) -> dict | list | None:
    """Vision extraction: sends one image + an instruction to return
    structured JSON, and returns it parsed - or None if no key is
    configured, the call fails, or the reply isn't valid JSON. Used by the
    business-card and returned-copy intake automations, which must always
    have a "couldn't read this, flag for manual review" path rather than
    guessing - see their modules for how they handle a None return.

    `image_data_url` is a full data: URL (e.g. "data:image/jpeg;base64,...")
    - see vision_intake.py's encode_image_data_url() for building one from
    uploaded file bytes.
    """
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=max_tokens,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            return None
        import json
        return json.loads(text)
    except Exception:
        logger.exception("OpenAI extract_json_from_image call failed.")
        return None
