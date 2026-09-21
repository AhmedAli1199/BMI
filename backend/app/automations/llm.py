"""Thin AI wrapper, used by the Follow-up Engine (followup_queue.py) and
SALES-012 (signal_triggers.py) to draft follow-up text, and by the
vision-based intake automations (business_card.py, returned_copy.py, via
vision_intake.py) to read a photographed card or mailing label - written
generically enough for any later automation to reuse without its own
client-setup code.

One provider preference, applied uniformly to text AND vision: if
GEMINI_API_KEY is set, every call here goes through Gemini; if it isn't
(or Gemini's own call fails), it falls back to OpenAI. No separate
"vision provider" switch to keep in sync with a "text provider" switch -
setting GEMINI_API_KEY is the entire migration step once BMI's own key
arrives, and unsetting it (or the key going bad) drops back to OpenAI
automatically rather than breaking every automation that calls this
module.

WHERE TO PUT THE API KEYS: GEMINI_API_KEY to prefer Gemini; OPENAI_API_KEY
as the fallback (and the only thing needed if not using Gemini at all) -
set wherever this backend runs (its .env file locally, or the
environment-variable panel in Render/Dokploy in production). Nothing else
needs to change; this module reads settings at call time, not import
time, so adding/removing a key and restarting the container is the entire
integration step either way.

Deliberately fails soft, not loud: every caller in this codebase treats
"neither provider produced a result" as "no AI draft available this
time," never as a reason to crash the scan job or drop the underlying
automation opportunity - see draft_text()'s docstring.
"""
from __future__ import annotations

import json
import logging

from app.core.config import settings

logger = logging.getLogger("app.automations.llm")

_openai_client = None
_openai_client_checked = False

_gemini_client = None
_gemini_client_checked = False


def _get_openai_client():
    """Lazily constructs the OpenAI client on first real use, not at
    import time - so importing this module (e.g. transitively, via
    app.automations.__init__) never fails or does network/env work just
    because openai_api_key happens to be unset in this environment."""
    global _openai_client, _openai_client_checked
    if _openai_client_checked:
        return _openai_client
    _openai_client_checked = True
    if not settings.openai_api_key:
        logger.info("OPENAI_API_KEY not set - OpenAI fallback unavailable.")
        return None
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    except Exception:
        logger.exception("Failed to construct the OpenAI client.")
        _openai_client = None
    return _openai_client


def _get_gemini_client():
    """Lazily constructs the Gemini client, same "never fail at import
    time" contract as _get_openai_client() above."""
    global _gemini_client, _gemini_client_checked
    if _gemini_client_checked:
        return _gemini_client
    _gemini_client_checked = True
    if not settings.gemini_api_key:
        return None
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    except Exception:
        logger.exception("Failed to construct the Gemini client - falling back to OpenAI.")
        _gemini_client = None
    return _gemini_client


def is_configured() -> bool:
    """Whether a real AI draft is available right now, under whichever
    provider will actually serve it - callers use this to decide whether
    to label a draft "AI-drafted" vs "templated" in the review queue, not
    to decide whether to call draft_text() (that's always safe to call
    either way)."""
    return _get_gemini_client() is not None or _get_openai_client() is not None


# Vision used to have its own separate is_vision_configured() when it had
# its own separate provider switch - now the same preference (Gemini,
# falling back to OpenAI) applies everywhere, so this is just an alias
# kept for callers (business_card.py, returned_copy.py) that already use
# the vision-specific name for clarity at their call sites.
is_vision_configured = is_configured


def draft_text(system_prompt: str, user_prompt: str, *, max_tokens: int = 400) -> str | None:
    """Returns the model's plain-text reply, or None if neither provider
    is configured or both calls fail - callers must have a non-AI
    fallback ready and use it on None, never propagate an exception up
    into a scheduled job (see scheduler.py's _run_guarded, which would
    otherwise treat a single bad AI call as reason to log the whole job
    as failed). Tries Gemini first (if configured), falls back to OpenAI
    on a Gemini failure or if Gemini isn't configured at all."""
    if _get_gemini_client() is not None:
        text = _draft_text_gemini(system_prompt, user_prompt, max_tokens=max_tokens)
        if text:
            return text
    return _draft_text_openai(system_prompt, user_prompt, max_tokens=max_tokens)


def _draft_text_openai(system_prompt: str, user_prompt: str, *, max_tokens: int) -> str | None:
    client = _get_openai_client()
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


def _draft_text_gemini(system_prompt: str, user_prompt: str, *, max_tokens: int) -> str | None:
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=settings.gemini_text_model,
            contents=[user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=0.4,
            ),
        )
        if not response.candidates:
            logger.warning("Gemini draft_text: no candidates returned - falling back to OpenAI.")
            return None
        text = (response.text or "").strip()
        return text or None
    except Exception:
        logger.exception("Gemini draft_text call failed (model=%s) - falling back to OpenAI.", settings.gemini_text_model)
        return None


