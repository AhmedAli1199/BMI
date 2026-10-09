"""Is a booking New Business? BMI's rule: the customer company has not spent with
BMI, on any product or service, in the previous 24 months.

- "Spent" = a live booking with a value, on any title (cancelled, contra and £0
  bookings don't count), or a paid Xero invoice to that customer.
- "Same customer" = the same CRM company, or the same client name once tidied
  ("Monty's" = "Montys Ltd"), or a name that customer has been invoiced under.
- The first deal is everything on the new customer's first invoice: a later booking
  counts as new only when it's on the same invoice number as their first booking
  (Matt, Oct 2026). Bookings made the same day as the first one count too.
  (settings.first_deal_rule="days" uses first_deal_days instead.)
- A similar name that did spend recently (e.g. "Delta" vs "Delta Air Lines")
  isn't decided automatically: the booking is marked "check" for a manager.
- A decision on a booking (SalesOrder.new_business_override) always wins: the
  salesperson ticks "New business" themselves and a manager checks it monthly.
"""
from __future__ import annotations

import bisect
import uuid
from dataclasses import dataclass, field
from datetime import date

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SalesEdition, SalesOrder, SalesOrderCredit, SalesRep, SalesTitle, XeroInvoice
from app.sales.analytics import BOOKED
from app.sales.invoice_numbers import canonical
from app.sales.matching import normalise


@dataclass
class Spend:
    day: date
    label: str
    value: float
    order_id: uuid.UUID | None = None
    invoice: str | None = None


@dataclass
class Verdict:
    status: str                  # new | returning | check
    reason: str
    decided_by: str = "history"  # history | manager | salesperson
    run_start: date | None = None  # first day of this new-business run (for once-per-customer bonuses)
    customer: str = ""           # the customer group's key
    last: dict | None = None
    similar: str | None = None
    limited_history: bool = False


def _months_back(d: date, months: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 - months, 12)
    m += 1
    from calendar import monthrange
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def order_day(o: SalesOrder, ed: SalesEdition | None) -> date | None:
    return o.booked_on or (ed.edition_date if ed else None) or (o.created_at.date() if o.created_at else None)


class _Groups:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


