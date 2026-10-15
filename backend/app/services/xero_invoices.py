"""Draft invoices in Xero from a booking (15 Oct call with Samantha).

One click on a booking (or its Ready to invoice card) makes a DRAFT sales invoice in Xero for the items that are due;
Samantha checks it and sends it from Xero herself, as she does today. Nothing is ever approved or sent from here.

What goes on it - the way Samantha raises them by hand:
  contact     the client's Xero contact. Found from the booking (its own link, the company's remembered link, the contact
              on the company's last Xero invoice, then a search by invoice-to / agency / client name and email); if it
              isn't certain, she is told and picks it herself. Her choice is remembered on the booking and the company.
  date        today (Xero's date is the day it's raised - she changes it in Xero if she sends it another day)
  reference   the client's PO number if there is one, otherwise "Magazine Month"
  currency    the booking's invoice currency (prices are in pounds, so other currencies ask for the amounts)
  lines       one per item: what it is and which issue, quantity 1, the price, agency commission as the discount,
              the account code, item code and tracking (product) for that publication - set once in
              Bookings > Xero codes, or chosen in the dialog and remembered.
Tax is left to Xero (it follows the contact and the account), exactly as when she types it in.

Everything that can go wrong comes back as a plain "problem" with what's needed to fix it, never as an error.
"""
from __future__ import annotations

import difflib
import hashlib
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, SalesDeal, SalesEdition, SalesOrder, SalesTitle, XeroInvoice
from app.services import xero

logger = logging.getLogger("app.services.xero_invoices")

EDIT_URL = "https://go.xero.com/AccountsReceivable/Edit.aspx?InvoiceID={}"
_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_SECONDS = 600
GENERIC_INVOICE_TO = re.compile(r"^(accounts?( payable| department| team)?|finance( team| department)?|the accounts team|ap)$", re.I)


class XeroUnavailable(Exception):
    """Xero isn't connected, or won't let us do this. The message is a plain sentence for the person."""


# ---- talking to Xero --------------------------------------------------------------------------------------

def _call(db: Session, method: str, path: str, *, params: dict | None = None, json: dict | None = None,
          headers: dict | None = None) -> httpx.Response:
    """One Xero API call for the connected organisation. Separate so tests can stub it."""
    if not xero.is_configured():
        raise XeroUnavailable("Xero isn't set up yet. An administrator connects it in Settings, Integrations.")
    conn = xero.ensure_webhook_connection(db) if xero.webhook_mode() else xero.connection(db)
    if not conn:
        raise XeroUnavailable("Xero isn't connected yet. An administrator connects it in Settings, Integrations.")
    try:
        token = xero._access_token(db, conn)
    except xero.XeroAuthError as exc:
        raise XeroUnavailable("The Xero connection needs renewing. An administrator reconnects it in Settings, Integrations.") from exc
    h = {"Authorization": f"Bearer {token}", "xero-tenant-id": conn.tenant_id, "Accept": "application/json", **(headers or {})}
    try:
        return httpx.request(method, f"{xero.API}/{path}", params=params, json=json, headers=h, timeout=60)
    except httpx.HTTPError as exc:
        raise XeroUnavailable("Xero didn't answer just now. Try again in a minute.") from exc


def _check(resp: httpx.Response) -> dict:
    if resp.status_code in (401, 403):
        raise XeroUnavailable("Xero didn't let BMI Brain do this. An administrator needs to reconnect Xero with permission "
                              "to create invoices (Settings, Integrations).")
    if resp.status_code == 429:
        raise XeroUnavailable("Xero is busy (too many requests). Try again in a minute.")
    if resp.status_code >= 500:
        raise XeroUnavailable("Xero had a problem on its side. Try again in a few minutes.")
    try:
        return resp.json()
    except ValueError:
        return {}


def validation_messages(body: dict) -> list[str]:
    """Xero's own reasons for refusing an invoice, e.g. "Account code '9999' is not a valid code for this document"."""
    out: list[str] = []
    for el in body.get("Elements") or []:
        for v in el.get("ValidationErrors") or []:
            if v.get("Message"):
                out.append(str(v["Message"]))
        for li in el.get("LineItems") or []:
            for v in li.get("ValidationErrors") or []:
                if v.get("Message"):
                    out.append(str(v["Message"]))
    if not out and body.get("Message"):
        out.append(str(body["Message"]))
    return list(dict.fromkeys(out))


