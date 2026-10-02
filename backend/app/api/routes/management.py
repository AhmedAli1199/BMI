"""Read API for SALES-028: the weekly summaries and the alerts log.
Leadership material, so administrators and data managers only (the same
audience as the Automations Hub)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.automations import require_staff
from app.core.identity import Identity
from app.db.session import get_db
from app.models import ManagementAlert, WeeklySummary

router = APIRouter(prefix="/management", tags=["management"])


class SummaryListItem(BaseModel):
    id: uuid.UUID
    week_of: date
    source: str
    generated_at: datetime
    headline: str


class SummaryOut(SummaryListItem):
    brief_markdown: str
    sections: list[dict]
    metrics_snapshot: dict


class AlertOut(BaseModel):
    id: uuid.UUID
    subject_type: str
    subject_id: uuid.UUID
    subject_label: str
    comparison_label: str | None
    prior_value: float
    current_value: float
    gap: float
    gap_pct: float
    message: str
    records_ref: list[dict]
    fired_at: datetime


def _headline(row: WeeklySummary) -> str:
    return next((s["paragraphs"][0] for s in row.sections if s.get("key") == "headline" and s.get("paragraphs")), "")


@router.get("/summaries", response_model=list[SummaryListItem])
def list_summaries(limit: int = Query(26, ge=1, le=104), db: Session = Depends(get_db), _staff: Identity = Depends(require_staff)) -> list[SummaryListItem]:
    rows = db.scalars(select(WeeklySummary).order_by(WeeklySummary.week_of.desc()).limit(limit)).all()
    return [SummaryListItem(id=r.id, week_of=r.week_of, source=r.source, generated_at=r.generated_at, headline=_headline(r)) for r in rows]


@router.get("/summaries/{summary_id}", response_model=SummaryOut)
def get_summary(summary_id: uuid.UUID, db: Session = Depends(get_db), _staff: Identity = Depends(require_staff)) -> SummaryOut:
    r = db.get(WeeklySummary, summary_id)
    if not r:
        raise HTTPException(status_code=404, detail="No such summary.")
    return SummaryOut(id=r.id, week_of=r.week_of, source=r.source, generated_at=r.generated_at, headline=_headline(r),
                      brief_markdown=r.brief_markdown, sections=r.sections, metrics_snapshot=r.metrics_snapshot)


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _staff: Identity = Depends(require_staff)) -> list[AlertOut]:
    rows = db.scalars(select(ManagementAlert).order_by(ManagementAlert.fired_at.desc()).limit(limit)).all()
    return [AlertOut(id=a.id, subject_type=a.subject_type, subject_id=a.subject_id, subject_label=a.subject_label,
                     comparison_label=a.comparison_label, prior_value=float(a.prior_value), current_value=float(a.current_value),
                     gap=float(a.gap), gap_pct=a.gap_pct, message=a.message, records_ref=a.records_ref, fired_at=a.fired_at) for a in rows]
