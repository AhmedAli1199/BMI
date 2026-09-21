"""Thin AI wrapper, used by the Follow-up Engine (followup_queue.py) to
draft follow-up text and by the vision-based intake automations
(business_card.py, returned_copy.py, via vision_intake.py) to read a
photographed card or mailing label - written generically enough for any
later automation to reuse without its own client-setup code.

Two independent providers, not one: draft_text()/extract_json() (plain
text) always go through OpenAI. extract_json_from_image() (vision) goes
through whichever provider `settings.vision_provider` selects - "openai"
(default) or "gemini" - so switching just the vision path to Gemini (e.g.
once a client-provided key arrives) never touches the text-drafting path.
See is_configured() vs is_vision_configured() below.

WHERE TO PUT THE API KEYS: OPENAI_API_KEY always; GEMINI_API_KEY (and
optionally VISION_PROVIDER=gemini to actually switch vision over to it)
only if using Gemini for vision - set wherever this backend runs (its
.env file locally, or the environment-variable panel in Render/Dokploy in
production). Nothing else needs to change; this module reads settings at
call time, not import time, so adding a key and restarting the container
is the entire integration step for either provider.

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

_gemini_client = None
_gemini_client_checked = False


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


def _get_gemini_client():
    """Lazily constructs the Gemini client, same "never fail at import
    time" contract as _get_client() above."""
    global _gemini_client, _gemini_client_checked
    if _gemini_client_checked:
        return _gemini_client
    _gemini_client_checked = True
    if not settings.gemini_api_key:
        logger.info("GEMINI_API_KEY not set - Gemini vision disabled.")
        return None
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    except Exception:
        logger.exception("Failed to construct the Gemini client - Gemini vision disabled for this run.")
        _gemini_client = None
    return _gemini_client


def is_vision_configured() -> bool:
    """Whether image reading (business card / returned copy) is available
    right now, under whichever provider is currently selected - callers
    use this instead of is_configured() before an extract_json_from_image
    call, since the two providers can be configured independently (e.g.
    an OpenAI text key present but no Gemini key yet, or vice versa)."""
    if settings.vision_provider == "gemini":
        return _get_gemini_client() is not None
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

    Routes to OpenAI or Gemini per `settings.vision_provider` - same
    signature and same fail-soft contract either way, so callers never
    need to know which provider actually served the request.

    `image_data_url` is a full data: URL (e.g. "data:image/jpeg;base64,...")
    - see vision_intake.py's encode_image_data_url() for building one from
    uploaded file bytes.
    """
    if settings.vision_provider == "gemini":
        return _extract_json_from_image_gemini(system_prompt, image_data_url, max_tokens=max_tokens)
    return _extract_json_from_image_openai(system_prompt, image_data_url, max_tokens=max_tokens)


def _extract_json_from_image_openai(
    system_prompt: str, image_data_url: str, *, max_tokens: int = 1000
) -> dict | list | None:
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


def _data_url_to_bytes(data_url: str) -> tuple[str, bytes]:
    """"data:image/jpeg;base64,..." -> (mime_type, raw_bytes) - Gemini's
    SDK wants raw bytes + a mime type, not a data URL the way OpenAI's
    chat API does."""
    import base64
    header, _, b64_data = data_url.partition(",")
    mime_type = header.split(";")[0].removeprefix("data:") or "image/jpeg"
    return mime_type, base64.b64decode(b64_data)


def _extract_json_from_image_gemini(
    system_prompt: str, image_data_url: str, *, max_tokens: int = 1000
) -> dict | list | None:
    """Untested against a live key as of this writing (no Gemini key
    configured in this environment yet) - follows the current google-genai
    SDK's documented shape (Client.models.generate_content with a
    types.Part.from_bytes image and response_mime_type="application/json"
    in GenerateContentConfig). Smoke-test this against a real photo the
    first time a real GEMINI_API_KEY is set, same as any other untested
    integration path."""
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        from google.genai import types
        mime_type, image_bytes = _data_url_to_bytes(image_data_url)
        response = client.models.generate_content(
            model=settings.gemini_vision_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                system_prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=max_tokens,
                temperature=0.1,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            return None
        import json
        return json.loads(text)
    except Exception:
        logger.exception("Gemini extract_json_from_image call failed.")
        return None