def reference_data(db: Session, fresh: bool = False) -> dict:
    """Xero's sales accounts, items, tracking categories and currencies (cached for 10 minutes)."""
    conn = xero.connection(db)
    key = conn.tenant_id if conn else "-"
    hit = _CACHE.get(key)
    if hit and not fresh and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    accounts = _check(_call(db, "GET", "Accounts")).get("Accounts") or []
    items = _check(_call(db, "GET", "Items")).get("Items") or []
    tracking = _check(_call(db, "GET", "TrackingCategories")).get("TrackingCategories") or []
    currencies = _check(_call(db, "GET", "Currencies")).get("Currencies") or []
    data = {
        "accounts": [{"code": a.get("Code"), "name": a.get("Name"), "type": a.get("Type")} for a in accounts
                     if a.get("Code") and a.get("Status", "ACTIVE") == "ACTIVE" and a.get("Type") in ("REVENUE", "SALES", "OTHERINCOME")],
        "items": [{"code": i.get("Code"), "name": i.get("Name") or i.get("Code"),
                   "account_code": (i.get("SalesDetails") or {}).get("AccountCode")} for i in items if i.get("Code") and i.get("IsSold", True)],
        "tracking": [{"name": t.get("Name"), "options": [o.get("Name") for o in t.get("Options") or [] if o.get("Status", "ACTIVE") == "ACTIVE"]}
                     for t in tracking if t.get("Status", "ACTIVE") == "ACTIVE"],
        "currencies": sorted({c.get("Code") for c in currencies if c.get("Code")} | {"GBP"}),
    }
    _CACHE[key] = (time.time(), data)
    return data


def search_contacts(db: Session, q: str, limit: int = 10) -> list[dict]:
    q = (q or "").strip()
    if len(q) < 2:
        return []
    body = _check(_call(db, "GET", "Contacts", params={"searchTerm": q, "summaryOnly": "true", "page": 1}))
    out = []
    for c in body.get("Contacts") or []:
        if c.get("ContactStatus", "ACTIVE") != "ACTIVE":
            continue
        out.append({"id": c.get("ContactID"), "name": c.get("Name") or "", "email": c.get("EmailAddress") or None,
                    "is_customer": bool(c.get("IsCustomer"))})
    return out[:limit]


# ---- finding the contact ----------------------------------------------------------------------------------

def _norm(s: str | None) -> str:
    from app.sales.matching import normalise
    return normalise(s or "")


def _name_score(want: str, got: str) -> float:
    a, b = _norm(want), _norm(got)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) >= 4 and (a in b or b in a):
        return 0.8
    return difflib.SequenceMatcher(None, a, b).ratio() * 0.85


@dataclass
class ContactGuess:
    contact: dict | None                      # {"id", "name"} when certain
    candidates: list[dict] = field(default_factory=list)
    tried: list[str] = field(default_factory=list)
    how: str = ""


def _names_to_try(db: Session, d: SalesDeal) -> list[str]:
    names = []
    first_line = (d.invoice_to or "").strip().splitlines()[0].strip() if (d.invoice_to or "").strip() else ""
    if first_line and not GENERIC_INVOICE_TO.match(first_line):
        names.append(first_line)
    if d.agency_name:
        names.append(d.agency_name)
    names.append(d.client_name)
    company = db.get(Company, d.company_id) if d.company_id else None
    if company:
        names.append(company.name)
    return [n for n in dict.fromkeys(x.strip() for x in names if x and x.strip())]


