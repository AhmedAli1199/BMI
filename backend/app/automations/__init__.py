"""Importing this package registers every automation's review kinds (see
registry.py) as a side effect - main.py imports it once at startup. Add a
new automation module here so it actually gets registered.
"""
from app.automations import allocations, booking_changes, booking_forms, brain_jobs, bounce_handling, brevo_sync, business_card, calendar_jobs, campaign_replies, call_notes, client_owners, competitor_issues, dedupe, departure, editorial_deadlines, email_summary, followup_queue, inbound_capture, invoice_due, issue_campaigns, issue_online, management_reports, merge_followups, messaging_jobs, news_campaigns, order_checks, personal_touchpoints, press_releases, proposal_requests, returned_copy, sales_orders, sor_checks, save_the_sale, signal_triggers, subscription_changes, subscription_forms, website_coverage, xero_matching  # noqa: F401
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, all_kinds, get_action, get_kind, register

__all__ = [
    "ExtraField",
    "ReviewAction",
    "ReviewKind",
    "all_kinds",
    "get_action",
    "get_kind",
    "register",
]
