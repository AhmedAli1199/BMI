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

RELIABILITY: every real provider call goes through _with_retries() (retry
with exponential backoff on a transient/rate-limit error specifically -
never on a genuine bad-request/auth error, which retrying can't fix) and
_throttle() (a minimum gap enforced between successive calls, process-
wide). Both exist because a scan loop firing 20+ classification calls
back to back was observed in production tripping Gemini's per-minute
rate limit, which - before this - silently fell through to "couldn't
classify, assume the safe/permissive default" for every one of those
calls. Both are tunable at runtime (Automations Settings, "LLM usage &
cost" group) via app.automations.runtime_settings, same as every other
scan tunable in this codebase.

COST TRACKING: every real provider call (success or failure) is logged as
one app.models.LlmUsageEvent row - tokens used and an estimated dollar
cost computed from the (also runtime-editable) price-per-1M-tokens
settings in effect at call time. See /api/automations/llm-usage for the
aggregated dashboard. Logging failures are caught and swallowed (a usage-
tracking bug must never break the underlying automation call).
"""
from __future__ import annotations

import json
import logging
import time

from app.core.config import settings

logger = logging.getLogger("app.automations.llm")

_openai_client = None
_openai_client_checked = False

_gemini_client = None
_gemini_client_checked = False

# Process-wide "when did the last real provider call start" - deliberately
# a plain module global, not per-thread: every automation scan in this
# codebase runs synchronously in a single worker process (see
# scheduler.py), so a simple global is enough to spread out a burst of
# calls from one scan loop without needing real concurrency control.
_last_call_started_at = 0.0


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


def _runtime_llm_settings() -> dict:
    """One quick DB read per top-level call (extract_json/draft_text/
    extract_json_from_image) for the reliability + pricing knobs - see
    app.automations.runtime_settings' docstring for why a fresh read
    each time (rather than a process-wide cache) is the deliberate
    choice here too: a setting changed in the UI should take effect on
    the very next call, not after some cache invalidation event. Falls
    back to the code defaults on any DB hiccup so a usage-tracking/
    settings problem can never block the underlying automation call."""
    try:
        from app.automations import runtime_settings
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            return {
                "max_retries": runtime_settings.get_int(db, "llm_max_retries"),
                "retry_base_delay": runtime_settings.get_float(db, "llm_retry_base_delay_seconds"),
                "min_interval": runtime_settings.get_float(db, "llm_call_min_interval_seconds"),
                "cost_gemini": (
                    runtime_settings.get_float(db, "llm_cost_gemini_input_per_1m"),
                    runtime_settings.get_float(db, "llm_cost_gemini_output_per_1m"),
                ),
                "cost_openai": (
                    runtime_settings.get_float(db, "llm_cost_openai_input_per_1m"),
                    runtime_settings.get_float(db, "llm_cost_openai_output_per_1m"),
                ),
            }
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to read LLM runtime settings - using code defaults for this call.")
        return {
            "max_retries": settings.llm_max_retries,
            "retry_base_delay": settings.llm_retry_base_delay_seconds,
            "min_interval": settings.llm_call_min_interval_seconds,
            "cost_gemini": (settings.llm_cost_gemini_input_per_1m, settings.llm_cost_gemini_output_per_1m),
            "cost_openai": (settings.llm_cost_openai_input_per_1m, settings.llm_cost_openai_output_per_1m),
        }


def _is_transient_error(exc: Exception) -> bool:
    """True for a rate-limit/overload/timeout-shaped error worth retrying -
    False for anything else (a bad API key, a malformed request, a content
    policy block), which retrying would only waste time on. Deliberately
    string/name-sniffed rather than importing each SDK's specific
    exception classes (openai.RateLimitError, google.genai.errors.
    ClientError, ...) - both SDKs' own class names and HTTP status text
    consistently surface one of these signatures, and this avoids a hard
    dependency on either SDK's exact exception hierarchy, which has
    changed across versions before."""
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    signals = ("ratelimit", "rate limit", "resourceexhausted", "resource exhausted",
               "quota", "429", "503", "overloaded", "timeout", "timed out",
               "unavailable", "internalservererror", "internal error")
    return any(s in name or s in text for s in signals)


def _with_retries(call_fn, *, max_retries: int, base_delay: float, log_label: str):
    """Calls call_fn() (a zero-arg callable making the real provider
    request), retrying with exponential backoff (base_delay, 2x, 4x, ...)
    on a transient error specifically. Re-raises the final exception on
    exhaustion or on a non-transient error - the caller's existing
    `except Exception` around this still catches it and falls back to
    OpenAI (or returns None) exactly as before this was added; retries
    only change how many attempts happen before that."""
    attempt = 0
    while True:
        try:
            return call_fn()
        except Exception as exc:
            if attempt >= max_retries or not _is_transient_error(exc):
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "%s: transient error (%s) - retrying in %.1fs (attempt %d/%d)",
                log_label, exc.__class__.__name__, delay, attempt + 1, max_retries,
            )
            time.sleep(delay)
            attempt += 1


def _gemini_retry_budget(cfg: dict) -> int:
    """Gemini gets its full configured retry budget only when it's the
    ONLY provider in play - if OpenAI is also configured, Gemini is
    always going to fall back to it on failure anyway, so retrying
    Gemini first (each attempt backing off 2x/4x/8x...) just delays
    reaching the provider that would have answered immediately. This is
    what turned a handful of Gemini rate-limit errors into whole scan
    runs taking 10+ minutes and blowing past the request timeout - see
    this module's docstring."""
    return 0 if _get_openai_client() is not None else cfg["max_retries"]


def _throttle(min_interval: float) -> None:
    """Blocks just long enough that this call starts no sooner than
    min_interval seconds after the last one did - spreads a scan loop's
    burst of calls out over real wall-clock time instead of firing them
    back to back, which is what was tripping a provider's per-minute rate
    limit in production (see this module's docstring)."""
    global _last_call_started_at
    if min_interval <= 0:
        return
    now = time.monotonic()
    wait = min_interval - (now - _last_call_started_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_started_at = time.monotonic()


def _log_usage(
    *, provider: str, model: str, call_type: str, purpose: str,
    prompt_tokens: int, completion_tokens: int, cost_rates: tuple[float, float],
    success: bool, error_type: str | None,
) -> None:
    """Writes one LlmUsageEvent row via its own short-lived session -
    deliberately independent of whatever DB session/transaction the
    caller (a scan loop) is mid-way through, so a usage record for a call
    that already happened and already cost real money can never be
    rolled back by an unrelated failure elsewhere in that scan's
    transaction (see app/models/llm_usage.py's docstring). Any failure
    here is logged and swallowed - cost tracking must never be the
    reason an automation call fails."""
    try:
        from app.db.session import SessionLocal
        from app.models import LlmUsageEvent
        input_rate, output_rate = cost_rates
        cost = (prompt_tokens / 1_000_000) * input_rate + (completion_tokens / 1_000_000) * output_rate
        db = SessionLocal()
        try:
            db.add(LlmUsageEvent(
                provider=provider, model=model, call_type=call_type, purpose=purpose,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=cost, success=success, error_type=error_type,
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to record LLM usage event (provider=%s purpose=%s) - cost dashboard will undercount this call.", provider, purpose)


def draft_text(system_prompt: str, user_prompt: str, *, max_tokens: int = 400, purpose: str = "unspecified") -> str | None:
    """Returns the model's plain-text reply, or None if neither provider
    is configured or both calls fail - callers must have a non-AI
    fallback ready and use it on None, never propagate an exception up
    into a scheduled job (see scheduler.py's _run_guarded, which would
    otherwise treat a single bad AI call as reason to log the whole job
    as failed). Tries Gemini first (if configured), falls back to OpenAI
    on a Gemini failure or if Gemini isn't configured at all.

    `purpose` is a short free-form label (e.g. "followup_queue.draft") -
    shown on the LLM usage/cost dashboard to break spend down by feature."""
    cfg = _runtime_llm_settings()
    if _get_gemini_client() is not None:
        text = _draft_text_gemini(system_prompt, user_prompt, max_tokens=max_tokens, purpose=purpose, cfg=cfg)
        if text:
            return text
    return _draft_text_openai(system_prompt, user_prompt, max_tokens=max_tokens, purpose=purpose, cfg=cfg)


def _draft_text_openai(system_prompt: str, user_prompt: str, *, max_tokens: int, purpose: str, cfg: dict) -> str | None:
    client = _get_openai_client()
    if client is None:
        return None
    _throttle(cfg["min_interval"])
    try:
        response = _with_retries(
            lambda: client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=max_tokens,
                temperature=0.4,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            ),
            max_retries=cfg["max_retries"], base_delay=cfg["retry_base_delay"], log_label="OpenAI draft_text",
        )
        usage = getattr(response, "usage", None)
        _log_usage(
            provider="openai", model=settings.openai_model, call_type="text", purpose=purpose,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0, completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cost_rates=cfg["cost_openai"], success=True, error_type=None,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception as exc:
        logger.exception("OpenAI draft_text call failed - falling back to templated text.")
        _log_usage(
            provider="openai", model=settings.openai_model, call_type="text", purpose=purpose,
            prompt_tokens=0, completion_tokens=0, cost_rates=cfg["cost_openai"], success=False, error_type=exc.__class__.__name__,
        )
        return None


def _draft_text_gemini(system_prompt: str, user_prompt: str, *, max_tokens: int, purpose: str, cfg: dict) -> str | None:
    client = _get_gemini_client()
    if client is None:
        return None
    _throttle(cfg["min_interval"])
    try:
        from google.genai import types
        response = _with_retries(
            lambda: client.models.generate_content(
                model=settings.gemini_text_model,
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=0.4,
                ),
            ),
            max_retries=_gemini_retry_budget(cfg), base_delay=cfg["retry_base_delay"], log_label="Gemini draft_text",
        )
        usage = getattr(response, "usage_metadata", None)
        _log_usage(
            provider="gemini", model=settings.gemini_text_model, call_type="text", purpose=purpose,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0, completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            cost_rates=cfg["cost_gemini"], success=True, error_type=None,
        )
        if not response.candidates:
            logger.warning("Gemini draft_text: no candidates returned - falling back to OpenAI.")
            return None
        text = (response.text or "").strip()
        return text or None
    except Exception as exc:
        logger.exception("Gemini draft_text call failed (model=%s) - falling back to OpenAI.", settings.gemini_text_model)
        _log_usage(
            provider="gemini", model=settings.gemini_text_model, call_type="text", purpose=purpose,
            prompt_tokens=0, completion_tokens=0, cost_rates=cfg["cost_gemini"], success=False, error_type=exc.__class__.__name__,
        )
        return None


def _parse_json_lenient(text: str) -> object | None:
    """Every extract_json*/vision call routes its raw response text through
    this before giving up on it. Gemini in particular (less often OpenAI)
    sometimes wraps valid JSON in a markdown code fence, or emits a
    literal newline/control character inside a string value (e.g. a
    multi-line address pulled out of an email signature) - technically
    invalid per strict JSON, but a value Python's own json module parses
    fine with strict=False. Treating either as a hard parse failure means
    burning a whole extra provider round-trip for no reason (a Gemini
    parse failure here falls back to OpenAI - see extract_json's
    docstring), so this tries progressively looser interpretations before
    returning None to the caller as a genuine "couldn't get JSON back"."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
    if not text:
        return None
    for strict in (True, False):
        try:
            return json.loads(text, strict=strict)
        except json.JSONDecodeError:
            continue
    # Last resort: the JSON object/array is embedded in surrounding prose
    # or trailing junk - grab the outermost matching span and retry.
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start, end = text.find(start_char), text.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1], strict=False)
            except json.JSONDecodeError:
                continue
    return None


def extract_json(system_prompt: str, user_prompt: str, *, max_tokens: int = 400, purpose: str = "unspecified") -> dict | None:
    """Same idea as extract_json_from_image() but for plain text - used by
    the bounce/OOO mailbox scan (bounce_handling.py) to classify a message
    it couldn't confidently place with cheap heuristics alone (see
    mail_parsing.py's looks_like_bounce/looks_like_ooo), and to pull a
    named replacement contact out of an out-of-office reply's body text.
    Returns None on any failure - callers must queue the item for manual
    review rather than guess when this comes back empty, same fail-soft
    contract as every other AI helper here. Tries Gemini first (if
    configured), falls back to OpenAI otherwise.

    `purpose` is a short free-form label - see draft_text()'s docstring."""
    cfg = _runtime_llm_settings()
    if _get_gemini_client() is not None:
        result = _extract_json_gemini(system_prompt, user_prompt, max_tokens=max_tokens, purpose=purpose, cfg=cfg)
        if result is not None:
            return result
    return _extract_json_openai(system_prompt, user_prompt, max_tokens=max_tokens, purpose=purpose, cfg=cfg)


def _extract_json_openai(system_prompt: str, user_prompt: str, *, max_tokens: int, purpose: str, cfg: dict) -> dict | None:
    client = _get_openai_client()
    if client is None:
        return None
    _throttle(cfg["min_interval"])
    try:
        response = _with_retries(
            lambda: client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            ),
            max_retries=cfg["max_retries"], base_delay=cfg["retry_base_delay"], log_label="OpenAI extract_json",
        )
        usage = getattr(response, "usage", None)
        _log_usage(
            provider="openai", model=settings.openai_model, call_type="json", purpose=purpose,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0, completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cost_rates=cfg["cost_openai"], success=True, error_type=None,
        )
        text = (response.choices[0].message.content or "").strip()
        return _parse_json_lenient(text) if text else None
    except Exception as exc:
        logger.exception("OpenAI extract_json call failed.")
        _log_usage(
            provider="openai", model=settings.openai_model, call_type="json", purpose=purpose,
            prompt_tokens=0, completion_tokens=0, cost_rates=cfg["cost_openai"], success=False, error_type=exc.__class__.__name__,
        )
        return None


def _extract_json_gemini(system_prompt: str, user_prompt: str, *, max_tokens: int, purpose: str, cfg: dict) -> dict | None:
    client = _get_gemini_client()
    if client is None:
        return None
    _throttle(cfg["min_interval"])
    try:
        from google.genai import types
        response = _with_retries(
            lambda: client.models.generate_content(
                model=settings.gemini_text_model,
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    max_output_tokens=max_tokens,
                    temperature=0.1,
                ),
            ),
            max_retries=_gemini_retry_budget(cfg), base_delay=cfg["retry_base_delay"], log_label="Gemini extract_json",
        )
        usage = getattr(response, "usage_metadata", None)
        _log_usage(
            provider="gemini", model=settings.gemini_text_model, call_type="json", purpose=purpose,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0, completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            cost_rates=cfg["cost_gemini"], success=True, error_type=None,
        )
        if not response.candidates:
            logger.warning("Gemini extract_json: no candidates returned - falling back to OpenAI.")
            return None
        text = (response.text or "").strip()
        return _parse_json_lenient(text) if text else None
    except Exception as exc:
        logger.exception("Gemini extract_json call failed (model=%s) - falling back to OpenAI.", settings.gemini_text_model)
        _log_usage(
            provider="gemini", model=settings.gemini_text_model, call_type="json", purpose=purpose,
            prompt_tokens=0, completion_tokens=0, cost_rates=cfg["cost_gemini"], success=False, error_type=exc.__class__.__name__,
        )
        return None


def extract_json_from_image(
    system_prompt: str, image_data_url: str, *, max_tokens: int = 1000, purpose: str = "unspecified"
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
    uploaded file bytes. `purpose` is a short free-form label - see
    draft_text()'s docstring.
    """
    cfg = _runtime_llm_settings()
    if _get_gemini_client() is not None:
        result = _extract_json_from_image_gemini(system_prompt, image_data_url, max_tokens=max_tokens, purpose=purpose, cfg=cfg)
        if result is not None:
            return result
    return _extract_json_from_image_openai(system_prompt, image_data_url, max_tokens=max_tokens, purpose=purpose, cfg=cfg)


def _extract_json_from_image_openai(
    system_prompt: str, image_data_url: str, *, max_tokens: int, purpose: str, cfg: dict
) -> dict | list | None:
    client = _get_openai_client()
    if client is None:
        return None
    _throttle(cfg["min_interval"])
    try:
        response = _with_retries(
            lambda: client.chat.completions.create(
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
            ),
            max_retries=cfg["max_retries"], base_delay=cfg["retry_base_delay"], log_label="OpenAI extract_json_from_image",
        )
        usage = getattr(response, "usage", None)
        _log_usage(
            provider="openai", model=settings.openai_model, call_type="vision", purpose=purpose,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0, completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cost_rates=cfg["cost_openai"], success=True, error_type=None,
        )
        text = (response.choices[0].message.content or "").strip()
        return _parse_json_lenient(text) if text else None
    except Exception as exc:
        logger.exception("OpenAI extract_json_from_image call failed.")
        _log_usage(
            provider="openai", model=settings.openai_model, call_type="vision", purpose=purpose,
            prompt_tokens=0, completion_tokens=0, cost_rates=cfg["cost_openai"], success=False, error_type=exc.__class__.__name__,
        )
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
    system_prompt: str, image_data_url: str, *, max_tokens: int, purpose: str, cfg: dict
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
    _throttle(cfg["min_interval"])
    try:
        from google.genai import types
        mime_type, image_bytes = _data_url_to_bytes(image_data_url)
        response = _with_retries(
            lambda: client.models.generate_content(
                model=settings.gemini_vision_model,
                contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    max_output_tokens=max_tokens,
                    temperature=0.1,
                ),
            ),
            max_retries=_gemini_retry_budget(cfg), base_delay=cfg["retry_base_delay"], log_label="Gemini extract_json_from_image",
        )
        usage = getattr(response, "usage_metadata", None)
        _log_usage(
            provider="gemini", model=settings.gemini_vision_model, call_type="vision", purpose=purpose,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0, completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            cost_rates=cfg["cost_gemini"], success=True, error_type=None,
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
        return _parse_json_lenient(text)
    except Exception as exc:
        logger.exception(
            "Gemini extract_json_from_image call failed (model=%s) - falling back to OpenAI. Check "
            "GEMINI_API_KEY validity, gemini_vision_model, and quota/billing on that key's project.",
            settings.gemini_vision_model,
        )
        _log_usage(
            provider="gemini", model=settings.gemini_vision_model, call_type="vision", purpose=purpose,
            prompt_tokens=0, completion_tokens=0, cost_rates=cfg["cost_gemini"], success=False, error_type=exc.__class__.__name__,
        )
        return None