def extract_json(system_prompt: str, user_prompt: str, *, max_tokens: int = 400) -> dict | None:
    """Same idea as extract_json_from_image() but for plain text - used by
    the bounce/OOO mailbox scan (bounce_handling.py) to classify a message
    it couldn't confidently place with cheap heuristics alone (see
    mail_parsing.py's looks_like_bounce/looks_like_ooo), and to pull a
    named replacement contact out of an out-of-office reply's body text.
    Returns None on any failure - callers must queue the item for manual
    review rather than guess when this comes back empty, same fail-soft
    contract as every other AI helper here. Tries Gemini first (if
    configured), falls back to OpenAI otherwise."""
    if _get_gemini_client() is not None:
        result = _extract_json_gemini(system_prompt, user_prompt, max_tokens=max_tokens)
        if result is not None:
            return result
    return _extract_json_openai(system_prompt, user_prompt, max_tokens=max_tokens)


def _extract_json_openai(system_prompt: str, user_prompt: str, *, max_tokens: int) -> dict | None:
    client = _get_openai_client()
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
        return json.loads(text) if text else None
    except Exception:
        logger.exception("OpenAI extract_json call failed.")
        return None


def _extract_json_gemini(system_prompt: str, user_prompt: str, *, max_tokens: int) -> dict | None:
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=settings.gemini_text_model,
            contents=[user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                max_output_tokens=max_tokens,
                temperature=0.1,
            ),
        )
        if not response.candidates:
            logger.warning("Gemini extract_json: no candidates returned - falling back to OpenAI.")
            return None
        text = (response.text or "").strip()
        return json.loads(text) if text else None
    except Exception:
        logger.exception("Gemini extract_json call failed (model=%s) - falling back to OpenAI.", settings.gemini_text_model)
        return None


def extract_json_from_image(
    system_prompt: str, image_data_url: str, *, max_tokens: int = 1000
) -> dict | list | None:
    """Vision extraction: sends one image + an instruction to return
    structured JSON, and returns it parsed - or None if neither provider
    is configured, both calls fail, or neither reply is valid JSON. Used
    by the business-card and returned-copy intake automations, which must
    always have a "couldn't read this, flag for manual review" path
    rather than guessing - see their modules for how they handle a None
    return. Tries Gemini first (if configured), falls back to OpenAI on a
    Gemini failure or if Gemini isn't configured at all.

    `image_data_url` is a full data: URL (e.g. "data:image/jpeg;base64,...")
    - see vision_intake.py's encode_image_data_url() for building one from
    uploaded file bytes.
    """
    if _get_gemini_client() is not None:
        result = _extract_json_from_image_gemini(system_prompt, image_data_url, max_tokens=max_tokens)
        if result is not None:
            return result
    return _extract_json_from_image_openai(system_prompt, image_data_url, max_tokens=max_tokens)


def _extract_json_from_image_openai(
    system_prompt: str, image_data_url: str, *, max_tokens: int = 1000
) -> dict | list | None:
    client = _get_openai_client()
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
        return json.loads(text) if text else None
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
    """Follows the current google-genai SDK's documented shape
    (Client.models.generate_content with a types.Part.from_bytes image,
    the extraction instructions as system_instruction rather than jammed
    into the user content, and response_mime_type="application/json" in
    GenerateContentConfig).

    Every failure mode here - a bad/expired key, a wrong model name, the
    image tripping Gemini's safety filters, a network error, hitting a
    quota - all land in the same `except Exception`. The distinct log
    lines below exist so the ACTUAL cause is visible in the backend logs;
    the caller falls back to OpenAI regardless of which one it was, so a
    person uploading a photo is never stuck just because Gemini had a bad
    day - see extract_json_from_image()."""
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        from google.genai import types
        mime_type, image_bytes = _data_url_to_bytes(image_data_url)
        response = client.models.generate_content(
            model=settings.gemini_vision_model,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                max_output_tokens=max_tokens,
                temperature=0.1,
            ),
        )
        block_reason = getattr(getattr(response, "prompt_feedback", None), "block_reason", None)
        if block_reason:
            logger.warning("Gemini extract_json_from_image: prompt/image blocked (%s) - falling back to OpenAI.", block_reason)
            return None
        if not response.candidates:
            logger.warning("Gemini extract_json_from_image: no candidates returned - falling back to OpenAI.")
            return None

        text = (response.text or "").strip()
        if not text:
            finish_reason = getattr(response.candidates[0], "finish_reason", None)
            logger.warning("Gemini extract_json_from_image: empty response text (finish_reason=%s) - falling back to OpenAI.", finish_reason)
            return None
        return json.loads(text)
    except Exception:
        logger.exception(
            "Gemini extract_json_from_image call failed (model=%s) - falling back to OpenAI. Check "
            "GEMINI_API_KEY validity, gemini_vision_model, and quota/billing on that key's project.",
            settings.gemini_vision_model,
        )
        return None
