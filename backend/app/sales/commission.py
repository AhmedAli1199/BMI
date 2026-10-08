"""Works out a salesperson's commission for a month, line by line, from the order
register and their plan (app/models/commission.py). Every figure carries the rule
and the reason that produced it, so a statement can be checked by the person paid.

A booking counts in the month it's earned: by default the month its issue
publishes or its event runs (settings.earned_on="booked" uses the booking date).
Personal revenue is the salesperson's credited share of the booking, after any
agency's cut. Approved statements are frozen; a later change to a paid month shows
up as an adjustment on the next statement.
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (CommissionRule, CommissionSettings, CommissionStatement, SalesEdition, SalesEditionCost, SalesOrder,
                        SalesOrderCredit, SalesRep, SalesTitle)
from app.sales.analytics import BOOKED
from app.sales.new_business import NewBusinessIndex

FALLBACK = "Not in their plan"


def settings(db: Session) -> CommissionSettings:
    st = db.get(CommissionSettings, 1)
    if not st:
        st = CommissionSettings(id=1, earned_on="publication", lookback_months=24, first_deal_days=0, event_profit_basis="all", fallback_flag=True)
        db.add(st)
        db.flush()
    return st


def period_bounds(period: str) -> tuple[date, date]:
    y, m = (int(x) for x in period.split("-"))
    return date(y, m, 1), date(y, m, monthrange(y, m)[1])


def _r(v: float) -> float:
    return round(v + 0.0, 2)


@dataclass
class Ctx:
    db: Session
    st: CommissionSettings
    ix: NewBusinessIndex
    titles: dict
    editions: dict

    @classmethod
    def build(cls, db: Session) -> "Ctx":
        st = settings(db)
        return cls(db, st, NewBusinessIndex.build(db, lookback_months=st.lookback_months, first_deal_days=st.first_deal_days),
                   {t.id: t for t in db.scalars(select(SalesTitle))}, {})

    def edition(self, eid: uuid.UUID) -> SalesEdition:
        if eid not in self.editions:
            self.editions[eid] = self.db.get(SalesEdition, eid)
        return self.editions[eid]

    def earned_on(self, o: SalesOrder, ed: SalesEdition) -> date | None:
        if self.st.earned_on == "booked":
            return o.booked_on or ed.edition_date
        return ed.edition_date or o.booked_on


def _label(t: SalesTitle, ed: SalesEdition) -> str:
    from app.api.routes.sales import edition_label
    return edition_label(t, ed)


def _rules(db: Session, rep: SalesRep, day: date | None = None) -> list[CommissionRule]:
    rules = db.scalars(select(CommissionRule).where(CommissionRule.rep_id == rep.id).order_by(CommissionRule.sort_order, CommissionRule.name)).all()
    if day:
        rules = [r for r in rules if (not r.valid_from or r.valid_from <= day) and (not r.valid_until or day <= r.valid_until)]
    return list(rules)


def _rule_for(rules: list[CommissionRule], slug: str) -> CommissionRule | None:
    return next((r for r in rules if slug in (r.title_slugs or [])), None)


def _share(o: SalesOrder, credit: float) -> float:
    """The salesperson's credit after any agency's cut (the cut comes off each share in proportion)."""
    value, agency = float(o.value_gbp or 0), float(o.agency_commission_gbp or 0)
    if value > 0 and agency > 0:
        return credit * max(0.0, value - agency) / value
    return credit


def core(ctx: Ctx, rep: SalesRep, period: str) -> dict:
    """Everything earned in one month (no adjustments for earlier months)."""
    db, start, end = ctx.db, *period_bounds(period)
    all_rules = _rules(db, rep)
    lines, bonuses, events, flags = [], [], [], []
    rows = db.execute(select(SalesOrderCredit, SalesOrder, SalesEdition)
                      .join(SalesOrder, SalesOrderCredit.order_id == SalesOrder.id)
                      .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
                      .where(SalesOrderCredit.rep_id == rep.id, SalesOrder.status == BOOKED)).all()
    new_customers: dict[str, dict] = {}
    for credit, o, ed in rows:
        day = ctx.earned_on(o, ed)
        if not day or not (start <= day <= end):
            continue
        ctx.editions[ed.id] = ed
        t = ctx.titles[ed.title_id]
        rules = [r for r in all_rules if (not r.valid_from or r.valid_from <= day) and (not r.valid_until or day <= r.valid_until)]
        rule = _rule_for(rules, t.slug)
        share = _share(o, float(credit.amount_gbp or 0))
        verdict = ctx.ix.classify(o, ed)
        line_flags = []
        if o.commission_rate is not None:
            base_rate, base_src = float(o.commission_rate), "Rate set on this booking"
        elif rule:
            base_rate, base_src = float(rule.base_rate), rule.name
        else:
            base_rate, base_src = float(rep.commission_rate or 0), FALLBACK
            line_flags.append(f"{t.name} isn't in {rep.name}'s plan, so the standard {base_rate:.1%} is used. Add it to their plan if that's wrong.")
        nb_rate = 0.0
        if rule and verdict.status == "new":
            nb_rate = float(rule.new_business_rate or 0)
            pub = ed.edition_date or day
            if rule.new_business_rate_change_on and rule.new_business_rate_after is not None and pub >= rule.new_business_rate_change_on:
                nb_rate = float(rule.new_business_rate_after)
        base_amt, nb_amt = share * base_rate, share * nb_rate
        line = {
            "order_id": str(o.id), "edition_id": str(ed.id), "edition": _label(t, ed), "title": t.name, "title_slug": t.slug,
            "group": rule.name if rule else FALLBACK, "publication": ed.edition_date.isoformat() if ed.edition_date else None,
            "earned_on": day.isoformat(), "booked_on": o.booked_on.isoformat() if o.booked_on else None,
            "client": o.client_name, "company_id": str(o.company_id) if o.company_id else None, "size": o.size,
            "value_gbp": float(o.value_gbp or 0), "share_gbp": _r(share), "split": abs(float(credit.amount_gbp or 0) - float(o.value_gbp or 0)) > 0.01,
            "agency_cut": float(o.agency_commission_gbp or 0) > 0,
            "base_rate": base_rate, "base_source": base_src, "base_gbp": _r(base_amt),
            "new_business": verdict.status, "new_business_reason": verdict.reason, "new_business_decided_by": verdict.decided_by,
            "new_business_rate": nb_rate, "new_business_gbp": _r(nb_amt), "commission_gbp": _r(base_amt + nb_amt), "flags": line_flags,
        }
        lines.append(line)
        if verdict.status == "new" and rule and rule.new_client_bonus_gbp:
            prev = new_customers.get(verdict.customer)
            if not prev or (o.booked_on or day) < prev["day"]:
                new_customers[verdict.customer] = {"day": o.booked_on or day, "client": o.client_name, "rule": rule, "order_id": str(o.id)}
    # £ per new customer, once: skipped when the same customer already earned it in an earlier month
    for key, c in list(new_customers.items()):
        for credit, o, ed in rows:
            d = ctx.earned_on(o, ed)
            if d and d < start and ctx.ix.key_for(o.company_id, o.client_name) == key and ctx.ix.classify(o, ed).status == "new" \
                    and _rule_for(all_rules, ctx.titles[ed.title_id].slug) is c["rule"]:
                new_customers.pop(key)
                break
    for c in new_customers.values():
        bonuses.append({"kind": "new_client", "label": f"New business bonus: {c['client']}", "group": c["rule"].name,
                        "amount_gbp": float(c["rule"].new_client_bonus_gbp), "order_id": c["order_id"],
                        "reason": f"{c['client']} is a new customer"})
    # New contract-publishing guides sold by this person, in the month the guide publishes
    for ed in db.scalars(select(SalesEdition).where(SalesEdition.new_contract_guide.is_(True), SalesEdition.new_contract_rep_id == rep.id)):
        d = ed.edition_date
        if not d or not (start <= d <= end):
            continue
        t = ctx.titles[ed.title_id]
        rule = _rule_for(_rules(db, rep, d), t.slug) or next((r for r in all_rules if r.new_guide_bonus_gbp), None)
        if rule and rule.new_guide_bonus_gbp:
            bonuses.append({"kind": "new_guide", "label": f"New contract-publishing guide: {_label(t, ed)}", "group": rule.name,
                            "amount_gbp": float(rule.new_guide_bonus_gbp), "edition_id": str(ed.id),
                            "reason": "Marked as a new contract-publishing guide on its edition page"})
    # Revenue thresholds (e.g. a newsletter passing £8,000 in a calendar year), per title, paid in the month it's passed
    for rule in all_rules:
        if not (rule.threshold_bonus_gbp and rule.threshold_gbp):
            continue
        ystart = date(start.year, 1, 1)
        for slug in rule.title_slugs or []:
            before = during = 0.0
            for credit, o, ed in rows:
                t = ctx.titles[ed.title_id]
                d = ctx.earned_on(o, ed)
                if t.slug != slug or not d or d < ystart or d > end:
                    continue
                amt = _share(o, float(credit.amount_gbp or 0))
                if d < start:
                    before += amt
                else:
                    during += amt
            limit = float(rule.threshold_gbp)
            if before <= limit < before + during:
                name = next((t.name for t in ctx.titles.values() if t.slug == slug), slug)
                bonuses.append({"kind": "threshold", "label": f"{name} passed £{limit:,.0f} in {start.year}", "group": rule.name,
                                "amount_gbp": float(rule.threshold_bonus_gbp),
                                "reason": f"Their {name} revenue this year reached £{before + during:,.0f}"})
    # Event profit share: events signed off this month
    for rule in all_rules:
        if not rule.event_profit_rate:
            continue
        slugs = set(rule.title_slugs or [])
        ids = [t.id for t in ctx.titles.values() if t.slug in slugs]
        eds = db.scalars(select(SalesEdition).where(SalesEdition.title_id.in_(ids), SalesEdition.costs_signed_off_at.isnot(None))).all() if ids else []
        for ed in eds:
            signed = ed.costs_signed_off_at.date()
            if not (start <= signed <= end):
                continue
            orders = db.execute(select(SalesOrder).where(SalesOrder.edition_id == ed.id, SalesOrder.status == BOOKED)).scalars().all()
            if ctx.st.event_profit_basis == "own":
                cr = {c.order_id: float(c.amount_gbp or 0) for c in db.scalars(select(SalesOrderCredit).where(
                    SalesOrderCredit.rep_id == rep.id, SalesOrderCredit.order_id.in_([o.id for o in orders])))} if orders else {}
                income = sum(_share(o, cr.get(o.id, 0)) for o in orders)
            else:
                income = sum(_share(o, float(o.value_gbp or 0)) for o in orders)
            costs = sum(float(c.amount_gbp or 0) for c in db.scalars(select(SalesEditionCost).where(
                SalesEditionCost.edition_id == ed.id, SalesEditionCost.kind == "cost")))
            profit = income - costs
            t = ctx.titles[ed.title_id]
            events.append({"edition_id": str(ed.id), "edition": _label(t, ed), "event_date": ed.edition_date.isoformat() if ed.edition_date else None,
                           "income_gbp": _r(income), "costs_gbp": _r(costs), "profit_gbp": _r(profit), "rate": float(rule.event_profit_rate),
                           "amount_gbp": _r(max(0.0, profit) * float(rule.event_profit_rate)), "group": rule.name,
                           "basis": "the whole event's income" if ctx.st.event_profit_basis == "all" else "their own sales on the event",
                           "loss": profit < 0})
    lines.sort(key=lambda x: (x["group"], x["earned_on"], x["client"].lower()))
    groups = defaultdict(lambda: {"share_gbp": 0.0, "base_gbp": 0.0, "new_business_gbp": 0.0, "commission_gbp": 0.0, "bookings": 0})
    for ln in lines:
        g = groups[ln["group"]]
        for k in ("share_gbp", "base_gbp", "new_business_gbp", "commission_gbp"):
            g[k] += ln[k]
        g["bookings"] += 1
    totals = {
        "share_gbp": _r(sum(ln["share_gbp"] for ln in lines)), "base_gbp": _r(sum(ln["base_gbp"] for ln in lines)),
        "new_business_gbp": _r(sum(ln["new_business_gbp"] for ln in lines)), "bonuses_gbp": _r(sum(b["amount_gbp"] for b in bonuses)),
        "event_profit_gbp": _r(sum(e["amount_gbp"] for e in events)),
    }
    totals["core_gbp"] = _r(totals["base_gbp"] + totals["new_business_gbp"] + totals["bonuses_gbp"] + totals["event_profit_gbp"])
    checks = [ln for ln in lines if ln["new_business"] == "check"]
    if not all_rules:
        flags.append(f"{rep.name} has no commission plan yet, so every booking uses the standard {float(rep.commission_rate or 0):.1%}.")
    return {"lines": lines, "bonuses": bonuses, "events": events, "totals": totals, "checks": len(checks),
            "groups": [{"name": k, **{kk: (_r(vv) if isinstance(vv, float) else vv) for kk, vv in v.items()}} for k, v in groups.items()],
            "flags": flags}


def statement(ctx: Ctx, rep: SalesRep, period: str) -> dict:
    """The month's statement: frozen if approved (with any change since shown), otherwise live with adjustments for
    earlier approved months whose figures have changed since they were paid."""
    db = ctx.db
    st = db.scalars(select(CommissionStatement).where(CommissionStatement.rep_id == rep.id, CommissionStatement.period == period)).first()
    if st:
        snap = dict(st.snapshot)
        live = core(ctx, rep, period)["totals"]["core_gbp"]
        snap["approved"] = {"at": st.approved_at.isoformat() if st.approved_at else None, "by": str(st.approved_by_user_id) if st.approved_by_user_id else None,
                            "changed_since_gbp": _r(live - float(snap["totals"]["core_gbp"]) - float(snap.get("carried_gbp", 0)))}
        return snap
    out = core(ctx, rep, period)
    adjustments = []
    for prev in db.scalars(select(CommissionStatement).where(CommissionStatement.rep_id == rep.id, CommissionStatement.period < period)
                           .order_by(CommissionStatement.period)):
        live = core(ctx, rep, prev.period)["totals"]["core_gbp"]
        diff = _r(live - float(prev.snapshot["totals"]["core_gbp"]) - float(prev.snapshot.get("carried_gbp", 0)))
        if abs(diff) >= 0.01:
            adjustments.append({"period": prev.period, "amount_gbp": diff,
                                "label": f"Change to {datetime.strptime(prev.period, '%Y-%m'):%B %Y} since it was approved"})
    out["adjustments"] = adjustments
    out["totals"]["adjustments_gbp"] = _r(sum(a["amount_gbp"] for a in adjustments))
    out["totals"]["total_gbp"] = _r(out["totals"]["core_gbp"] + out["totals"]["adjustments_gbp"])
    out["period"], out["rep_id"], out["approved"] = period, str(rep.id), None
    return out


def approve(ctx: Ctx, rep: SalesRep, period: str, user_id: uuid.UUID | None) -> CommissionStatement:
    db = ctx.db
    if db.scalars(select(CommissionStatement).where(CommissionStatement.rep_id == rep.id, CommissionStatement.period == period)).first():
        raise ValueError("This month is already approved.")
    if period >= date.today().strftime("%Y-%m"):
        raise ValueError("A month can be approved once it has ended.")
    s = statement(ctx, rep, period)
    if s["checks"]:
        raise ValueError(f"{s['checks']} booking{'s' if s['checks'] != 1 else ''} still need a decision on whether they're new business.")
    snap = {k: v for k, v in s.items() if k != "approved"}
    snap["carried_gbp"] = 0
    row = CommissionStatement(id=uuid.uuid4(), rep_id=rep.id, period=period, total_gbp=s["totals"]["total_gbp"], snapshot=snap,
                              approved_by_user_id=user_id, approved_at=datetime.now(timezone.utc))
    db.add(row)
    # adjustments paid on this statement now count as carried for the months they came from
    for adj in s["adjustments"]:
        prev = db.scalars(select(CommissionStatement).where(CommissionStatement.rep_id == rep.id, CommissionStatement.period == adj["period"])).first()
        if prev:
            prev.snapshot = {**prev.snapshot, "carried_gbp": _r(float(prev.snapshot.get("carried_gbp", 0)) + adj["amount_gbp"])}
    db.flush()
    return row
