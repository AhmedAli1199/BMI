"""SALES-028 (weekly management summary & alerts): the two things the
automation itself has to remember - which behind-last-cycle alerts it has
already fired (so the same edition isn't alerted every day), and each
week's brief (so leadership can look back across cycles). Every figure in
both comes from the order register (see app/sales/analytics.py); these
tables hold the automation's own output, never a second copy of the data.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class ManagementAlert(Base, UUIDPk):
    __tablename__ = "management_alerts"

    subject_type: Mapped[str] = mapped_column(String(20), nullable=False, default="edition")
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    subject_label: Mapped[str] = mapped_column(String(200), nullable=False)
    comparison_label: Mapped[str | None] = mapped_column(String(200))
    prior_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    current_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    gap: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    gap_pct: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # [{"type": "edition", "id": "...", "label": "..."}] - what to open to see the records behind it.
    records_ref: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class WeeklySummary(Base, UUIDPk):
    __tablename__ = "weekly_summaries"

    week_of: Mapped[date] = mapped_column(Date, nullable=False, unique=True)  # the Monday the brief was written for
    brief_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    # [{"key", "title", "paragraphs": [str], "bullets": [{"text", "href"}]}] - the same content as the
    # markdown, structured so the UI can render it without parsing text.
    sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metrics_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # "ai" = the headline paragraph was written by the model (and passed the numbers check);
    # "template" = fully templated, either because no model is configured or its text was rejected.
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="template")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
