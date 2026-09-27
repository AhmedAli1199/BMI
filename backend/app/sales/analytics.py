"""Shared calculations over the Sales Order Register, used by both the
/sales API and the SOR automations - kept in one place so "booked", "last
year's equivalent edition" and "not rebooked yet" mean exactly the same
thing on every page and in every automation.

Definitions (also shown as info hints in the UI):
- Booked value: the £ value of orders with status "booked". Cancelled,
  contra (free swap) and moved orders are excluded - a moved order counts
  in the edition it moved to, where it's re-entered.
- Same point last year: last year's editions of the same title, counting
  only orders booked on or before today's date one year ago - the fair
  comparison for an edition that's still selling.
- Equivalent edition: same title, previous year, same name once the year
  is taken out ("Jan 2026" <-> "Jan 2025"); for numbered issues
  ("OBH 105" <-> "OBH 101") the edition in the same position in the
  year's running order.
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SalesEdition, SalesOrder

BOOKED = "booked"


def name_key(name: str) -> str:
    return re.sub(r"\b(19|20)\d{2}\b|\s+|[^a-z0-9]", "", name.lower())


def _running_order(eds: list[SalesEdition]) -> list[SalesEdition]:
    return sorted(eds, key=lambda e: (e.edition_date or date(e.year, 12, 31), e.name))


def equivalent_editions(db: Session, editions: list[SalesEdition]) -> dict[uuid.UUID, SalesEdition]:
    """edition.id -> the same title's equivalent edition one year earlier."""
    wanted = {(e.title_id, e.year - 1) for e in editions}
    if not wanted:
        return {}
    prev_rows = db.scalars(select(SalesEdition).where(
        SalesEdition.title_id.in_({t for t, _ in wanted}),
        SalesEdition.year.in_({y for _, y in wanted}),
    )).all()
    by_title_year: dict[tuple, list[SalesEdition]] = defaultdict(list)
    for p in prev_rows:
        by_title_year[(p.title_id, p.year)].append(p)

    this_year_rows = db.scalars(select(SalesEdition).where(
        SalesEdition.title_id.in_({e.title_id for e in editions}),
        SalesEdition.year.in_({e.year for e in editions}),
    )).all()
    by_title_year_now: dict[tuple, list[SalesEdition]] = defaultdict(list)
    for e in this_year_rows:
        by_title_year_now[(e.title_id, e.year)].append(e)

    out = {}
    for e in editions:
        prev = by_title_year.get((e.title_id, e.year - 1), [])
        if not prev:
            continue
        key = name_key(e.name)
        hit = next((p for p in prev if name_key(p.name) == key and key), None)
        if not hit and re.fullmatch(r"\D*\d{2,3}\D*", e.name.strip()):
            ordered_now = _running_order(by_title_year_now[(e.title_id, e.year)])
            ordered_prev = _running_order(prev)
            idx = next((i for i, x in enumerate(ordered_now) if x.id == e.id), None)
            if idx is not None and idx < len(ordered_prev):
                hit = ordered_prev[idx]
        if hit:
            out[e.id] = hit
    return out


def edition_totals(db: Session, edition_ids: list[uuid.UUID], booked_before: date | None = None) -> dict[uuid.UUID, dict]:
    """Per edition: booked £, orders, invoiced £, uninvoiced count, pages."""
    if not edition_ids:
        return {}
    q = select(
        SalesOrder.edition_id,
        func.coalesce(func.sum(SalesOrder.value_gbp).filter(SalesOrder.status == BOOKED), 0),
        func.count().filter(SalesOrder.status == BOOKED),
        func.coalesce(func.sum(SalesOrder.invoice_value_gbp).filter(SalesOrder.status == BOOKED), 0),
        func.count().filter(SalesOrder.status == BOOKED, SalesOrder.value_gbp > 0, SalesOrder.invoice_number.is_(None)),
        func.coalesce(func.sum(SalesOrder.pages).filter(SalesOrder.status == BOOKED), 0),
        func.count().filter(SalesOrder.import_warning.isnot(None)),
    ).where(SalesOrder.edition_id.in_(edition_ids)).group_by(SalesOrder.edition_id)
    if booked_before:
        q = q.where(func.coalesce(SalesOrder.booked_on, date.min) <= booked_before)
    return {
        row[0]: {"booked": float(row[1]), "orders": row[2], "invoiced": float(row[3]),
                 "uninvoiced": row[4], "pages": float(row[5]), "warnings": row[6]}
        for row in db.execute(q).all()
    }


def same_point_last_year(today: date) -> date:
    try:
        return today.replace(year=today.year - 1)
    except ValueError:  # 29 Feb
        return today - timedelta(days=365)
