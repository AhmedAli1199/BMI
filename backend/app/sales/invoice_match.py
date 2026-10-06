"""Matching Xero invoices to order-register bookings (so nobody has to type an
invoice number).

For every sales invoice in Xero that no booking claims yet, find the booking
(or the few bookings) it was raised for, using what both sides say:

- client: the invoice's customer against the booking's client name, helped
  by what we already know - the name this client has been invoiced under
  before (an agency, a PR company, "Delta" vs "Delta Air Lines");
- amount: the invoice total before VAT equals the booking's value, or the
  values of 2-4 of the same client's bookings add up to it (one invoice for
  several bookings is common); foreign-currency invoices are converted;
- issue: the invoice reference / line text names the issue ("OBH 94",
  "People Awards") - the strongest clue when a client has several bookings
  of the same price;
- timing: the invoice is dated sensibly around the booking and the issue.

Tested on BMI's own history (booking numbers hidden, then found again): when
the matcher acted on its own it was right 99 times in 100; for about 86% of
invoices its first answer was right. So only a *clear* match is applied on
its own (a strong client match and a comfortable lead over the next-best
answer); everything else becomes a review item with the candidates and the
reasons side by side. Nothing is ever written to Xero.
"""
from __future__ import annotations

import itertools
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from rapidfuzz import fuzz
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import SalesEdition, SalesOrder, SalesTitle, XeroInvoice
from app.services.field_audit import record_field_changes
from app.services.xero import number_key

# A match is applied on its own only when the client name is a strong match
# AND the best answer leads the runner-up by at least this much.
AUTO_MIN_NAME = 85
AUTO_MARGIN = 15
MAX_SUM_SIZE = 4          # one invoice for up to this many bookings
MAX_GROUP = 14            # bookings of one client considered together
MAX_CANDIDATES = 4        # shown on a review card

_STOP = {"ltd", "limited", "inc", "llc", "plc", "the", "and", "co", "company", "corp", "corporation", "gmbh", "uk",
         "lp", "llp", "sa", "ag", "pte", "pty", "of", "for"}
_GENERIC_TITLE_WORDS = {"magazine", "online", "events", "travel"}
XERO_INVOICE_URL = "https://go.xero.com/AccountsReceivable/View.aspx?InvoiceID={}"


def norm(s: str | None) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower().replace("&", " and "))
    return " ".join(t for t in s.split() if t not in _STOP)


def _money(v: float | None) -> str:
    return "—" if v is None else f"£{v:,.2f}".replace(".00", "")


def invoice_gbp_net(inv: XeroInvoice) -> float | None:
    """The invoice total before VAT in pounds (foreign invoices converted at
    Xero's own rate), or None when that can't be worked out."""
    net = float(inv.sub_total or 0)
    if (inv.currency or "GBP") == "GBP":
        return net
    rate = float(inv.currency_rate or 0)
    return net / rate if rate else None


def _tol(value: float, inv: XeroInvoice) -> float:
    return 2.0 if (inv.currency or "GBP") == "GBP" else max(2.0, 0.03 * value)


@dataclass
class Context:
    titles: dict
    editions: dict
    pool: list[SalesOrder]                      # bookings still needing an invoice
    names: dict[uuid.UUID, str]                 # booking id -> normalised client name
    aliases: dict[str, Counter]                 # normalised client -> Counter(normalised Xero customer names seen)


@dataclass
class Hypothesis:
    orders: list[SalesOrder]
    score: float
    name_sim: int
    known_name: bool
    cue_issue: str | None
    cue_title: bool
    days: int | None
    kind: str                                    # single | sum
    notes: list[str] = field(default_factory=list)


def edition_label(ctx: Context, ed: SalesEdition) -> str:
    from app.api.routes.sales import edition_label as _label

    return _label(ctx.titles[ed.title_id], ed)


def build_context(db: Session) -> Context:
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    editions = {e.id: e for e in db.scalars(select(SalesEdition))}
    xero_keys = {k for (k,) in db.execute(select(XeroInvoice.number_key).where(XeroInvoice.number_key.isnot(None)))}
    pool, names = [], {}
    for o in db.scalars(select(SalesOrder).where(SalesOrder.status == "booked", SalesOrder.value_gbp > 0,
                                                  SalesOrder.xero_invoice_id.is_(None))):
        # No invoice number yet - or a number that isn't in Xero at all (a typo, or from before the sync window).
        if o.invoice_number and number_key(o.invoice_number) in xero_keys:
            continue
        pool.append(o)
        names[o.id] = norm(o.client_name)
    aliases: dict[str, Counter] = defaultdict(Counter)
    for client, contact in db.execute(
            select(SalesOrder.client_name, XeroInvoice.contact_name)
            .join(XeroInvoice, SalesOrder.xero_invoice_id == XeroInvoice.id)):
        if client and contact:
            aliases[norm(client)][norm(contact)] += 1
    return Context(titles, editions, pool, names, aliases)


