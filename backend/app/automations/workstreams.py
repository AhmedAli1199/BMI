"""Which automation (review kind) belongs to which workstream, and which
scheduled job produces it - the one place this is defined. The frontend
reads it from GET /api/automations/workstreams instead of keeping its own
copy, and dashboard.py's Data Health page reads the hygiene list from here
too.

A kind with job_id=None is produced by a person, not a scanner (a photo
upload), so it has no "last run" to show.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workstream:
    id: str
    label: str
    tagline: str
    kinds: tuple[str, ...]


WORKSTREAMS: tuple[Workstream, ...] = (
    Workstream(
        id="sales",
        label="Sales & Follow-ups",
        tagline="Timely follow-ups, commercial signals, and personal touchpoints drafted for your reps.",
        kinds=("proposal_request", "followup_due", "signal_trigger", "personal_touchpoint_due", "call_notes"),
    ),
    Workstream(
        id="capture",
        label="Lead & Contact Capture",
        tagline="New prospects spotted in inbound mail, ready to become CRM contacts.",
        kinds=("inbound_contact_unmatched", "subscription_signup"),
    ),
    Workstream(
        id="business-cards",
        label="Business Cards & Photos",
        tagline="Trade-show cards and returned-copy labels, read by the Brain and matched against the CRM.",
        kinds=("business_card_new", "business_card_existing", "returned_copy"),
    ),
    Workstream(
        id="hygiene",
        label="CRM Data Hygiene",
        tagline="Duplicates, bounces, out-of-office replies and departures that keep the CRM accurate.",
        kinds=("ooo_ambiguous", "departure_unconfirmed", "duplicate_contact", "bounce_uncertain", "bounce_unmatched"),
    ),
    Workstream(
        id="revenue",
        label="Revenue & Orders",
        tagline="Renewals, uninvoiced bookings and client matching, all run on the Sales Order Register.",
        kinds=("renewal_due", "sor_invoice_missing", "sor_client_match", "sor_invoice_match", "order_check", "booking_change", "allocation_due", "invoice_due",
               "sor_issue_check", "online_booking", "save_the_sale", "client_owner"),
    ),
)

KIND_JOB: dict[str, str | None] = {
    "followup_due": "followup_engine_scan",
    "signal_trigger": "sales012_signal_triggers_scan",
    "personal_touchpoint_due": "personal_touchpoints_scan",
    "inbound_contact_unmatched": "sales011_inbound_capture_scan",
    "business_card_new": None,
    "business_card_existing": None,
    "returned_copy": None,
    "ooo_ambiguous": "cs001_cs002_bounce_ooo_scan",
    "bounce_uncertain": "cs001_cs002_bounce_ooo_scan",
    "bounce_unmatched": "cs001_cs002_bounce_ooo_scan",
    "departure_unconfirmed": "cs001_cs002_bounce_ooo_scan",
    "duplicate_contact": "cs004_dedupe_scan",
    "renewal_due": "sor_renewal_scan",
    "sor_invoice_missing": "sor_invoice_chase_scan",
    "sor_invoice_match": "xero_invoice_match_scan",
    "sor_client_match": "sor_client_match_scan",
    "order_check": None,
    "booking_change": None,
    "allocation_due": "allocation_reminder_scan",
    "invoice_due": "invoice_due_scan",
    "sor_issue_check": "sor_issue_check_scan",
    "online_booking": None,
    "subscription_signup": None,
    "save_the_sale": "save_the_sale_scan",
    "call_notes": None,
    "proposal_request": "proposal_request_scan",
    "client_owner": "client_owner_refresh",
}

# Where the cards come from for a kind no scheduled job makes (KIND_JOB None): a short label for the table's
# Scanner column and a sentence for its detail panel.
KIND_SOURCE: dict[str, tuple[str, str]] = {
    "business_card_new": ("Photo upload", "Made when someone uploads a photo of a business card, not by a scheduled scanner."),
    "business_card_existing": ("Photo upload", "Made when someone uploads a photo of a business card, not by a scheduled scanner."),
    "returned_copy": ("Photo upload", "Made when someone uploads photos of returned post, not by a scheduled scanner."),
    "order_check": ("When a booking is confirmed", "Made when a salesperson confirms a booking, so accounts can check it before invoicing."),
    "booking_change": ("When a change is asked for", "Made when someone asks to change a booking accounts have already checked."),
    "online_booking": ("Online booking forms", "Made when a client fills in one of BMI's online booking forms."),
    "subscription_signup": ("Subscribe forms", "Made when someone signs up on one of the titles' subscribe forms."),
    "call_notes": ("After a call", "Made when the notetaker finishes a call and its notes are ready."),
}


def source_for(kind: str) -> tuple[str, str]:
    return KIND_SOURCE.get(kind, ("Made in the app", "Made by something people do in the app, not by a scheduled scanner."))


# Which llm_usage_events.purpose prefix belongs to which kind, for the
# per-automation AI cost figure. A prefix shared by several kinds (the
# bounce/OOO scanner makes one set of calls for all of its kinds) can't be
# split honestly, so the UI labels that figure as shared rather than
# guessing a per-kind share.
KIND_COST_PREFIX: dict[str, str | None] = {
    "followup_due": "followup_queue.",
    "signal_trigger": "signal_triggers.",
    "personal_touchpoint_due": "personal_touchpoints.",
    "inbound_contact_unmatched": "inbound_capture.",
    "business_card_new": "business_card.",
    "business_card_existing": "business_card.",
    "returned_copy": "returned_copy.",
    "ooo_ambiguous": "bounce_handling.",
    "bounce_uncertain": "bounce_handling.",
    "bounce_unmatched": "bounce_handling.",
    "departure_unconfirmed": "bounce_handling.",
    "duplicate_contact": None,
    "renewal_due": "sor_renewal.",
    "sor_invoice_missing": None,
    "sor_invoice_match": None,
    "sor_client_match": None,
    "order_check": None,
    "booking_change": None,
    "allocation_due": None,
    "invoice_due": None,
    "sor_issue_check": None,
    "online_booking": None,
    "subscription_signup": None,
    "save_the_sale": "save_the_sale.",
    "call_notes": None,
    "proposal_request": "proposal_requests.",
}


def get_workstream(workstream_id: str) -> Workstream | None:
    return next((w for w in WORKSTREAMS if w.id == workstream_id), None)


def kinds_for_job(job_id: str) -> list[str]:
    return [k for k, j in KIND_JOB.items() if j == job_id]