def find_contact(db: Session, d: SalesDeal) -> ContactGuess:
    if d.xero_contact_id:
        return ContactGuess({"id": d.xero_contact_id, "name": d.xero_contact_name or ""}, how="linked on this booking")
    company = db.get(Company, d.company_id) if d.company_id else None
    if company and company.xero_contact_id and not d.agency_name:
        return ContactGuess({"id": company.xero_contact_id, "name": company.xero_contact_name or ""}, how="linked on the company")
    names = _names_to_try(db, d)
    # The contact on this client's last Xero invoice is the strongest clue.
    if d.company_id:
        last = db.scalar(select(XeroInvoice.contact_name).join(SalesOrder, SalesOrder.xero_invoice_id == XeroInvoice.id)
                         .where(SalesOrder.company_id == d.company_id, XeroInvoice.contact_name.isnot(None))
                         .order_by(XeroInvoice.issued_on.desc().nulls_last()).limit(1))
        if last and not d.agency_name:
            names.insert(0, last)
    emails = {e.lower() for e in (d.invoice_email, d.contact_email) if e}
    # Names in order of who the invoice goes to: invoice-to, then the agency, then the client. The first name with
    # exactly one certain match wins (an agency booking is invoiced to the agency, not the advertiser).
    seen: dict[str, tuple[float, dict]] = {}
    for n in names[:4]:
        found = search_contacts(db, n)
        sure_here = []
        for c in found:
            s = _name_score(n, c["name"])
            if c.get("email") and c["email"].lower() in emails:
                s = max(s, 0.97)
            if s >= 0.95:
                sure_here.append(c)
            if c["id"] not in seen or seen[c["id"]][0] < s:
                seen[c["id"]] = (s, c)
        if len(sure_here) == 1:
            ranked = sorted(seen.values(), key=lambda x: -x[0])
            return ContactGuess({"id": sure_here[0]["id"], "name": sure_here[0]["name"]},
                                [{**c, "score": round(sc, 2)} for sc, c in ranked[:6]], names, "matched by name")
        if len(sure_here) > 1:
            break
    ranked = sorted(seen.values(), key=lambda x: -x[0])
    candidates = [{**c, "score": round(sc, 2)} for sc, c in ranked[:6]]
    return ContactGuess(None, candidates, names, "several possible" if any(sc >= 0.95 for sc, _ in ranked) or len(candidates) > 1 else "not found")


# ---- working out the invoice -------------------------------------------------------------------------------

def _money(v) -> float:
    return round(float(v or 0), 2)


def _title_codes(codes: dict, title_id: uuid.UUID | None) -> dict:
    base = dict((codes or {}).get("default") or {})
    own = ((codes or {}).get("titles") or {}).get(str(title_id)) or {}
    return {**base, **{k: v for k, v in own.items() if v}}


def _month(d: date | None) -> str:
    return f"{d:%b %Y}" if d else ""


def due_orders(db: Session, d: SalesDeal, order_ids: list[uuid.UUID] | None) -> list[tuple[SalesOrder, SalesEdition, SalesTitle]]:
    stmt = (select(SalesOrder, SalesEdition, SalesTitle).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
            .join(SalesTitle, SalesEdition.title_id == SalesTitle.id)
            .where(SalesOrder.deal_id == d.id, SalesOrder.status == "booked", SalesOrder.invoice_number.is_(None),
                   SalesOrder.xero_invoice_id.is_(None), SalesOrder.added_value.is_(False), SalesOrder.value_gbp > 0))
    if order_ids:
        stmt = stmt.where(SalesOrder.id.in_(order_ids))
    rows = db.execute(stmt).all()
    if not order_ids:   # nothing chosen: the items that are due now
        from app.automations import invoice_due
        due = {o.id for o, _, _ in invoice_due.due_items(db, d)}
        rows = [r for r in rows if r[0].id in due]
    return sorted(rows, key=lambda r: (r[0].item_date or r[1].edition_date or date.max, r[0].description or ""))