def _issue_cue(ctx: Context, o: SalesOrder, tokens: set[str]) -> tuple[str | None, bool]:
    ed = ctx.editions[o.edition_id]
    title = ctx.titles[ed.title_id]
    nums = [x for x in norm(ed.name).split() if x.isdigit() and 2 <= len(x) <= 3]
    words = [w for w in norm(title.name.replace("(", " ").replace(")", " ")).split()
             if len(w) >= 3 and w not in _GENERIC_TITLE_WORDS]
    hit_num = next((n for n in nums if n in tokens), None)
    hit_title = any(w in tokens for w in words)
    if hit_num:
        word = next((w for w in words if w in tokens), None)
        return (f"{word.upper()} {hit_num}" if word else f"issue {hit_num}"), hit_title
    return None, hit_title


def _days(inv: XeroInvoice, o: SalesOrder, ed: SalesEdition) -> int | None:
    ref = o.booked_on or ed.edition_date
    return (inv.issued_on - ref).days if inv.issued_on and ref else None


def _date_score(d: int | None) -> int:
    if d is None:
        return 0
    return 12 if -20 <= d <= 90 else (-12 if d > 240 or d < -90 else 0)


def _tokens(inv: XeroInvoice) -> set[str]:
    return set(norm(f"{inv.reference or ''} {inv.line_text or ''}").split())


def hypotheses(ctx: Context, inv: XeroInvoice) -> list[Hypothesis]:
    """Every sensible answer to "which booking(s) is this invoice for?",
    best first."""
    target = invoice_gbp_net(inv)
    if target is None or not ctx.pool:
        return []
    inv_name = norm(inv.contact_name)
    tokens = _tokens(inv)
    sim: dict[uuid.UUID, tuple[int, bool]] = {}
    for o in ctx.pool:
        cn = ctx.names[o.id]
        known = ctx.aliases.get(cn, {}).get(inv_name, 0) > 0
        sim[o.id] = (100 if known else fuzz.token_set_ratio(cn, inv_name), known)

    out: list[Hypothesis] = []

    def score(parts: list[SalesOrder]) -> tuple[float, str | None, bool, int | None]:
        cues = [_issue_cue(ctx, o, tokens) for o in parts]
        ds = [_days(inv, o, ctx.editions[o.edition_id]) for o in parts]
        base = sim[parts[0].id][0]
        pts = sum(25 * (c[0] is not None) + 10 * c[1] + _date_score(d) for c, d in zip(cues, ds)) / len(parts)
        eds = len({o.edition_id for o in parts})
        issue = next((c[0] for c in cues if c[0]), None)
        return base + pts - 5 * (eds - 1), issue, any(c[1] for c in cues), next((d for d in ds if d is not None), None)

    for o in ctx.pool:
        v = float(o.value_gbp)
        if abs(v - target) <= _tol(v, inv):
            s, issue, t_hit, d = score([o])
            out.append(Hypothesis([o], s, sim[o.id][0], sim[o.id][1], issue, t_hit, d, "single"))

    by_client: dict[str, list[SalesOrder]] = defaultdict(list)
    for o in ctx.pool:
        if sim[o.id][0] >= 80:
            by_client[ctx.names[o.id]].append(o)
    for group in by_client.values():
        for r in range(2, MAX_SUM_SIZE + 1):
            for sub in itertools.combinations(group[:MAX_GROUP], r):
                total = sum(float(o.value_gbp) for o in sub)
                if abs(total - target) <= _tol(total, inv):
                    s, issue, t_hit, d = score(list(sub))
                    out.append(Hypothesis(list(sub), s, sim[sub[0].id][0], sim[sub[0].id][1], issue, t_hit, d, "sum"))
    out.sort(key=lambda h: -h.score)
    # the same set of bookings can only appear once
    seen, unique = set(), []
    for h in out:
        key = frozenset(o.id for o in h.orders)
        if key not in seen:
            seen.add(key)
            unique.append(h)
    return unique


def is_clear(top: Hypothesis, rest: list[Hypothesis]) -> bool:
    runner_up = rest[0].score if rest else -50
    return top.name_sim >= AUTO_MIN_NAME and top.score - runner_up >= AUTO_MARGIN


def why_not_automatic(top: Hypothesis, rest: list[Hypothesis], inv: XeroInvoice, auto_on: bool) -> str:
    """One plain sentence for the top of the review card."""
    if top.name_sim < AUTO_MIN_NAME:
        return (f"The invoice is to “{inv.contact_name}”, which isn't the booking's client name - it may be an agency or a "
                f"parent company. Check this is the right booking.")
    if rest and top.score - rest[0].score < AUTO_MARGIN:
        return "More than one booking fits this invoice about equally well. Pick the right one."
    if any(o.invoice_number for o in top.orders):
        return "This booking already has an invoice number that isn't in Xero (a typo?). Linking will replace it."
    if not auto_on:
        return "Automatic linking is switched off, so every match waits for you."
    return "Please check this one."