@dataclass
class NewBusinessIndex:
    lookback_months: int = 24
    first_deal_days: int = 0
    first_deal_rule: str = "invoice"
    rep_users: dict = field(default_factory=dict)                  # order id -> logins of the salespeople credited on it
    groups: _Groups = field(default_factory=_Groups)
    spends: dict[str, list[Spend]] = field(default_factory=dict)   # group -> sorted by day
    names: dict[str, str] = field(default_factory=dict)            # tidied name -> a display name
    earliest: date | None = None
    _spaced: dict | None = None

    def key_for(self, company_id: uuid.UUID | None, client_name: str) -> str:
        n = normalise(client_name) or client_name.strip().lower()
        if company_id:
            self.groups.union(f"c:{company_id}", f"n:{n}")
            return self.groups.find(f"c:{company_id}")
        return self.groups.find(f"n:{n}")

    @classmethod
    def build(cls, db: Session, *, lookback_months: int = 24, first_deal_days: int = 0, first_deal_rule: str = "invoice") -> "NewBusinessIndex":
        ix = cls(lookback_months=lookback_months, first_deal_days=first_deal_days, first_deal_rule=first_deal_rule)
        for oid, uid in db.execute(select(SalesOrderCredit.order_id, SalesRep.user_id).join(SalesRep, SalesOrderCredit.rep_id == SalesRep.id)
                                   .where(SalesRep.user_id.isnot(None))):
            ix.rep_users.setdefault(oid, set()).add(uid)
        titles = {t.id: t for t in db.scalars(select(SalesTitle))}
        rows = db.execute(select(SalesOrder, SalesEdition).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)).all()
        raw: list[tuple[str, Spend]] = []
        for o, ed in rows:
            n = normalise(o.client_name) or o.client_name.strip().lower()
            node = f"n:{n}"
            ix.groups.find(node)
            if o.company_id:
                ix.groups.union(f"c:{o.company_id}", node)
            ix.names.setdefault(n, o.client_name)
            d = order_day(o, ed)
            if d and (ix.earliest is None or d < ix.earliest):
                ix.earliest = d
            if o.status == BOOKED and float(o.value_gbp or 0) > 0 and d:
                t = titles.get(ed.title_id)
                raw.append((node, Spend(d, f"{t.name if t else ''} {ed.name}".strip(), float(o.value_gbp), o.id, canonical(o.invoice_number))))
        # Names a customer has been invoiced under in Xero join that customer.
        for o_cid, o_name, contact in db.execute(
                select(SalesOrder.company_id, SalesOrder.client_name, XeroInvoice.contact_name)
                .join(XeroInvoice, SalesOrder.xero_invoice_id == XeroInvoice.id)):
            if contact:
                ix.groups.union(f"n:{normalise(o_name) or o_name.strip().lower()}", f"n:{normalise(contact) or contact.strip().lower()}")
        for inv in db.scalars(select(XeroInvoice).where(XeroInvoice.status.notin_(("VOIDED", "DELETED", "DRAFT")))):
            if inv.contact_name and inv.issued_on and float(inv.amount_paid or 0) > 0:
                n = normalise(inv.contact_name) or inv.contact_name.strip().lower()
                ix.names.setdefault(n, inv.contact_name)
                raw.append((f"n:{n}", Spend(inv.issued_on, f"Xero invoice {inv.invoice_number}", float(inv.sub_total or 0), invoice=canonical(inv.invoice_number))))
        for node, sp in raw:
            ix.spends.setdefault(ix.groups.find(node), []).append(sp)
        for v in ix.spends.values():
            v.sort(key=lambda s: s.day)
        return ix

    def _prior(self, group: str, day: date, exclude: uuid.UUID | None = None) -> list[Spend]:
        lst = self.spends.get(group, [])
        start = _months_back(day, self.lookback_months)
        lo = bisect.bisect_left([s.day for s in lst], start)
        return [s for s in lst[lo:] if s.day < day and s.order_id != exclude]

    def _run_start(self, group: str, day: date, exclude: uuid.UUID | None) -> date:
        """Walks back to the first day of the spell that has no spend in the 24 months before it."""
        current = day
        while True:
            prior = self._prior(group, current, exclude)
            if not prior:
                return current
            current = prior[0].day

    def classify(self, o: SalesOrder, ed: SalesEdition | None) -> Verdict:
        day = order_day(o, ed) or date.today()
        group = self.key_for(o.company_id, o.client_name)
        limited = bool(self.earliest and _months_back(day, self.lookback_months) < self.earliest)
        if o.new_business_override is not None:
            by = "salesperson" if o.new_business_set_by_user_id in self.rep_users.get(o.id, ()) else "manager"
            who = "the salesperson" if by == "salesperson" else "a manager"
            return Verdict("new" if o.new_business_override else "returning",
                           o.new_business_reason or (f"Ticked as new business by {who}" if o.new_business_override else f"Marked as not new business by {who}"),
                           decided_by=by, run_start=day, customer=group)
        prior = self._prior(group, day, o.id)
        if prior:
            start = self._run_start(group, day, o.id)
            last = prior[-1]
            mine = canonical(o.invoice_number)
            if self.first_deal_rule == "invoice":
                firsts = [s for s in self.spends.get(group, []) if s.day == start and s.order_id != o.id]
                if mine and any(s.invoice == mine for s in firsts) and not self._prior(group, start, o.id):
                    return Verdict("new", f"On the same invoice ({o.invoice_number}) as the new customer's first booking on {start.day} {start:%b %Y}",
                                   run_start=start, customer=group, limited_history=limited)
            elif (day - start).days <= self.first_deal_days and not self._prior(group, start, o.id):
                when = "the same day as" if day == start else f"{(day - start).days} days after"
                return Verdict("new", f"Part of a new customer's first deal (booked {when} their first booking on {start.day} {start:%b %Y})",
                               run_start=start, customer=group, limited_history=limited)
            return Verdict("returning", f"Returning: last spent {last.label}, {last.day.day} {last.day:%b %Y}, £{last.value:,.0f}",
                           customer=group, last={"label": last.label, "day": last.day.isoformat(), "value": last.value,
                                                 "order_id": str(last.order_id) if last.order_id else None})
        # No spend for this customer - but is a similar name a recent spender?
        from app.sales.invoice_match import norm

        mine = norm(o.client_name)
        similar = None
        if len(mine) >= 4:
            start = _months_back(day, self.lookback_months)
            if self._spaced is None:
                self._spaced = {k: norm(v) for k, v in self.names.items()}
            for _, score, name in process.extract(mine, self._spaced, scorer=fuzz.token_set_ratio, score_cutoff=90, limit=8):
                if self.groups.find(f"n:{name}") == group:
                    continue
                g = self.groups.find(f"n:{name}")
                if any(start <= s.day < day for s in self.spends.get(g, [])):
                    similar = self.names.get(name, name)
                    break
        since = _months_back(day, self.lookback_months)
        if similar:
            return Verdict("check", f"No spend under this name since {since.day} {since:%b %Y}, but “{similar}” has spent with BMI recently. Is it the same customer?",
                           customer=group, similar=similar, run_start=day, limited_history=limited)
        return Verdict("new", f"New business: no spend found since {since.day} {since:%b %Y}" + (" (the register starts in "
                       f"{self.earliest:%b %Y})" if limited else ""), run_start=day, customer=group, limited_history=limited)
