"""One row per real LLM API call made anywhere in the codebase (see
app/automations/llm.py, the single chokepoint every automation's AI call
goes through) - what it cost, whether it succeeded, and which automation
it was for. Exists purely for the cost/usage dashboard
(/api/automations/llm-usage) - nothing here is read by any automation
logic, so a bug in this table can never affect a scan's real behavior.

Written directly from llm.py using its own short-lived session, not the
caller's - an automation's own DB transaction (which may roll back a
savepoint on a bad item, see review_queue.py's bulk actions) should never
be able to erase a usage record for a call that already happened and
already cost real money.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class LlmUsageEvent(Base, UUIDPk):
    __tablename__ = "llm_usage_events"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # "gemini" | "openai"
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    call_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "text" | "json" | "vision"
    # Which automation/module made this call (e.g. "inbound_capture.intent",
    # "bounce_handling.ooo_extraction") - a free-form label the caller
    # passes in, so the usage dashboard can break cost down by feature
    # without this table needing to know what every caller is.
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Computed at call time from the pricing settings then in effect (see
    # runtime_settings' llm_cost_* keys) - a later price change doesn't
    # retroactively rewrite historical rows, same as a real invoice.
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Only set on failure - the exception's class name, e.g.
    # "RateLimitError"/"ResourceExhausted" - enough to spot a rate-limit
    # storm on the dashboard without storing a full traceback.
    error_type: Mapped[str | None] = mapped_column(String(64))
