"""The agent: Google's agent kit (ADK) running Gemini over the Brain's tools.

Speed and cost choices (docs/ai-hub-plan.md):
- The instructions and tool list are fixed (prompt.static_instruction, registry.adk_tools), so every request
  starts with the same long block and Gemini serves it from its prompt cache.
- Thinking level is set per question (route): Gemini 3 thinks at "high" unless told otherwise, which is slow.
  Help questions and simple lookups use the configured level (low by default).
- One agent per thinking level is built once and reused.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings

_model_override = None   # tests put a scripted model here (set_model)


def set_model(model) -> None:
    """Use this model instead of Gemini (tests). None goes back to Gemini."""
    global _model_override
    _model_override = model
    _agents.cache_clear()


def model_name() -> str:
    return getattr(_model_override, "model", None) or settings.brain_model or settings.gemini_text_model


def configured() -> bool:
    return _model_override is not None or bool(settings.gemini_api_key)


def _model():
    if _model_override is not None:
        return _model_override
    from google.adk.models.google_llm import Gemini
    return Gemini(model=model_name(), client_kwargs={"api_key": settings.gemini_api_key})


@dataclass(frozen=True)
class Route:
    name: str        # help | record | general
    thinking: str    # minimal | low | medium | high


DEEP = re.compile(r"\b(compare|analy[sz]e|explain (all|every)|step by step|work out|calculate|difference between)\b", re.I)
RECORD = re.compile(r"\b(this|my|booking|order|invoice|item|edition)\b.*\b(why|when|where|locked|status|invoiced|sent|due)\b|\b(why|when)\b.*\b(this|booking|invoice)\b", re.I)


def route(question: str, context: dict) -> Route:
    """No extra model call: the page and what was pointed at say most of it."""
    base = settings.brain_thinking or "low"
    if DEEP.search(question or ""):
        return Route("general", "medium" if base in ("minimal", "low") else base)
    if context.get("record") or RECORD.search(question or ""):
        return Route("record", base)
    return Route("help", base)


@lru_cache(maxsize=8)
def _agents(thinking: str):
    from google.adk.agents import LlmAgent
    from google.genai import types

    from app.brain import prompt, registry
    level = {"minimal": types.ThinkingLevel.MINIMAL, "low": types.ThinkingLevel.LOW,
             "medium": types.ThinkingLevel.MEDIUM, "high": types.ThinkingLevel.HIGH}.get(thinking, types.ThinkingLevel.LOW)
    return LlmAgent(
        name="brain", model=_model(), description="BMI Brain's assistant",
        static_instruction=prompt.static_instruction(),
        tools=registry.adk_tools(),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3, max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_level=level)),
    )


def app_for(r: Route):
    from google.adk.apps import App
    cache = None
    if settings.brain_explicit_cache and _model_override is None:
        from google.adk.agents.context_cache_config import ContextCacheConfig
        cache = ContextCacheConfig(min_tokens=4096, ttl_seconds=1800, cache_intervals=20)
    return App(name="bmi_brain", root_agent=_agents(r.thinking), context_cache_config=cache)