# ---- the review card's content ----------------------------------------------------------

def _booking_facts(ctx: Context, o: SalesOrder, rep_names: dict) -> dict:
    ed = ctx.editions[o.edition_id]
    return {
        "id": str(o.id), "client": o.client_name, "edition": edition_label(ctx, ed), "edition_id": str(ed.id),
        "edition_date": ed.edition_date.isoformat() if ed.edition_date else None,
        "size": o.size, "booked_on": o.booked_on.isoformat() if o.booked_on else None,
        "value_gbp": float(o.value_gbp), "rep": rep_names.get(o.rep_id), "typed_number": o.invoice_number,
    }


def _reasons(ctx: Context, inv: XeroInvoice, h: Hypothesis) -> list[dict]:
    rs: list[dict] = []
    client = h.orders[0].client_name
    if h.known_name:
        rs.append({"key": "client", "label": "Client", "ok": True,
                   "detail": f"“{inv.contact_name}” is the name this client has been invoiced under before."})
    elif h.name_sim >= AUTO_MIN_NAME:
        rs.append({"key": "client", "label": "Client", "ok": True,
                   "detail": f"Names match: invoice to “{inv.contact_name}”, booking for “{client}”."})
    elif h.name_sim >= 60:
        rs.append({"key": "client", "label": "Client", "ok": None,
                   "detail": f"Names are similar but not the same: invoice to “{inv.contact_name}”, booking for “{client}”."})
    else:
        rs.append({"key": "client", "label": "Client", "ok": False,
                   "detail": f"Invoice is to “{inv.contact_name}” but the booking is for “{client}” - perhaps an agency."})
    net = invoice_gbp_net(inv)
    cur = inv.currency or "GBP"
    values = [float(o.value_gbp) for o in h.orders]
    if h.kind == "sum":
        parts = " + ".join(_money(v) for v in values)
        rs.append({"key": "amount", "label": "Amount", "ok": True,
                   "detail": f"{len(values)} bookings add up to the invoice: {parts} = {_money(sum(values))} before VAT."})
    elif cur == "GBP":
        rs.append({"key": "amount", "label": "Amount", "ok": True,
                   "detail": f"{_money(net)} before VAT on the invoice equals the booking's {_money(values[0])}."})
    else:
        rs.append({"key": "amount", "label": "Amount", "ok": True,
                   "detail": f"{cur} {float(inv.sub_total or 0):,.0f} before VAT is about {_money(net)} - the booking is {_money(values[0])}."})
    if h.cue_issue:
        rs.append({"key": "issue", "label": "Issue", "ok": True, "detail": f"The invoice mentions “{h.cue_issue}”."})
    elif h.cue_title:
        rs.append({"key": "issue", "label": "Issue", "ok": None, "detail": "The invoice names the title but not the issue."})
    else:
        rs.append({"key": "issue", "label": "Issue", "ok": None, "detail": "The invoice doesn't say which issue it's for."})
    if h.days is not None:
        word = "after" if h.days >= 0 else "before"
        what = "the booking" if h.orders[0].booked_on else "the issue date"
        ok = -20 <= h.days <= 90
        rs.append({"key": "timing", "label": "Timing", "ok": True if ok else None,
                   "detail": f"Invoiced {abs(h.days)} day{'s' if abs(h.days) != 1 else ''} {word} {what}."})
    return rs


def invoice_facts(inv: XeroInvoice) -> dict:
    due = float(inv.amount_due or 0)
    state = ("voided" if inv.status in ("VOIDED", "DELETED") else "paid" if due <= 0
             else "overdue" if inv.due_on and inv.due_on < date.today()
             else "part_paid" if float(inv.amount_paid or 0) > 0 else "unpaid")
    return {
        "id": str(inv.id), "number": inv.invoice_number, "contact": inv.contact_name, "reference": inv.reference,
        "lines": inv.line_text, "issued_on": inv.issued_on.isoformat() if inv.issued_on else None,
        "due_on": inv.due_on.isoformat() if inv.due_on else None, "currency": inv.currency or "GBP",
        "net": float(inv.sub_total or 0), "vat": float(inv.total_tax or 0), "total": float(inv.total or 0),
        "amount_due": float(inv.amount_due or 0), "state": state, "status": inv.status,
        "url": XERO_INVOICE_URL.format(inv.xero_id),
    }