def plan(db: Session, d: SalesDeal, order_ids: list[uuid.UUID] | None, overrides: dict | None = None) -> dict:
    """The invoice we'd create, and anything stopping it, without touching Xero beyond lookups."""
    from app.api.routes.sales import edition_label
    from app.sales import deals as dl

    ov = overrides or {}
    line_ov = ov.get("lines") or {}
    problems: list[dict] = []
    rows = due_orders(db, d, order_ids)
    st = dl.settings(db)
    codes = st.xero_codes or {}
    currency = (ov.get("currency") or d.invoice_currency or "GBP").upper()
    agency = float(d.agency_pct or 0)
    lines = []
    for o, ed, t in rows:
        c = _title_codes(codes, t.id)
        mine = line_ov.get(str(o.id)) or {}
        runs = o.item_date or ed.edition_date
        what = o.description or o.size or "Advertising"
        desc = mine.get("description") or f"{what} - {edition_label(t, ed)}" + (f" ({runs:%-d %b %Y})" if o.item_date else "")
        amount = mine.get("unit_amount")
        lines.append({
            "order_id": str(o.id), "title_id": str(t.id), "title": t.name, "description": desc[:4000], "quantity": 1,
            "unit_amount": round(float(amount), 2) if amount not in (None, "") else _money(o.value_gbp),
            "value_gbp": _money(o.value_gbp),
            "discount_rate": round(agency * 100, 2) if agency else None,
            "account_code": mine.get("account_code") or c.get("account_code") or None,
            "item_code": mine.get("item_code") if "item_code" in mine else (c.get("item_code") or None),
            "tracking": [x for x in (mine.get("tracking") or c.get("tracking") or []) if x.get("name") and x.get("option")],
            "amount_given": amount not in (None, ""),
        })
    if not rows:
        problems.append({"key": "nothing", "message": "There's nothing on this booking left to invoice: everything is invoiced, free, or not due yet."})

    contact = None
    candidates: list[dict] = []
    tried: list[str] = []
    try:
        if ov.get("contact_id"):
            contact = {"id": ov["contact_id"], "name": ov.get("contact_name") or ""}
        else:
            g = find_contact(db, d)
            contact, candidates, tried = g.contact, g.candidates, g.tried
    except XeroUnavailable as exc:
        problems.append({"key": "connection", "message": str(exc)})
    if not contact and not any(p["key"] == "connection" for p in problems):
        names = ", ".join(f"“{n}”" for n in tried[:3]) or f"“{d.client_name}”"
        problems.append({"key": "contact", "message": (
            f"We couldn't find the right Xero contact for this booking (we looked for {names}). "
            "Please choose it below, or search for it. It's remembered next time."
            if not candidates else
            f"We found more than one Xero contact that could be this client ({names}). Please choose the right one below. It's remembered next time.")})
    missing = sorted({ln["title"] for ln in lines if not ln["account_code"] and not ln["item_code"]})
    if missing:
        problems.append({"key": "account", "message": (
            f"There's no Xero account code yet for {', '.join(missing)}. Choose the account for "
            f"{'each line' if len(lines) > 1 else 'the line'} below - it's remembered for that publication.")})
    if currency != "GBP" and any(not ln["amount_given"] for ln in lines):
        problems.append({"key": "currency", "message": (
            f"This booking is invoiced in {currency}, but its prices are in pounds. Enter the {currency} amount for each line below.")})

    title_names = sorted({ln["title"] for ln in lines})
    first_run = min((o.item_date or ed.edition_date for o, ed, _ in rows if (o.item_date or ed.edition_date)), default=None)
    reference = ov.get("reference") or d.po_number or " ".join(x for x in (" / ".join(title_names), _month(first_run)) if x)
    return {
        "deal_id": str(d.id), "deal_number": d.number, "client_name": d.client_name,
        "contact": contact, "contact_candidates": candidates,
        "date": date.today().isoformat(), "reference": reference[:255], "currency": currency,
        "lines": lines, "problems": problems,
        "invoice_to": d.invoice_to, "invoice_email": d.invoice_email, "po_number": d.po_number,
        "instructions": d.invoice_instructions,
        "agency": {"name": d.agency_name, "pct": round(agency * 100, 2)} if d.agency_name else None,
    }


def _payload(draft: dict) -> dict:
    lines = []
    for ln in draft["lines"]:
        li = {"Description": ln["description"], "Quantity": ln["quantity"], "UnitAmount": ln["unit_amount"]}
        if ln.get("discount_rate"):
            li["DiscountRate"] = ln["discount_rate"]
        if ln.get("account_code"):
            li["AccountCode"] = ln["account_code"]
        if ln.get("item_code"):
            li["ItemCode"] = ln["item_code"]
        if ln.get("tracking"):
            li["Tracking"] = [{"Name": x["name"], "Option": x["option"]} for x in ln["tracking"]]
        lines.append(li)
    inv = {"Type": "ACCREC", "Status": "DRAFT", "Contact": {"ContactID": draft["contact"]["id"]}, "Date": draft["date"],
           "LineAmountTypes": "Exclusive", "Reference": draft["reference"], "LineItems": lines}
    if draft["currency"] != "GBP":
        inv["CurrencyCode"] = draft["currency"]
    return {"Invoices": [inv]}


def summary(inv: dict) -> dict:
    """What Samantha sees after it's made: everything on the invoice, as Xero has it."""
    return {
        "id": inv.get("InvoiceID"), "number": inv.get("InvoiceNumber"), "status": inv.get("Status"),
        "url": EDIT_URL.format(inv.get("InvoiceID")), "contact": (inv.get("Contact") or {}).get("Name"),
        "date": (xero._day(inv.get("DateString") or inv.get("Date")) or date.today()).isoformat(),
        "due_date": d.isoformat() if (d := xero._day(inv.get("DueDateString") or inv.get("DueDate"))) else None,
        "reference": inv.get("Reference"), "currency": inv.get("CurrencyCode") or "GBP",
        "lines": [{"description": li.get("Description"), "quantity": li.get("Quantity"), "unit_amount": li.get("UnitAmount"),
                   "discount_rate": li.get("DiscountRate"), "account_code": li.get("AccountCode"), "item_code": li.get("ItemCode"),
                   "tax_type": li.get("TaxType"), "tax": li.get("TaxAmount"), "amount": li.get("LineAmount"),
                   "tracking": [f"{t.get('Name')}: {t.get('Option')}" for t in li.get("Tracking") or []]}
                  for li in inv.get("LineItems") or []],
        "sub_total": inv.get("SubTotal"), "tax": inv.get("TotalTax"), "total": inv.get("Total"),
    }


