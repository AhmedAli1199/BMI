"""What the assistant may tell each person: exactly what they can open in the app themselves.

Two layers, both the app's own:
1. The role (app/roles.py): e.g. the Automations Hub and Data Health are for administrators and data managers.
2. The section switches in Settings > Sections (app/ui_sections.py): an administrator can switch any section off
   for a role or one person. Switched off = the assistant won't look it up, explain it or answer about it.

Every tool calls `require(env, <section>)` (or `require_any` when the same facts appear on several screens) and
the turn's <context> lists what this person can't open, so the model declines those questions up front too.
"""
from __future__ import annotations

from app.roles import CAN_MANAGE_USERS, CAN_USE_AUTOMATIONS, CAN_VIEW_OWN_QUEUE

NO_PERMISSION = "You don't have permission to view that."

# Sections that also need a particular role (on top of not being switched off).
ROLE_GATED = {
    "automations_hub": CAN_USE_AUTOMATIONS,
    "data_health": CAN_USE_AUTOMATIONS,
    "today": CAN_VIEW_OWN_QUEUE,
    "review_queue": CAN_VIEW_OWN_QUEUE,
}
# Things that aren't sections but are role-limited.
ADMIN_ONLY = {"users", "sections_settings"}
STAFF_ONLY = {"integrations"}       # Xero, notetaker, the automation mailbox

# Which section a page belongs to (longest prefix wins) - for help guides and the page someone is on.
ROUTE_SECTION = [
    ("/sales/dashboard", "sales_dashboard"), ("/sales/editions", "editions"), ("/sales/compare", "editions"),
    ("/sales/bookings", "bookings"), ("/sales/renewals", "renewals"), ("/sales/proposals", "proposals"),
    ("/sales/deals", "orders"), ("/sales/orders", "orders"), ("/sales/rate-card", "rate_card"),
    ("/sales/invoicing", "invoicing"), ("/sales/commissions", "commissions"), ("/sales/costs", "editions"),
    ("/sales/summaries", "sales_overview"), ("/sales", "sales_overview"),
    ("/contacts", "contacts"), ("/companies", "companies"), ("/groups", "groups"), ("/activities", "calendar"),
    ("/reminders", "reminders"), ("/calls", "calls"), ("/mail-merge/templates", "email_templates"), ("/mail-merge", "mail_merge"),
    ("/editorial", "editorial"), ("/automations/today", "today"), ("/automations/review", "review_queue"),
    ("/automations", "automations_hub"), ("/data-health", "data_health"),
    ("/settings/users", "users"), ("/settings/sections", "sections_settings"),
]


def section_for(path: str | None) -> str | None:
    if not path:
        return None
    path = path.split("?")[0].rstrip("/") or "/"
    best = None
    for prefix, key in ROUTE_SECTION:
        if (path == prefix or path.startswith(prefix + "/")) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, key)
    return best[1] if best else None


def blocked(db, identity) -> set[str]:
    """Every section (and role-limited area) this person can't open."""
    from app.ui_sections import KEYS, hidden_for
    role = identity.role if identity.is_known else "admin"
    out = set(hidden_for(db, role, identity.user_id))
    for key, roles in ROLE_GATED.items():
        if role not in roles:
            out.add(key)
    if role not in CAN_MANAGE_USERS:
        out |= ADMIN_ONLY
    if role not in CAN_USE_AUTOMATIONS:
        out |= STAFF_ONLY
    return out & (KEYS | ADMIN_ONLY | STAFF_ONLY)


def can(env, section: str) -> bool:
    return section not in blocked(env.db, env.identity)


def require(env, section: str) -> None:
    from app.brain.registry import ToolError
    if not can(env, section):
        raise ToolError(f"{NO_PERMISSION} (Say exactly that, kindly, and don't describe what's there.)")


def require_any(env, *sections: str) -> None:
    """For facts shown on several screens (e.g. sales figures): fine if any of them can be opened."""
    from app.brain.registry import ToolError
    b = blocked(env.db, env.identity)
    if sections and all(s in b for s in sections):
        raise ToolError(f"{NO_PERMISSION} (Say exactly that, kindly, and don't describe what's there.)")


def blocked_labels(db, identity) -> list[str]:
    from app.ui_sections import SECTIONS
    names = {s.key: s.label for s in SECTIONS} | {"users": "Users and roles", "sections_settings": "Section settings",
                                                  "integrations": "Integrations (Xero, notetaker, mailbox)"}
    return sorted(names.get(k, k) for k in blocked(db, identity))