def candidate_payload(ctx: Context, inv: XeroInvoice, hyps: list[Hypothesis], rep_names: dict) -> list[dict]:
    out = []
    for i, h in enumerate(hyps[:MAX_CANDIDATES]):
        strength = ("strong" if h.name_sim >= AUTO_MIN_NAME and (h.cue_issue or i == 0 and len(hyps) == 1)
                    else "likely" if h.name_sim >= 60 else "possible")
        out.append({
            "key": str(uuid.uuid4()), "kind": h.kind, "strength": strength,
            "bookings": [_booking_facts(ctx, o, rep_names) for o in h.orders],
            "total_gbp": round(sum(float(o.value_gbp) for o in h.orders), 2),
            "reasons": _reasons(ctx, inv, h),
        })
    return out


# ---- linking / unlinking -----------------------------------------------------------------

_AUDIT = ("invoice_number", "invoice_value_gbp", "invoiced_on", "xero_link")


def link_bookings(db: Session, inv: XeroInvoice, orders: list[SalesOrder], source: str,
                  user_id: uuid.UUID | None) -> None:
    """Records, on each booking, which Xero invoice it belongs to: the
    invoice number, the invoiced value and date (what staff used to type),
    and the real link. Every field change goes to the booking's history."""
    now = datetime.now(timezone.utc)
    single = len(orders) == 1
    who = {"auto": "automatically", "confirmed": "after a person confirmed it", "typed": "from the typed number"}[source]
    for o in orders:
        before = {"invoice_number": o.invoice_number, "invoice_value_gbp": o.invoice_value_gbp,
                  "invoiced_on": o.invoiced_on, "xero_link": None}
        o.invoice_number = inv.invoice_number
        o.invoice_value_gbp = round(invoice_gbp_net(inv) or float(o.value_gbp), 2) if single else float(o.value_gbp)
        o.invoiced_on = inv.issued_on or now.date()
        o.xero_invoice_id, o.xero_link_source, o.xero_linked_at = inv.id, source, now
        record_field_changes(
            db, entity_type="sales_order", entity_id=o.id, before=before,
            updates={"invoice_number": o.invoice_number, "invoice_value_gbp": o.invoice_value_gbp,
                     "invoiced_on": o.invoiced_on,
                     "xero_link": f"Linked {who} to Xero invoice {inv.invoice_number}"},
            changed_by_user_id=user_id)
        o.updated_at = now


def unlink_order(db: Session, o: SalesOrder, user_id: uuid.UUID | None) -> None:
    """Undo a link made by the matcher: clears the number, value, date and
    link it filled in."""
    if o.xero_link_source not in ("auto", "confirmed"):
        raise ValueError("Only links made by the invoice matcher can be undone here - edit the invoice number by hand instead.")
    before = {"invoice_number": o.invoice_number, "invoice_value_gbp": o.invoice_value_gbp,
              "invoiced_on": o.invoiced_on, "xero_link": "linked"}
    o.invoice_number = o.invoice_value_gbp = o.invoiced_on = None
    o.xero_invoice_id = o.xero_link_source = o.xero_linked_at = None
    record_field_changes(db, entity_type="sales_order", entity_id=o.id, before=before,
                         updates={"invoice_number": None, "invoice_value_gbp": None, "invoiced_on": None,
                                  "xero_link": "Link to the Xero invoice removed"},
                         changed_by_user_id=user_id)
    o.updated_at = datetime.now(timezone.utc)


def sync_link_after_edit(db: Session, o: SalesOrder) -> None:
    """Called when someone edits a booking's invoice number by hand: keep
    the real link in step with what was typed."""
    key = number_key(o.invoice_number)
    if not key:
        o.xero_invoice_id = o.xero_link_source = o.xero_linked_at = None
        return
    inv = db.scalars(select(XeroInvoice).where(XeroInvoice.number_key == key)
                     .order_by(XeroInvoice.updated_at_xero.desc().nulls_last())).first()
    if inv and o.xero_invoice_id != inv.id:
        o.xero_invoice_id, o.xero_link_source, o.xero_linked_at = inv.id, "typed", datetime.now(timezone.utc)
    elif not inv:
        o.xero_invoice_id = o.xero_link_source = o.xero_linked_at = None


def unclaimed_invoices(db: Session) -> list[XeroInvoice]:
    """Sales invoices in Xero that no booking has: not void, not a draft,
    no booking linked to it and no booking typed with its number."""
    claimed_ids = select(SalesOrder.xero_invoice_id).where(SalesOrder.xero_invoice_id.isnot(None))
    typed = {number_key(n) for (n,) in db.execute(select(SalesOrder.invoice_number).where(SalesOrder.invoice_number.isnot(None)))}
    rows = db.scalars(select(XeroInvoice).where(
        XeroInvoice.status.notin_(("VOIDED", "DELETED", "DRAFT")),
        XeroInvoice.id.notin_(claimed_ids))).all()
    return [i for i in rows if i.number_key not in typed]
