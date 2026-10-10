"""Sections of the app an administrator can hide from other roles, so the
screens stay uncluttered for people who don't need everything.

This is about tidiness, not security: hiding a section takes it out of the
navigation for that role. What a person may actually read or change is still
decided by their role and database access (app/roles.py, UserAccess).
Administrators always see every section.

The frontend sidebar uses these same keys (frontend/src/lib/sections.ts).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import AutomationSetting

STORE_KEY = "ui_hidden_sections"
HIDEABLE_ROLES = ("data_manager", "sales")


@dataclass(frozen=True)
class SectionDef:
    key: str
    label: str
    group: str
    description: str


SECTIONS: list[SectionDef] = [
    SectionDef("contacts", "Contacts", "Platform", "The contact list and contact pages."),
    SectionDef("companies", "Companies", "Platform", "The company list and company pages."),
    SectionDef("groups", "Groups", "Platform", "Contact groups and lists."),
    SectionDef("calendar", "Calendar & Tasks", "Platform", "Meetings, calls and tasks."),
    SectionDef("reminders", "Reminders", "Platform", "Personal reminders."),
    SectionDef("mail_merge", "Mail merge", "Platform", "Sending one email to many contacts."),
    SectionDef("email_templates", "Email templates", "Platform", "The shared library of email templates."),
    SectionDef("sales_overview", "Sales overview", "Sales", "The sales headline figures and booking pace."),
    SectionDef("sales_dashboard", "Sales dashboard", "Sales", "How each issue is selling against last cycle."),
    SectionDef("editions", "Editions", "Sales", "Every issue, month and event with its bookings."),
    SectionDef("bookings", "All bookings", "Sales", "The full list of bookings."),
    SectionDef("renewals", "Renewals", "Sales", "Last year's advertisers who haven't rebooked."),
    SectionDef("proposals", "Proposals", "Sales", "Writing and sending proposals."),
    SectionDef("orders", "Orders", "Sales", "Order confirmations and multi-item bookings."),
    SectionDef("rate_card", "Rate card", "Sales", "Prices for every brand."),
    SectionDef("invoicing", "Invoicing", "Sales", "Bookings waiting for an invoice."),
    SectionDef("commissions", "Commission", "Sales", "Commission statements (people only ever see their own)."),
    SectionDef("editorial", "Editorial plan", "Sales", "Issue dates, deadlines and features."),
    SectionDef("today", "Today", "BMI Brain", "Each person's list of things to do today."),
    SectionDef("review_queue", "Review Queue", "BMI Brain", "Suggestions waiting for someone to check."),
    SectionDef("automations_hub", "Automations Hub", "BMI Brain", "Automation status and results (data managers only)."),
    SectionDef("data_health", "Data Health", "BMI Brain", "Duplicate and incomplete records (data managers only)."),
]
KEYS = {s.key for s in SECTIONS}


def hidden_by_role(db: Session) -> dict[str, list[str]]:
    row = db.get(AutomationSetting, STORE_KEY)
    raw = (row.value or {}).get("v") if row else None
    raw = raw if isinstance(raw, dict) else {}
    return {role: sorted(k for k in raw.get(role, []) if k in KEYS) for role in HIDEABLE_ROLES}


def hidden_for(db: Session, role: str | None) -> list[str]:
    if role not in HIDEABLE_ROLES:
        return []
    return hidden_by_role(db)[role]


def save(db: Session, hidden: dict[str, list[str]]) -> dict[str, list[str]]:
    clean = {role: sorted({k for k in hidden.get(role, []) if k in KEYS}) for role in HIDEABLE_ROLES}
    row = db.get(AutomationSetting, STORE_KEY)
    if row:
        row.value = {"v": clean}
    else:
        db.add(AutomationSetting(key=STORE_KEY, value={"v": clean}))
    db.flush()
    return clean
