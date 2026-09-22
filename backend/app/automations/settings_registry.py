"""Every automation tunable the UI can edit at runtime - same plug-in shape
as app/preferences.py, deliberately: adding a new editable setting later
means adding one AutomationSettingDef below, nothing in the frontend (it
renders entirely from GET /api/automations/settings).

A setting's *code* default always comes from app/core/config.py's Settings
class (the env var) - this registry only adds the metadata needed to show
and edit it (label, description, type, valid range), and
runtime_settings.py layers a DB override on top of that default. Removing
an override (not covered here - see the DELETE route) just falls back to
the env var again, never leaves the setting in an undefined state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SettingType = Literal["bool", "int", "float", "csv", "text"]


@dataclass(frozen=True)
class AutomationSettingDef:
    key: str  # matches a field name on app.core.config.Settings
    label: str
    description: str
    group: str  # which automation this belongs to, for the UI to section by
    type: SettingType
    min: float | None = None
    max: float | None = None


AUTOMATION_SETTING_DEFS: list[AutomationSettingDef] = [
    # ---- CS-001 / CS-002 - bounce & OOO mailbox scan ----
    AutomationSettingDef(
        key="automations_bounce_scan_enabled", label="Scan enabled",
        description="Whether the bounce/OOO mailbox scan runs on its schedule.",
        group="Bounce & OOO scan", type="bool",
    ),
    AutomationSettingDef(
        key="graph_scan_mailboxes", label="Mailboxes to scan",
        description="Comma-separated mailbox addresses this scan reads for bounces and out-of-office replies.",
        group="Bounce & OOO scan", type="csv",
    ),
    AutomationSettingDef(
        key="bounce_scan_initial_lookback_minutes", label="Initial lookback (minutes)",
        description="How far back the very first scan of a mailbox looks, before it has its own cursor.",
        group="Bounce & OOO scan", type="int", min=1,
    ),
    AutomationSettingDef(
        key="ooo_llm_max_per_run", label="Max OOO LLM classifications per run",
        description="Caps how many candidate out-of-office messages get the LLM genuine-absence/replacement-extraction call in one run. Anything past the cap is retried on the next scheduled tick, not lost.",
        group="Bounce & OOO scan", type="int", min=1,
    ),

    # ---- CS-003 - departure scan ----
    AutomationSettingDef(
        key="automations_departure_scan_enabled", label="Scan enabled",
        description="Whether the departure/successor scan runs on its schedule.",
        group="Departure scan", type="bool",
    ),

    # ---- CS-004 - duplicate contact scan ----
    AutomationSettingDef(
        key="automations_dedupe_scan_enabled", label="Scan enabled",
        description="Whether the duplicate-contact scan runs on its schedule.",
        group="Duplicate contact scan", type="bool",
    ),
    AutomationSettingDef(
        key="dedupe_confidence_floor", label="Confidence floor",
        description="Minimum multi-field match confidence (0-1) before a pair is queued for review.",
        group="Duplicate contact scan", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="dedupe_max_per_run", label="Max queued per run",
        description="Caps how many candidate pairs get queued in one run.",
        group="Duplicate contact scan", type="int", min=1,
    ),
    AutomationSettingDef(
        key="dedupe_batch_size", label="Contacts examined per run",
        description="Bounds real query cost - how many contacts the scan drives through matching per run, independent of how many get queued.",
        group="Duplicate contact scan", type="int", min=1,
    ),

    # ---- Follow-up engine ----
    AutomationSettingDef(
        key="automations_followup_scan_enabled", label="Scan enabled",
        description="Whether the follow-up due scan runs on its schedule.",
        group="Follow-up engine", type="bool",
    ),
    AutomationSettingDef(
        key="followup_lookback_days", label="Lookback (days)",
        description="How many days in the past the scan looks for overdue follow-ups.",
        group="Follow-up engine", type="int", min=0,
    ),
    AutomationSettingDef(
        key="followup_lookahead_days", label="Lookahead (days)",
        description="How many days ahead the scan looks for upcoming follow-ups.",
        group="Follow-up engine", type="int", min=0,
    ),
    AutomationSettingDef(
        key="followup_max_per_run", label="Max queued per run",
        description="Caps how many follow-up drafts get queued in one run.",
        group="Follow-up engine", type="int", min=1,
    ),

    # ---- SALES-010-lite - email exchange summary ----
    AutomationSettingDef(
        key="automations_email_summary_scan_enabled", label="Scan enabled",
        description="Whether the email exchange summary scan runs on its schedule.",
        group="Email exchange summary", type="bool",
    ),
    AutomationSettingDef(
        key="graph_email_summary_mailboxes", label="Mailboxes to scan",
        description="Comma-separated salesperson mailboxes this scan reads for real client conversations.",
        group="Email exchange summary", type="csv",
    ),
    AutomationSettingDef(
        key="email_summary_max_recipients", label="Max recipients",
        description="Drop any thread with more people on it than this - a group thread, not a 1:1 sales conversation.",
        group="Email exchange summary", type="int", min=1,
    ),
    AutomationSettingDef(
        key="email_summary_min_body_chars", label="Min body length (characters)",
        description="Drop messages shorter than this - a bare \"Thanks!\" has nothing to extract.",
        group="Email exchange summary", type="int", min=0,
    ),
    AutomationSettingDef(
        key="email_summary_initial_lookback_minutes", label="Initial lookback (minutes)",
        description="How far back the very first scan of a mailbox looks, before it has its own cursor.",
        group="Email exchange summary", type="int", min=1,
    ),
    AutomationSettingDef(
        key="email_summary_internal_domains", label="Internal domains",
        description="Comma-separated BMI-owned email domains. A thread is dropped when both the sender and the matched contact are on one of these - staff-to-staff mail, not a client conversation.",
        group="Email exchange summary", type="csv",
    ),
    AutomationSettingDef(
        key="email_summary_confidence_threshold", label="Confidence threshold",
        description="A signal below this confidence (0-1, the model's own genuine score) is dropped entirely rather than stored - SALES-012 should never trigger off something the model itself wasn't sure about.",
        group="Email exchange summary", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="email_summary_idle_close_hours", label="Idle-close window (hours)",
        description="A thread with no new message for this long is considered closed - a single Note summarising the whole exchange (what was discussed/offered/agreed, package + rate) is written once, on close.",
        group="Email exchange summary", type="int", min=1,
    ),

    # ---- SALES-011 - inbound contact capture ----
    AutomationSettingDef(
        key="automations_inbound_capture_scan_enabled", label="Scan enabled",
        description="Whether the inbound contact capture scan runs on its schedule.",
        group="Inbound contact capture", type="bool",
    ),
    AutomationSettingDef(
        key="graph_inbound_capture_mailboxes", label="Mailboxes to scan (mailbox:source_db)",
        description="Comma-separated \"mailbox:source_db\" pairs, e.g. enquiries@bmipublishing.co.uk:prospects - which Act! database a lead from that mailbox should be matched/suggested against. Use \"mailbox:*\" for a genuinely shared/general inbox not tied to one brand - the reviewer picks the database when confirming instead of a company/group guess being computed.",
        group="Inbound contact capture", type="csv",
    ),
    AutomationSettingDef(
        key="inbound_capture_max_recipients", label="Max recipients",
        description="Drop any thread with more people on it than this - a group thread, not a genuine new enquiry.",
        group="Inbound contact capture", type="int", min=1,
    ),
    AutomationSettingDef(
        key="inbound_capture_min_body_chars", label="Min body length (characters)",
        description="Drop messages shorter than this - too little to be a real enquiry.",
        group="Inbound contact capture", type="int", min=0,
    ),
    AutomationSettingDef(
        key="inbound_capture_initial_lookback_minutes", label="Initial lookback (minutes)",
        description="How far back the very first scan of a mailbox looks, before it has its own cursor.",
        group="Inbound contact capture", type="int", min=1,
    ),
    AutomationSettingDef(
        key="inbound_capture_llm_max_per_run", label="Max LLM classifications per run",
        description="Caps how many candidate messages get the LLM intent-classification call (new inquiry / reply / spam / unsubscribe request) in one run, across all mailboxes combined. Anything past the cap is retried on the next scheduled tick, not lost.",
        group="Inbound contact capture", type="int", min=1,
    ),

    # ---- SALES-002 - business card dedupe & group assignment ----
    AutomationSettingDef(
        key="teams_webhook_url", label="Teams webhook URL",
        description="MS Teams \"Incoming Webhook\" connector URL for the batch-confirm summary (added/updated/skipped). Left blank, the summary is just logged.",
        group="Business card capture", type="text",
    ),

    # ---- SALES-012 - budget-window & renewal triggers ----
    AutomationSettingDef(
        key="automations_signal_triggers_scan_enabled", label="Scan enabled",
        description="Whether the budget-window/renewal trigger scan runs on its schedule.",
        group="Budget window & renewal triggers", type="bool",
    ),
    AutomationSettingDef(
        key="sales012_lead_days", label="Lead time (days)",
        description="A signal with a due_date triggers once that date is within this many days.",
        group="Budget window & renewal triggers", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales012_no_date_delay_days", label="Undated signal delay (days)",
        description="A signal with no due_date triggers this many days after it was first extracted.",
        group="Budget window & renewal triggers", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales012_max_per_run", label="Max queued per run",
        description="Caps how many review items get queued in one run.",
        group="Budget window & renewal triggers", type="int", min=1,
    ),

    # ---- SALES-005 - personal touchpoint reminders ----
    AutomationSettingDef(
        key="automations_personal_touchpoints_scan_enabled", label="Scan enabled",
        description="Whether the personal touchpoint reminder scan runs on its schedule.",
        group="Personal touchpoint reminders", type="bool",
    ),
    AutomationSettingDef(
        key="sales005_lead_days", label="Lead time (days)",
        description="A touchpoint with a stated date triggers once that date is this many days away (0 = on or after the date itself, never before).",
        group="Personal touchpoint reminders", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales005_no_date_delay_days", label="Undated touchpoint delay (days)",
        description="A touchpoint with no specific date triggers this many days after it was first mentioned.",
        group="Personal touchpoint reminders", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales005_max_per_run", label="Max queued per run",
        description="Caps how many review items get queued in one run.",
        group="Personal touchpoint reminders", type="int", min=1,
    ),

    # ---- SALES-013 - morning follow-up queue ranking ----
    AutomationSettingDef(
        key="sales013_weight_urgency", label="Urgency weight",
        description="How much a due-date's closeness (or overdue-ness) drives the morning queue's ranking. Always based on a real date.",
        group="Morning follow-up queue", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="sales013_weight_value", label="Deal value weight",
        description="How much a linked Opportunity's value drives ranking. Only ~7 Opportunity rows exist across all databases - set to 0 to ignore value entirely and rank on urgency alone.",
        group="Morning follow-up queue", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="sales013_value_cap", label="Value cap ($ / £ treated as \"maximum\")",
        description="An Opportunity total_amount at or above this scores as maximum value (1.0) for ranking purposes.",
        group="Morning follow-up queue", type="float", min=1.0,
    ),

    # ---- LLM reliability & cost - see app/automations/llm.py ----
    AutomationSettingDef(
        key="llm_max_retries", label="Max retries per call",
        description="How many times a Gemini/OpenAI call retries on a transient/rate-limit error before giving up. 0 disables retries.",
        group="LLM usage & cost", type="int", min=0, max=10,
    ),
    AutomationSettingDef(
        key="llm_retry_base_delay_seconds", label="Retry base delay (seconds)",
        description="Starting delay before the first retry - doubles each attempt (exponential backoff).",
        group="LLM usage & cost", type="float", min=0.1,
    ),
    AutomationSettingDef(
        key="llm_call_min_interval_seconds", label="Min delay between calls in one scan (seconds)",
        description="Spreads out a burst of LLM calls within a single scan run's loop, so it doesn't trip a provider's per-minute rate limit.",
        group="LLM usage & cost", type="float", min=0.0,
    ),
    AutomationSettingDef(
        key="llm_cost_gemini_input_per_1m", label="Gemini input cost ($ / 1M tokens)",
        description="List price for Gemini prompt tokens - update when the provider changes pricing. Only affects the cost dashboard, never automation behavior.",
        group="LLM usage & cost", type="float", min=0.0,
    ),
    AutomationSettingDef(
        key="llm_cost_gemini_output_per_1m", label="Gemini output cost ($ / 1M tokens)",
        description="List price for Gemini completion tokens.",
        group="LLM usage & cost", type="float", min=0.0,
    ),
    AutomationSettingDef(
        key="llm_cost_openai_input_per_1m", label="OpenAI input cost ($ / 1M tokens)",
        description="List price for OpenAI prompt tokens.",
        group="LLM usage & cost", type="float", min=0.0,
    ),
    AutomationSettingDef(
        key="llm_cost_openai_output_per_1m", label="OpenAI output cost ($ / 1M tokens)",
        description="List price for OpenAI completion tokens.",
        group="LLM usage & cost", type="float", min=0.0,
    ),
    AutomationSettingDef(
        key="llm_cost_overrides_json", label="Per-model cost overrides (JSON)",
        description=(
            "Exact rate for a specific model, checked before the provider-level defaults above. "
            'Shape: {"<exact model name, e.g. gemini-3.6-flash>": {"input": <$/1M tokens>, "output": <$/1M tokens>}}. '
            "Use this to give the model actually configured (see Provider settings) its real published rate "
            "without a code change - the provider-level fields above are only the fallback for a model with no "
            "entry here."
        ),
        group="LLM usage & cost", type="text",
    ),
]

_BY_KEY = {d.key: d for d in AUTOMATION_SETTING_DEFS}


def get_def(key: str) -> AutomationSettingDef | None:
    return _BY_KEY.get(key)
