"""Sales Orders tools: find a booking, and explain exactly where a booking is up to (and why)."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import or_, select

from app.brain.registry import ToolEnv, ToolError, brain_tool
from app.models import SalesDeal, User

STATUS_MEANING = {
    "pencilled": "Pencilled - provisional, not confirmed by the client yet. Nothing is invoiced or handed off.",
    "confirmed": "Confirmed - the client has agreed; it goes to Accounts to check, then on to invoicing and hand-offs.",
    "cancelled": "Cancelled - kept for the record; nothing more happens with it.",
}
HANDOFF_STATE = {
    "sent": "sent", "failed": "couldn't be sent", "no_address": "no email address set up for this team yet",
    "waiting_format": "waiting until the format is decided (it says TBC)", "waiting_check": "waiting for the booking to be confirmed and checked",
    "due": "ready - goes out on the next save or when someone presses Send",
}


def _find(env: ToolEnv, booking: str) -> SalesDeal:
    b = (booking or "").strip().lstrip("#")
    d = None
    if re.fullmatch(r"[0-9a-fA-F-]{36}", b):
        d = env.db.get(SalesDeal, uuid.UUID(b))
    elif b.isdigit():
        d = env.db.scalar(select(SalesDeal).where(SalesDeal.number == int(b)))
    if not d:
        raise ToolError(f"There's no booking {booking!r}. Ask for the booking number, or use sales_order_find with the client's name.")
    return d


def _date(iso: str | None) -> str | None:
    if not iso:
        return None
    from datetime import date
    try:
        return date.fromisoformat(iso[:10]).strftime("%-d %b %Y")
    except ValueError:
        return iso


@brain_tool("Finding the booking")
def sales_order_find(env: ToolEnv, query: str) -> dict:
    """Finds bookings by number, client, agency, contact or order (PO) number. Up to 8, newest first.

    Args:
      query: a booking number or some words from the client/agency/contact name
    """
    q = (query or "").strip().lstrip("#")
    if not q:
        raise ToolError("Say which booking - a number or the client's name.")
    like = f"%{q}%"
    conds = [SalesDeal.client_name.ilike(like), SalesDeal.agency_name.ilike(like), SalesDeal.contact_name.ilike(like), SalesDeal.po_number.ilike(like)]
    if q.isdigit():
        conds.append(SalesDeal.number == int(q))
    rows = env.db.scalars(select(SalesDeal).where(or_(*conds)).order_by(SalesDeal.number.desc()).limit(8)).all()
    return {"bookings": [{"number": d.number, "client": d.client_name, "agency": d.agency_name, "status": d.status,
                          "booked_on": _date(d.booked_on.isoformat()) if d.booked_on else None,
                          "total_gbp": float(d.total_gbp or 0), "link": f"/sales/deals/{d.id}"} for d in rows],
            "note": None if rows else "No bookings match. Try a shorter part of the name."}


@brain_tool("Looking at the booking")
def sales_order_explain(env: ToolEnv, booking: str) -> dict:
    """Explains where one booking is up to, with the real reasons: status, whether this person can change it and
    why not, the Accounts check, the lock, each item's invoicing (when it's due, invoiced, in Xero) and hand-offs.

    Args:
      booking: the booking number (e.g. "1234") or its id from the page address
    """
    from app.api.routes import deals as routes
    d = _find(env, booking)
    out = routes._out(env.db, d, env.identity)
    me = env.user
    names = {u.id: u.name for u in env.db.scalars(select(User).where(User.id.in_([x for x in (d.checked_by_user_id, d.created_by_user_id) if x])))}

    if out["status"] == "cancelled":
        can, why = False, "It's cancelled. Reopen it first to change it."
    elif out["locked"] and not out["can_approve"]:
        can, why = False, "Accounts has checked it (or part of it is invoiced), so changes go to Accounts: use Request a change."
    elif not out["can_edit"]:
        can, why = False, "Only the salesperson on this booking, whoever created it, Accounts or a manager can change it."
    else:
        can, why = True, None

    lock = None
    if out["locked"]:
        reasons = []
        if d.checked_at:
            reasons.append(f"Accounts checked it on {d.checked_at:%-d %b %Y}" + (f" ({names.get(d.checked_by_user_id)})" if names.get(d.checked_by_user_id) else ""))
        if any(r.get("invoice_number") for r in out["schedule"]):
            reasons.append("at least one item has been invoiced")
        lock = {"why": " and ".join(reasons) or "it's been checked by Accounts",
                "who_can_unlock": "Accounts (or an administrator standing in for them)",
                "what_you_can_do": "Press Request a change and say what needs changing; Accounts approve it or unlock the booking for you."}
    items = []
    for r in out["schedule"][:25]:
        items.append({
            "item": r.get("description"), "edition": r.get("edition") or r.get("title"), "runs_on": _date(r.get("runs_on")),
            "value_gbp": r.get("value_gbp"), "added_value": r.get("added_value") or None,
            "to_allocate": r.get("to_allocate") or None,
            "invoice_due": _date(r.get("invoice_due")), "invoice_number": r.get("invoice_number"),
            "xero": r.get("xero_state"), "ready_to_invoice": r.get("ready_to_invoice") or None,
        })
    handoffs = [{"line": h["description"], "goes_to": h["team"],
                 "teams": [{"team": t["team"], "state": HANDOFF_STATE.get(t["state"], t["state"]), "sent_on": _date(t.get("sent_at"))} for t in h["teams"]]}
                for h in out["handoffs"][:15]]
    check = out.get("check")
    return {
        "link": f"/sales/deals/{d.id}", "number": d.number, "client": d.client_name, "agency": d.agency_name,
        "salesperson": (out.get("rep") or {}).get("name"),
        "status": out["status"], "status_meaning": STATUS_MEANING.get(out["status"]),
        "confirmed_on": _date(out.get("confirmed_at")), "confirmation_sent": _date(out.get("sent_at")), "sent_to": out.get("sent_to"),
        "you": {"name": me.name if me else None, "can_change_it": can, "why_not": why, "are_accounts": out["can_approve"]},
        "accounts_check": None if check is None else {
            "state": {"checked": "checked", "fix": "Accounts asked for something to be fixed", "waiting": "waiting for Accounts to check"}[check["state"]],
            "note_from_accounts": check.get("note"), "checked_on": _date(check.get("checked_at")), "checked_by": check.get("checked_by"),
            "stops_sending_confirmation": check.get("blocks_sending") or None},
        "locked": lock, "unlocked_for_a_change": out.get("unlocked"),
        "change_waiting_for_accounts": out.get("pending_change"),
        "invoicing": {"when": out.get("invoice_plan_label"), "on_date": _date(out.get("invoice_on")),
                      "invoiced_gbp": out["totals"]["invoiced_gbp"], "ready_now_gbp": out["totals"]["to_invoice_gbp"],
                      "xero_contact": (out.get("xero_contact") or {}).get("name")},
        "items": items, "more_items": max(0, len(out["schedule"]) - 25),
        "to_allocate": {"count": out["totals"]["unallocated_count"], "value_gbp": out["totals"]["unallocated_gbp"], "by": _date(out.get("allocate_by"))}
        if out["totals"]["unallocated_count"] else None,
        "handoffs": handoffs, "warnings": out["warnings"][:8],
        "total_gbp": out["totals"]["total_gbp"],
    }


@brain_tool("Working out the figures")
def sales_metrics(env: ToolEnv, measure: str = "booked", group_by: str = "none", year: int = 0, basis: str = "",
                  title: str = "", salesperson: str = "", client: str = "", product_line: str = "", compare_last_year: bool = False) -> dict:
    """Sales figures worked out exactly like the Sales Orders screens. ALWAYS use this for totals - never add
    numbers up yourself. Quote the period and the definition it gives back.

    Args:
      measure: booked | invoiced | awaiting_invoice | items | advertisers
      group_by: none | title | salesperson | month | client | edition | product_line
      year: the reporting year (a financial year is named by the year it starts in: 2025 = Jul 2025 - Jun 2026); 0 = this year
      basis: financial | calendar | "" for BMI's usual setting
      title: optional magazine/brand name, e.g. "Selling Travel"
      salesperson: optional name or initials
      client: optional client name
      product_line: optional print | online | events
      compare_last_year: also give the year before, for comparison
    """
    from app.brain import metrics
    from app.brain.tools.crm import need
    need(env, "sales_overview", "bookings", "editions")
    try:
        return metrics.compute(env.db, measure=measure, group_by=group_by, year=year or None, basis=basis or None, title=title or None,
                               salesperson=salesperson or None, client=client or None, product_line=product_line or None,
                               compare_last_year=compare_last_year)
    except metrics.MetricError as e:
        raise ToolError(str(e))


@brain_tool("Listing the items")
def sales_items(env: ToolEnv, client: str = "", title: str = "", year: int = 0, status: str = "booked", uninvoiced_only: bool = False,
                limit: int = 20) -> dict:
    """Individual booked items (one per advert or listing per edition), newest edition first - for "what did they
    book in ...", "which items aren't invoiced". For totals use sales_metrics instead.

    Args:
      client: optional client name
      title: optional magazine/brand name
      year: optional edition year (calendar), 0 = any
      status: booked | pencilled | cancelled | any
      uninvoiced_only: only booked items with a value and no invoice number
      limit: how many to list (up to 50)
    """
    from sqlalchemy import func

    from app.brain.tools.crm import need
    from app.models import Company, SalesEdition, SalesOrder, SalesTitle
    need(env, "bookings", "editions")
    stmt = (select(SalesOrder, SalesEdition, SalesTitle).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
            .join(SalesTitle, SalesEdition.title_id == SalesTitle.id).outerjoin(Company, Company.id == SalesOrder.company_id))
    if client.strip():
        like = f"%{client.strip()}%"
        stmt = stmt.where(or_(SalesOrder.client_name.ilike(like), Company.name.ilike(like)))
    if title.strip():
        t = f"%{title.strip()}%"
        stmt = stmt.where(or_(SalesTitle.name.ilike(t), SalesTitle.slug.ilike(t)))
    if year:
        stmt = stmt.where(SalesEdition.year == year)
    if status in ("booked", "pencilled", "cancelled"):
        stmt = stmt.where(SalesOrder.status == status)
    if uninvoiced_only:
        stmt = stmt.where(SalesOrder.status == "booked", SalesOrder.invoice_number.is_(None), SalesOrder.value_gbp > 0)
    total = env.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = env.db.execute(stmt.order_by(func.coalesce(SalesOrder.item_date, SalesEdition.edition_date).desc().nulls_last())
                          .limit(max(1, min(limit, 50)))).all()
    return {"items": [{"client": o.client_name, "edition": f"{t.name} · {e.name}", "runs": _date((o.item_date or e.edition_date).isoformat()) if (o.item_date or e.edition_date) else None,
                       "what": o.size or o.series, "value_gbp": float(o.value_gbp or 0), "status": o.status, "invoice": o.invoice_number,
                       "link": f"/sales/orders/{o.id}"} for o, e, t in rows],
            "total_matching": total, "see_all": "/sales/bookings"}
