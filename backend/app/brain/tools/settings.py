"""Settings, live: the asking person's own (role, permissions, database access, preferences, connections), the
company settings they're allowed to see (automation settings, booking confirmation details, editorial brand rules,
which sections are switched off, connections), and - for administrators - anyone's account settings.

Passwords, keys and tokens are never read here: those live only in the server's environment. Connections are
reported as working / not set up / has a problem, never with their technical error text.
"""
from __future__ import annotations

import re

from sqlalchemy import select

from app.brain import access
from app.brain.registry import ToolEnv, ToolError, brain_tool
from app.models import User

WORD = re.compile(r"[a-z0-9]+")
CONFIRMATION_LABELS = {
    "company_block": "Company details on confirmations", "footer": "Confirmation footer", "terms": "Terms and conditions",
    "artwork_specs": "Artwork specifications", "production_emails": "Production team email addresses",
    "accounts_emails": "Accounts email addresses (get a copy of new bookings)", "default_production_contact": "Default production contact",
    "default_copy_instructions": "Default copy instructions", "default_special_instructions": "Default special instructions",
    "next_number": "Next booking number",
}


def _person(db, user: User) -> dict:
    from app.automations.registry import all_kinds  # noqa: F401 (kinds registered for the accounts check)
    from app.core.identity import Identity
    from app.models import CalendarConnection, MailAccount, Publication, UserAccess, WritingProfile
    from app.preferences import PREFERENCE_DEFS
    from app.roles import ROLE_DEFS
    from app.sales import accounts
    ident = Identity(user_id=str(user.id), role=user.role)
    prefs = user.preferences or {}
    pubs = {p.slug: p.name for p in db.scalars(select(Publication))}
    grants = db.execute(select(UserAccess.source_db, UserAccess.group_id).where(UserAccess.user_id == user.id)).all()
    cal = db.scalars(select(CalendarConnection).where(CalendarConnection.user_id == user.id)).all()
    mail = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id).limit(1))
    return {
        "name": user.name, "email": user.email,
        "role": next((r.label for r in ROLE_DEFS if r.value == user.role), user.role),
        "does_the_accounts_work": bool(accounts.can_approve(db, user.id, user.role)),
        "database_access": "everything (administrator)" if user.role == "admin" else
                           [pubs.get(s, s) + (" (one group only)" if g else "") for s, g in grants] or "none yet",
        "cannot_open": access.blocked_labels(db, ident) or "nothing - every section is on",
        "preferences": [{"setting": d.label, "value": next((o.label for o in d.options if o.value == prefs.get(d.key, d.default)), prefs.get(d.key, d.default)),
                         "what_it_does": d.description} for d in PREFERENCE_DEFS],
        "outlook_connected": bool(mail) and not (mail and mail.last_error),
        "calendars": [{"calendar": "Outlook" if c.provider == "microsoft" else "Google", "working": c.status != "error" and not c.last_error} for c in cal] or "none connected",
        "writing_style_set_up": bool(db.scalar(select(WritingProfile.id).where(WritingProfile.user_id == user.id).limit(1))),
        "active": user.is_active, "where_to_change": "/settings",
    }


@brain_tool("Checking your settings")
def my_settings(env: ToolEnv) -> dict:
    """The asking person's own account: role, whether they do the Accounts work, which databases they can see,
    which sections are switched off for them, their preferences (email notifications, call recording...), and
    which connections they have (Outlook, calendars, writing style)."""
    if not env.user:
        raise ToolError("I don't know who's asking, so I can't look at settings.")
    return _person(env.db, env.user)


@brain_tool("Checking their settings")
def person_settings(env: ToolEnv, person: str) -> dict:
    """Administrators only: another person's account settings (the same as my_settings, for them).

    Args:
      person: their name or email
    """
    access.require(env, "users")
    p = (person or "").strip()
    rows = env.db.scalars(select(User).where((User.name.ilike(f"%{p}%")) | (User.email.ilike(f"%{p}%"))).limit(6)).all()
    if not rows:
        raise ToolError(f"Nobody called {person!r} has an account.")
    if len(rows) > 1 and not any(r.name.lower() == p.lower() for r in rows):
        return {"which_one": [{"name": r.name, "email": r.email} for r in rows]}
    u = next((r for r in rows if r.name.lower() == p.lower()), rows[0])
    return _person(env.db, u) | {"where_to_change": "/settings/users"}


def _score(query: str, *texts: str) -> int:
    want = {w for w in WORD.findall(query.lower()) if len(w) > 2}
    have = set(WORD.findall(" ".join(t or "" for t in texts).lower()))
    return len(want & have)


