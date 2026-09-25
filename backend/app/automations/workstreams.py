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
        kinds=("followup_due", "signal_trigger", "personal_touchpoint_due"),
    ),
    Workstream(
        id="capture",
        label="Lead & Contact Capture",
        tagline="New prospects spotted in inbound mail, ready to become CRM contacts.",
        kinds=("inbound_contact_unmatched",),
    ),
    Workstream(
        id="business-cards",
        label="Business Cards & Photos",
        tagline="Trade-show cards and returned-copy labels, read by AI and matched against the CRM.",
        kinds=("business_card_new", "business_card_existing", "returned_copy"),
    ),
    Workstream(
        id="hygiene",
        label="CRM Data Hygiene",
        tagline="Duplicates, bounces, out-of-office replies and departures that keep the CRM accurate.",
        kinds=("ooo_ambiguous", "departure_unconfirmed", "duplicate_contact", "bounce_uncertain", "bounce_unmatched"),
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
    "departure_unconfirmed": "cs003_departure_scan",
    "duplicate_contact": "cs004_dedupe_scan",
}


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
}


def get_workstream(workstream_id: str) -> Workstream | None:
    return next((w for w in WORKSTREAMS if w.id == workstream_id), None)


def kinds_for_job(job_id: str) -> list[str]:
    return [k for k, j in KIND_JOB.items() if j == job_id]
