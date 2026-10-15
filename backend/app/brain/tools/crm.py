"""CRM tools: find a client, a client at a glance (what they bought, at what rate, who they are, what was said),
search everything written about clients, and what's on my plate. All of it limited to what the asking person may
see on the contact and company pages; private notes only for whoever wrote them."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select

from app.brain import search as brain_search
from app.brain.registry import ToolEnv, ToolError, brain_tool
from app.core import visibility as vis
from app.models import Activity, CallRecording, Company, Contact, Email, Opportunity, Reminder, SalesDeal, SalesEdition, SalesOrder, SalesTitle
from app.sales.analytics import BOOKED, period_label, period_year_of

UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")


def need(env: ToolEnv, *sections: str) -> None:
    """Only what this person can open themselves (role + Settings > Sections) - see app/brain/access.py."""
    from app.brain.access import require_any
    require_any(env, *sections)


def _d(v) -> str | None:
    if not v:
        return None
    return (v if isinstance(v, date) else v.date() if isinstance(v, datetime) else v).strftime("%-d %b %Y")


def _companies(env: ToolEnv, name: str, limit: int = 8) -> list[Company]:
    stmt = select(Company).where(Company.name.ilike(f"%{name.strip()}%"))
    if (cl := vis.company_clause(env.db, env.identity)) is not None:
        stmt = stmt.where(cl)
    rows = env.db.scalars(stmt.order_by(func.length(Company.name)).limit(limit)).all()
    return rows


def _contacts(env: ToolEnv, q: str, limit: int = 8) -> list[Contact]:
    like = f"%{q.strip()}%"
    stmt = select(Contact).where(or_(Contact.full_name.ilike(like),
                                     Contact.id.in_(select(Email.contact_id).where(Email.address.ilike(like)))))
    if (cl := vis.contact_clause(env.db, env.identity)) is not None:
        stmt = stmt.where(cl)
    return env.db.scalars(stmt.order_by(func.length(Contact.full_name)).limit(limit)).all()


def _email(env: ToolEnv, contact_id) -> str | None:
    return env.db.scalar(select(Email.address).where(Email.contact_id == contact_id).limit(1))


@brain_tool("Looking for the client")
def crm_find(env: ToolEnv, query: str) -> dict:
    """Finds companies and people by name (or a person's email). Use it first when a client is named, to get
    the right record - if several match, ask which one.

    Args:
      query: part of a company name, a person's name or an email address
    """
    need(env, "contacts", "companies")
    if len((query or "").strip()) < 2:
        raise ToolError("Say a bit more of the name.")
    firms = _companies(env, query)
    people = _contacts(env, query)
    names = {c.id: c.name for c in env.db.scalars(select(Company).where(Company.id.in_([p.company_id for p in people if p.company_id])))} if people else {}
    return {
        "companies": [{"id": str(c.id), "name": c.name, "industry": c.industry or c.category, "link": f"/companies/{c.id}"} for c in firms],
        "people": [{"id": str(p.id), "name": p.full_name, "job_title": p.job_title, "company": names.get(p.company_id) or p.company_name_freetext,
                    "email": _email(env, p.id), "link": f"/contacts/{p.id}"} for p in people],
        "note": None if firms or people else "Nobody matches that you can see. Try a shorter part of the name, or check the spelling.",
    }


def _resolve(env: ToolEnv, client: str) -> tuple[Company | None, list[Company]]:
    c = (client or "").strip()
    if UUID_RE.match(c):
        co = env.db.get(Company, uuid.UUID(c))
        if co and vis.can_see_company(env.db, co.id, env.identity):
            return co, []
        person = env.db.get(Contact, uuid.UUID(c))
        if person and person.company_id and vis.can_see_contact(env.db, person.id, env.identity):
            return env.db.get(Company, person.company_id), []
        raise ToolError("That record doesn't exist or this person can't see it.")
    hits = _companies(env, c, 6)
    exact = [h for h in hits if h.name.lower() == c.lower()]
    if exact:
        return exact[0], []
    if len(hits) == 1:
        return hits[0], []
    return None, hits


@brain_tool("Looking at the client")
def crm_client_snapshot(env: ToolEnv, client: str) -> dict:
    """Everything about one client at a glance: who they are, their people, what they've bought (latest first, with
    the rate paid), totals by year, their bookings, open opportunities, what's coming up, and the latest notes
    and call notes. Use it for "what did X last buy", "what's their budget", "when did we last speak".

    Args:
      client: the company name, or a company/contact id from crm_find or the page
    """
    need(env, "companies", "contacts", "bookings", "orders")
    co, choices = _resolve(env, client)
    if not co and choices:
        return {"which_one": [{"id": str(c.id), "name": c.name, "link": f"/companies/{c.id}"} for c in choices],
                "note": "Several companies match - ask which one (or use the id)."}
    db = env.db
    name = co.name if co else client.strip()
    item_filter = (SalesOrder.company_id == co.id) if co else SalesOrder.client_name.ilike(f"%{name}%")
    if not co and not db.scalar(select(SalesOrder.id).where(item_filter).limit(1)):
        raise ToolError(f"No client called {client!r} that this person can see. Try crm_find with part of the name.")

    rows = db.execute(select(SalesOrder, SalesEdition, SalesTitle).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
                      .join(SalesTitle, SalesEdition.title_id == SalesTitle.id)
                      .where(item_filter, SalesOrder.status.in_((BOOKED, "pencilled")))
                      .order_by(func.coalesce(SalesOrder.item_date, SalesEdition.edition_date).desc().nulls_last(), SalesOrder.booked_on.desc().nulls_last())
                      .limit(60)).all()
    bought = [{"edition": f"{t.name} · {e.name}", "runs": _d(o.item_date or e.edition_date), "what": o.size or o.series or o.position,
               "value_gbp": float(o.value_gbp or 0), "status": o.status, "booked_on": _d(o.booked_on),
               "invoice": o.invoice_number, "link": f"/sales/orders/{o.id}"} for o, e, t in rows]
    paid = [b for b in bought if b["status"] == BOOKED and b["value_gbp"] > 0]
    from app.brain.metrics import year_basis
    financial, start = year_basis(db, None)
    by_year: dict[str, float] = {}
    for o, e, _t in rows:
        if o.status != BOOKED:
            continue
        d = o.item_date or e.edition_date or date(e.year, 1, 1)
        y = period_year_of(d, financial, start) if financial else e.year
        label = period_label(y, financial, start)
        by_year[label] = round(by_year.get(label, 0) + float(o.value_gbp or 0), 2)

    out: dict = {
        "client": name, "link": f"/companies/{co.id}" if co else f"/sales/bookings?q={name}",
        "about": {"industry": co.industry or co.category, "website": co.website, "region": co.region or co.territory} if co else None,
        "last_bought": paid[0] if paid else None,
        "recent_items": bought[:10], "more_items": max(0, len(bought) - 10),
        "booked_by_year": by_year, "year_basis": "financial years from July" if financial else "calendar years",
    }
    if co:
        people = db.scalars(select(Contact).where(Contact.company_id == co.id).order_by(Contact.last_reach_date.desc().nulls_last()).limit(8)).all()
        out["people"] = [{"name": p.full_name, "job_title": p.job_title, "email": _email(env, p.id), "link": f"/contacts/{p.id}"}
                         for p in people if vis.can_see_contact(db, p.id, env.identity)]
        deals = db.scalars(select(SalesDeal).where(SalesDeal.company_id == co.id).order_by(SalesDeal.number.desc()).limit(5)).all()
        out["bookings"] = [{"number": d.number, "status": d.status, "total_gbp": float(d.total_gbp or 0), "booked_on": _d(d.booked_on),
                            "link": f"/sales/deals/{d.id}"} for d in deals]
        opps = db.scalars(select(Opportunity).where(Opportunity.company_id == co.id).order_by(Opportunity.estimated_close_at.desc().nulls_last()).limit(5)).all()
        out["opportunities"] = [{"name": o.name, "status": o.status, "stage": o.stage_name, "value_gbp": o.total_amount,
                                 "expected_close": _d(o.estimated_close_at)} for o in opps]
        now = datetime.now(timezone.utc)
        ppl = select(Contact.id).where(Contact.company_id == co.id)
        acts = db.scalars(select(Activity).where(or_(Activity.company_id == co.id, Activity.contact_id.in_(ppl)), Activity.start_at >= now,
                                                 Activity.is_cleared.is_(False), or_(Activity.is_private.is_(False), Activity.created_by_user_id == env.identity.user_uuid))
                          .order_by(Activity.start_at).limit(5)).all()
        out["coming_up"] = [{"when": _d(a.start_at), "what": a.activity_type, "subject": a.subject} for a in acts]
        calls = db.scalars(select(CallRecording).where(CallRecording.company_id == co.id, CallRecording.status == "completed")
                           .order_by(CallRecording.created_at.desc()).limit(3)).all()
        out["calls"] = [{"title": c.title, "when": _d(c.started_at or c.created_at), "summary": ((c.notes or {}).get("summary") or "")[:400],
                         "link": f"/calls/{c.id}"} for c in calls]
        out["latest_notes"] = brain_search.search(db, env.identity, "", company_id=co.id, limit=5)
    return out


@brain_tool("Searching notes and history")
def crm_search_notes(env: ToolEnv, query: str, client: str = "", kinds: str = "", since: str = "", until: str = "") -> dict:
    """Searches everything written about clients - notes, history, activities, call notes, opportunities - by
    meaning and by exact words. Use for "budget", "who did they say", "why did they cancel", a rate or date.

    Args:
      query: what to look for, in a few words, e.g. "budget for next year" or "£2,500"
      client: optional company name or id to search only that client
      kinds: optional, comma separated: note, history, activity, call, opportunity
      since: optional earliest date, YYYY-MM-DD
      until: optional latest date, YYYY-MM-DD
    """
    need(env, "contacts", "companies")
    company_id = None
    if client.strip():
        co, choices = _resolve(env, client)
        if not co:
            return {"which_one": [{"id": str(c.id), "name": c.name} for c in choices] if choices else [],
                    "note": "Several companies match - ask which one." if choices else f"No client called {client!r}."}
        company_id = co.id

    def day(s: str, end: bool = False):
        if not s.strip():
            return None
        try:
            d = date.fromisoformat(s.strip()[:10])
        except ValueError:
            raise ToolError("Dates look like 2025-03-31.")
        return datetime(d.year, d.month, d.day, 23 if end else 0, 59 if end else 0, tzinfo=timezone.utc)
    hits = brain_search.search(env.db, env.identity, query, company_id=company_id,
                               kinds=[k.strip() for k in kinds.split(",") if k.strip()] or None, since=day(since), until=day(until, True))
    return {"results": hits, "note": None if hits else "Nothing written about that which this person can see."}


@brain_tool("Checking your diary")
def crm_my_day(env: ToolEnv, days: int = 7) -> dict:
    """The asking person's own open reminders (including overdue ones) and their activities for the next few days.

    Args:
      days: how many days ahead to look (1-31)
    """
    need(env, "reminders", "calendar")
    me = env.identity.user_uuid
    if not me:
        raise ToolError("I don't know who's asking, so I can't look at a diary.")
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=max(1, min(int(days or 7), 31)))
    rems = env.db.scalars(select(Reminder).where(Reminder.user_id == me, Reminder.status == "open", Reminder.due_at <= end)
                          .order_by(Reminder.due_at).limit(20)).all()
    acts = env.db.scalars(select(Activity).where(Activity.created_by_user_id == me, Activity.start_at >= now - timedelta(hours=1),
                                                 Activity.start_at <= end, Activity.is_cleared.is_(False)).order_by(Activity.start_at).limit(20)).all()
    return {
        "reminders": [{"due": _d(r.due_at), "overdue": r.due_at < now or None, "note": (r.note or "")[:200],
                       "link": f"/companies/{r.company_id}" if r.company_id else f"/contacts/{r.contact_id}" if r.contact_id else "/reminders"} for r in rems],
        "activities": [{"when": a.start_at.strftime("%a %-d %b %H:%M"), "what": a.activity_type, "subject": a.subject} for a in acts],
        "see_all": "/reminders",
    }


@brain_tool("Looking at the person")
def crm_contact(env: ToolEnv, person: str) -> dict:
    """One person in the CRM: job, company, emails and phones, the groups they're in, when they were last
    contacted, their next activity and the latest notes about them.

    Args:
      person: their name or email, or a contact id from crm_find or the page
    """
    need(env, "contacts")
    from app.models import Group, GroupMembership, Phone
    p = (person or "").strip()
    if UUID_RE.match(p):
        c = env.db.get(Contact, uuid.UUID(p))
        if not c or not vis.can_see_contact(env.db, c.id, env.identity):
            raise ToolError("That person doesn't exist or this person can't see them.")
        people = [c]
    else:
        people = _contacts(env, p, 6)
    if not people:
        raise ToolError(f"Nobody called {person!r} that this person can see.")
    if len(people) > 1 and not any((x.full_name or "").lower() == p.lower() for x in people):
        return {"which_one": [{"id": str(x.id), "name": x.full_name, "job_title": x.job_title, "link": f"/contacts/{x.id}"} for x in people]}
    c = next((x for x in people if (x.full_name or "").lower() == p.lower()), people[0])
    db = env.db
    co = db.get(Company, c.company_id) if c.company_id else None
    groups = db.scalars(select(Group).join(GroupMembership, GroupMembership.group_id == Group.id).where(GroupMembership.contact_id == c.id).limit(12)).all()
    now = datetime.now(timezone.utc)
    nxt = db.scalar(select(Activity).where(Activity.contact_id == c.id, Activity.start_at >= now, Activity.is_cleared.is_(False))
                    .order_by(Activity.start_at).limit(1))
    return {
        "name": c.full_name, "job_title": c.job_title, "company": co.name if co else c.company_name_freetext,
        "company_link": f"/companies/{co.id}" if co else None, "link": f"/contacts/{c.id}",
        "emails": [e for e in db.scalars(select(Email.address).where(Email.contact_id == c.id).limit(4))],
        "phones": [ph for ph in db.scalars(select(Phone.number).where(Phone.contact_id == c.id).limit(4))],
        "groups": [g.name for g in groups],
        "last_contacted": {"meeting": _d(c.last_meet_date), "spoke": _d(c.last_reach_date), "email": _d(c.last_email_date),
                           "letter": _d(c.last_letter_date)},
        "unsubscribed": c.is_unsubscribed or c.is_email_opted_out or None, "email_bounced": c.has_bounced or None,
        "next_activity": {"when": _d(nxt.start_at), "what": nxt.activity_type, "subject": nxt.subject} if nxt else None,
        "latest_notes": brain_search.search(db, env.identity, "", contact_id=c.id, limit=4),
    }


@brain_tool("Looking at the groups")
def crm_groups(env: ToolEnv, query: str = "") -> dict:
    """Contact groups (lists) this person can see, with how many people are in each.

    Args:
      query: optional part of a group name
    """
    need(env, "groups")
    from app.models import Group, GroupMembership
    stmt = select(Group, func.count(GroupMembership.id)).outerjoin(GroupMembership, GroupMembership.group_id == Group.id).group_by(Group.id)
    if query.strip():
        stmt = stmt.where(Group.name.ilike(f"%{query.strip()}%"))
    if (cl := vis.group_clause(env.db, env.identity)) is not None:
        stmt = stmt.where(cl)
    rows = env.db.execute(stmt.order_by(func.count(GroupMembership.id).desc()).limit(25)).all()
    return {"groups": [{"name": g.name, "people": n, "about": g.description, "link": f"/groups/{g.id}"} for g, n in rows], "see_all": "/groups"}


@brain_tool("Checking the calls")
def calls_recent(env: ToolEnv, limit: int = 10) -> dict:
    """Recent calls the notetaker joined (or was booked for) that this person can see: when, with whom, and
    whether the notes are ready, saved to history or the call wasn't recorded.

    Args:
      limit: how many (up to 25)
    """
    need(env, "calls")
    from app.models.calendar import CalendarAttendance
    from app.roles import CAN_USE_AUTOMATIONS
    q = select(CallRecording).order_by(CallRecording.created_at.desc()).limit(max(1, min(limit, 25)))
    if env.identity.role not in CAN_USE_AUTOMATIONS:
        me = env.identity.user_uuid
        q = q.where(or_(CallRecording.user_id == me, CallRecording.calendar_meeting_id.in_(
            select(CalendarAttendance.meeting_id).where(CalendarAttendance.user_id == me))))
    rows = env.db.scalars(q).all()
    return {"calls": [{"title": c.title, "when": _d(c.started_at or c.created_at), "status": c.status_label or c.status,
                       "saved_to_history": bool(c.saved_to_history_at), "link": f"/calls/{c.id}"} for c in rows], "see_all": "/calls"}


@brain_tool("Checking team activity")
def team_activity(env: ToolEnv, days: int = 7) -> dict:
    """How much each person has logged recently: history entries (calls, meetings, emails logged) and activities
    scheduled, over the last few days.

    Args:
      days: how many days back (1-60)
    """
    need(env, "sales_dashboard")
    from app.models import HistoryEntry, User
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(days or 7), 60)))
    names = {u.id: u.name for u in env.db.scalars(select(User))}
    hist = dict(env.db.execute(select(HistoryEntry.created_by_user_id, func.count()).where(
        HistoryEntry.created_by_user_id.isnot(None), HistoryEntry.occurred_at >= since).group_by(HistoryEntry.created_by_user_id)).all())
    acts = dict(env.db.execute(select(Activity.created_by_user_id, func.count()).where(
        Activity.created_by_user_id.isnot(None), Activity.start_at >= since).group_by(Activity.created_by_user_id)).all())
    people = sorted(set(hist) | set(acts), key=lambda u: -(hist.get(u, 0) + acts.get(u, 0)))
    return {"since": _d(since), "people": [{"name": names.get(u, "Someone"), "history_logged": hist.get(u, 0), "activities": acts.get(u, 0)}
                                           for u in people], "see_all": "/sales/dashboard"}


@brain_tool("Checking the feedback board")
def feedback_open(env: ToolEnv, page: str = "") -> dict:
    """Open feedback on the feedback board (what people reported as broken, confusing or an idea), newest first.

    Args:
      page: optional page address to see only feedback about that page, e.g. "/sales/deals"
    """
    from app.models import Feedback
    stmt = select(Feedback).where(Feedback.status.in_(("new", "looking"))).order_by(Feedback.created_at.desc()).limit(15)
    if page.strip():
        stmt = stmt.where(Feedback.page_path == page.strip())
    rows = env.db.scalars(stmt).all()
    return {"open": [{"number": f.number, "kind": f.kind, "said": (f.message or "")[:200], "page": f.page_path,
                      "status": "being looked at" if f.status == "looking" else "new", "votes": len(f.me_too or []),
                      "link": f"/feedback?open={f.id}"} for f in rows], "see_all": "/feedback"}


@brain_tool("Checking data health")
def data_health(env: ToolEnv) -> dict:
    """How tidy the CRM is: people with no email or phone, companies with no industry, and the clean-up cards
    waiting (duplicates, bounces, out-of-office replies, people who've left)."""
    need(env, "data_health")
    from app.api.routes.dashboard import get_data_health
    return get_data_health(source_db=None, db=env.db).model_dump() | {"see_all": "/data-health"}