def _connections(env: ToolEnv) -> list[dict]:
    from app.automations import runtime_settings
    from app.core.config import settings
    from app.services import calendar_providers as cp
    from app.services import notetaker, outlook, xero
    out = []
    conn = xero.connection(env.db)
    out.append({"setting": "Xero", "value": "connected" + (", but its last sync had a problem" if conn and conn.last_error else "")
                if (conn or xero.webhook_mode()) else ("not connected" if xero.is_configured() else "not set up"), "where": "/settings"})
    out.append({"setting": "BMI Notetaker", "value": "connected" if notetaker.configured() else "not set up", "where": "/calls/meetings"})
    out.append({"setting": "Automation mailbox (sends notifications and hand-offs)",
                "value": runtime_settings.get_str(env.db, "automation_mailbox") or "not set", "where": "/automations/settings"})
    out.append({"setting": "Outlook sign-in for everyone", "value": "set up" if outlook.is_configured() else "not set up", "where": "/settings"})
    out.append({"setting": "Google Calendar sign-in", "value": "set up" if cp.google_configured() else "not set up", "where": "/calls/meetings"})
    out.append({"setting": "AI (Gemini)", "value": "set up" if settings.gemini_api_key else "not set up", "where": "(server settings)"})
    return out


@brain_tool("Looking up the settings")
def settings_lookup(env: ToolEnv, query: str = "") -> dict:
    """Finds company settings that match some words, with their current value, what they do and where to change
    them: automation settings, booking confirmation details, editorial brand rules, switched-off sections and
    connections (Xero, notetaker, mailbox) - only the ones this person may see.

    Args:
      query: a few words, e.g. "renewal", "invoice reminder", "production email", "Xero". Empty = a short summary.
    """
    from app.automations.settings_registry import AUTOMATION_SETTING_DEFS
    from app.automations.status import setting_view
    found: list[tuple[int, dict]] = []
    seen_areas = []
    if access.can(env, "automations_hub"):
        seen_areas.append("automation settings")
        for d in AUTOMATION_SETTING_DEFS:
            v = setting_view(env.db, d)
            found.append((_score(query, d.label, d.description, d.group, d.key),
                          {"area": f"Automations - {d.group}", "setting": d.label, "value": v["value"], "default": v["default"],
                           "what_it_does": d.description, "where": "/automations/settings"}))
    if access.can(env, "orders"):
        seen_areas.append("booking confirmation details")
        from app.sales import deals as dl
        st = dl.settings(env.db)
        for key, label in CONFIRMATION_LABELS.items():
            val = getattr(st, key, None)
            found.append((_score(query, label, "booking confirmation order"),
                          {"area": "Booking confirmations", "setting": label, "value": (str(val)[:300] if val else "not set"),
                           "where": "/sales/deals (Confirmation details)"}))
        routes = st.handoff_routes or {}
        found.append((_score(query, "hand off handoff editorial production routes emails"),
                      {"area": "Booking confirmations", "setting": "Hand-off routes (who editorial and production emails go to)",
                       "value": f"{len(routes.get('titles') or {})} titles set up" if routes else "not set up", "where": "/sales/deals (Hand-offs)"}))
    if access.can(env, "editorial"):
        seen_areas.append("editorial brand rules")
        from app.api.routes import editorial as ed
        from app.sales.brands import BRANDS
        for b in BRANDS:
            try:
                s = ed._settings(env.db, b.key)
            except Exception:
                continue
            found.append((_score(query, b.name, "brand editorial deadline rules audience facts", " ".join(s.rules_described)),
                          {"area": "Editorial plan", "setting": f"{b.name} - deadline rules and brand facts",
                           "value": "; ".join(s.rules_described)[:400] or "no rules set", "where": f"/editorial/settings/{b.key}"}))
    if access.can(env, "sections_settings"):
        seen_areas.append("switched-off sections")
        from app.ui_sections import SECTIONS, hidden_by_role
        names = {s.key: s.label for s in SECTIONS}
        for role, keys in hidden_by_role(env.db).items():
            found.append((_score(query, "sections hidden switched off visible menu", role, "sales data manager"),
                          {"area": "Sections", "setting": f"Switched off for the {role.replace('_', ' ')} role",
                           "value": ", ".join(names.get(k, k) for k in keys) or "nothing", "where": "/settings/sections"}))
    if access.can(env, "integrations"):
        seen_areas.append("connections")
        for c in _connections(env):
            found.append((_score(query, c["setting"], "connection integration connected"), {"area": "Connections", **c}))
    if not seen_areas:
        raise ToolError(f"{access.NO_PERMISSION} (Say exactly that, kindly; they can still ask about their own settings.)")
    if query.strip():
        hits = [r for s, r in sorted(found, key=lambda x: -x[0]) if s > 0][:12]
        return {"results": hits, "searched": seen_areas,
                "note": None if hits else "No setting matches those words. Try another word, or ask for a summary."}
    by_area: dict[str, int] = {}
    for _, r in found:
        by_area[r["area"]] = by_area.get(r["area"], 0) + 1
    changed = [r for _, r in found if "default" in r and r["value"] != r["default"]][:15]
    return {"areas": by_area, "changed_from_default": changed, "searched": seen_areas}