def _remember(db: Session, d: SalesDeal, draft: dict, overrides: dict) -> None:
    """The contact and any codes chosen in the dialog are kept for next time."""
    from app.sales import deals as dl

    d.xero_contact_id, d.xero_contact_name = draft["contact"]["id"], draft["contact"].get("name") or d.xero_contact_name
    company = db.get(Company, d.company_id) if d.company_id else None
    if company and not d.agency_name and (overrides.get("contact_id") or not company.xero_contact_id):
        company.xero_contact_id, company.xero_contact_name = d.xero_contact_id, d.xero_contact_name
    chosen = overrides.get("lines") or {}
    if not chosen or overrides.get("remember_codes") is False:
        return
    st = dl.settings(db)
    codes = dict(st.xero_codes or {})
    titles = dict(codes.get("titles") or {})
    for ln in draft["lines"]:
        mine = chosen.get(ln["order_id"]) or {}
        if not (mine.get("account_code") or mine.get("item_code") or mine.get("tracking")):
            continue
        own = dict(titles.get(ln["title_id"]) or {})
        for k in ("account_code", "item_code", "tracking"):
            if mine.get(k) and not own.get(k):
                own[k] = mine[k]
        titles[ln["title_id"]] = own
    codes["titles"] = titles
    st.xero_codes = codes


def create(db: Session, d: SalesDeal, order_ids: list[uuid.UUID] | None, overrides: dict | None, user_id: uuid.UUID | None) -> dict:
    """Make the draft invoice. Returns {"ok": True, "invoice": summary} or {"ok": False, "draft": ..., "problems": [...]}."""
    ov = overrides or {}
    draft = plan(db, d, order_ids, ov)
    if draft["problems"]:
        return {"ok": False, "draft": draft, "problems": draft["problems"]}
    key = hashlib.sha256(("|".join(sorted(ln["order_id"] for ln in draft["lines"])) + "|" + draft["contact"]["id"]).encode()).hexdigest()[:40]
    try:
        resp = _call(db, "POST", "Invoices", json=_payload(draft), headers={"Idempotency-Key": key})
        body = _check(resp)
    except XeroUnavailable as exc:
        return {"ok": False, "draft": draft, "problems": [{"key": "connection", "message": str(exc)}]}
    if resp.status_code >= 400:
        msgs = validation_messages(body) or ["Xero didn't accept the invoice."]
        probs = []
        for m in msgs:
            low = m.lower()
            k = "account" if "account" in low else "contact" if "contact" in low else "currency" if "currency" in low else "tracking" if "tracking" in low else "xero"
            probs.append({"key": k, "message": f"Xero said: {m}"})
        return {"ok": False, "draft": draft, "problems": probs}
    inv = (body.get("Invoices") or [{}])[0]
    if not inv.get("InvoiceID"):
        return {"ok": False, "draft": draft, "problems": [{"key": "xero", "message": "Xero didn't say whether the invoice was made. Check Xero before trying again."}]}
    # Keep our copy of the invoice and link the items to it, exactly like a matched invoice.
    xero._upsert(db, inv)
    db.flush()
    row = db.scalar(select(XeroInvoice).where(XeroInvoice.xero_id == inv["InvoiceID"]))
    orders = db.scalars(select(SalesOrder).where(SalesOrder.id.in_([uuid.UUID(ln["order_id"]) for ln in draft["lines"]]))).all()
    from app.sales.invoice_match import link_bookings
    link_bookings(db, row, list(orders), "created", user_id)
    for o in orders:   # our own figures (Xero's draft total may be in another currency)
        o.invoice_value_gbp, o.invoiced_on = o.value_gbp, date.today()
    _remember(db, d, draft, ov)
    d.updated_at = datetime.now(timezone.utc)
    from app.automations import invoice_due
    db.flush()
    invoice_due.refresh(db, d, notify=False)
    return {"ok": True, "invoice": summary(inv)}
