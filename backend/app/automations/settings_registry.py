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
    # ---- Reminders, notifications & mail merge ----
    AutomationSettingDef(
        key="automations_reminders_scan_enabled", label="Reminders fire",
        description="Turns due reminders into notifications every 5 minutes.",
        group="Reminders & Notifications", type="bool",
    ),
    AutomationSettingDef(
        key="automations_notification_email_enabled", label="Email notifications",
        description="Emails notifications from the automation mailbox (needs the mailbox below and Mail.Send on the app registration).",
        group="Reminders & Notifications", type="bool",
    ),
    AutomationSettingDef(
        key="automation_mailbox", label="Automation mailbox",
        description="The shared mailbox notification emails are sent from, e.g. automation@bmipublishing.co.uk. Empty = in-app only.",
        group="Reminders & Notifications", type="text",
    ),
    AutomationSettingDef(
        key="automations_mail_merge_sender_enabled", label="Mail merge sending",
        description="Sends queued mail-merge emails from each user's connected Outlook.",
        group="Reminders & Notifications", type="bool",
    ),
    AutomationSettingDef(
        key="mail_merge_per_minute", label="Mail merge emails per minute",
        description="Per sender. Exchange Online allows 30 a minute per mailbox; keep this below that.",
        group="Reminders & Notifications", type="int", min=1, max=30,
    ),
    # ---- CS-001 / CS-002 - bounce & OOO mailbox scan ----
    AutomationSettingDef(
        key="automations_bounce_scan_enabled", label="Mailbox monitoring active",
        description="Enables automated background scanning for email bounces and out-of-office replies.",
        group="Deliverability & Out-of-Office", type="bool",
    ),
    AutomationSettingDef(
        key="graph_scan_mailboxes", label="Monitored inboxes",
        description="Comma-separated inbox addresses monitored for bounces and out-of-office responses.",
        group="Deliverability & Out-of-Office", type="csv",
    ),
    AutomationSettingDef(
        key="bounce_scan_initial_lookback_minutes", label="Initial scan lookback (minutes)",
        description="How far back the first scan checks when establishing a new mailbox connection.",
        group="Deliverability & Out-of-Office", type="int", min=1,
    ),
    AutomationSettingDef(
        key="ooo_llm_max_per_run", label="Max out-of-office analyses per cycle",
        description="Maximum auto-replies analyzed for leave dates and colleague handovers per scan cycle.",
        group="Deliverability & Out-of-Office", type="int", min=1,
    ),

    # ---- CS-004 - duplicate contact scan ----
    AutomationSettingDef(
        key="automations_dedupe_scan_enabled", label="Duplicate detection active",
        description="Enables scheduled scans across publication lists to identify matching contact records.",
        group="Duplicate Resolution", type="bool",
    ),
    AutomationSettingDef(
        key="dedupe_confidence_floor", label="Match sensitivity threshold (0.0–1.0)",
        description="Minimum similarity score required before surfacing a potential duplicate pair for review.",
        group="Duplicate Resolution", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="dedupe_max_per_run", label="Max duplicate pairs queued per run",
        description="Maximum duplicate pairs surfaced for human review in a single scan cycle.",
        group="Duplicate Resolution", type="int", min=1,
    ),
    AutomationSettingDef(
        key="dedupe_batch_size", label="Contacts evaluated per run",
        description="Number of contact records compared during each scheduled deduplication cycle.",
        group="Duplicate Resolution", type="int", min=1,
    ),

    # ---- Follow-up engine ----
    AutomationSettingDef(
        key="automations_followup_scan_enabled", label="Follow-up queue active",
        description="Enables automatic drafting of follow-up emails for due and overdue CRM activities.",
        group="Follow-up Engine", type="bool",
    ),
    AutomationSettingDef(
        key="followup_lookback_days", label="Overdue lookback window (days)",
        description="How many days in the past to search for uncompleted activities needing follow-up.",
        group="Follow-up Engine", type="int", min=0,
    ),
    AutomationSettingDef(
        key="followup_lookahead_days", label="Upcoming lead window (days)",
        description="How many days in advance to pre-draft follow-up emails ahead of scheduled tasks.",
        group="Follow-up Engine", type="int", min=0,
    ),
    AutomationSettingDef(
        key="followup_max_per_run", label="Max follow-up drafts per run",
        description="Maximum follow-up drafts generated in a single processing run.",
        group="Follow-up Engine", type="int", min=1,
    ),

    # ---- SALES-010-lite - email exchange summary ----
    AutomationSettingDef(
        key="automations_email_summary_scan_enabled", label="Email exchange logging active",
        description="Enables automatic thread summarization and commercial signal extraction for closed conversations.",
        group="Email Summaries & Commercial Signals", type="bool",
    ),
    AutomationSettingDef(
        key="graph_email_summary_mailboxes", label="Monitored rep inboxes",
        description="Comma-separated sales representative mailboxes monitored for client exchanges.",
        group="Email Summaries & Commercial Signals", type="csv",
    ),
    AutomationSettingDef(
        key="email_summary_max_recipients", label="Max thread participants",
        description="Excludes large distribution or group threads beyond this recipient count to focus on direct 1:1 client sales conversations.",
        group="Email Summaries & Commercial Signals", type="int", min=1,
    ),
    AutomationSettingDef(
        key="email_summary_min_body_chars", label="Minimum message length",
        description="Excludes brief pleasantries shorter than this character count to focus on substantive exchanges.",
        group="Email Summaries & Commercial Signals", type="int", min=0,
    ),
    AutomationSettingDef(
        key="email_summary_initial_lookback_minutes", label="Initial lookback window (minutes)",
        description="How far back the initial scan reads when connecting to a mailbox for the first time.",
        group="Email Summaries & Commercial Signals", type="int", min=1,
    ),
    AutomationSettingDef(
        key="email_summary_internal_domains", label="Internal BMI email domains",
        description="Comma-separated internal domains used to filter out internal colleague conversations.",
        group="Email Summaries & Commercial Signals", type="csv",
    ),
    AutomationSettingDef(
        key="email_summary_confidence_threshold", label="Signal confidence threshold (0.0–1.0)",
        description="Minimum AI confidence required to capture commercial signals (budget dates, rates, and callbacks).",
        group="Email Summaries & Commercial Signals", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="email_summary_idle_close_hours", label="Thread quiescence window (hours)",
        description="Hours of inactivity before an email thread is considered completed and summarized into a CRM note.",
        group="Email Summaries & Commercial Signals", type="int", min=1,
    ),

    # ---- SALES-011 - inbound contact capture ----
    AutomationSettingDef(
        key="automations_inbound_capture_scan_enabled", label="Inbound lead capture active",
        description="Enables automatic detection and contact card creation for new prospective clients.",
        group="Inbound Lead Capture", type="bool",
    ),
    AutomationSettingDef(
        key="graph_inbound_capture_mailboxes", label="Enquiry mailboxes (mailbox:database)",
        description="Comma-separated inbox mappings (e.g. enquiries@bmipublishing.co.uk:prospects) defining which publication database receives new leads.",
        group="Inbound Lead Capture", type="csv",
    ),
    AutomationSettingDef(
        key="inbound_capture_max_recipients", label="Max thread participants",
        description="Excludes multi-recipient group broadcasts to ensure only genuine direct inquiries are captured.",
        group="Inbound Lead Capture", type="int", min=1,
    ),
    AutomationSettingDef(
        key="inbound_capture_min_body_chars", label="Minimum email length",
        description="Ignores empty or ultra-short automated messages.",
        group="Inbound Lead Capture", type="int", min=0,
    ),
    AutomationSettingDef(
        key="inbound_capture_initial_lookback_minutes", label="Initial lookback (minutes)",
        description="Initial lookback window when first monitoring an inquiry inbox.",
        group="Inbound Lead Capture", type="int", min=1,
    ),
    AutomationSettingDef(
        key="inbound_capture_llm_max_per_run", label="Max inquiries analyzed per run",
        description="Maximum new email inquiries processed for commercial intent and signature details per cycle.",
        group="Inbound Lead Capture", type="int", min=1,
    ),

    # ---- SALES-002 - business card dedupe & group assignment ----
    AutomationSettingDef(
        key="teams_webhook_url", label="Microsoft Teams webhook URL",
        description="Optional incoming webhook URL to post automated notifications and daily review summaries to Teams.",
        group="Notifications & Alerts", type="text",
    ),

    # ---- SALES-012 - budget-window & renewal triggers ----
    AutomationSettingDef(
        key="automations_signal_triggers_scan_enabled", label="Commercial trigger scan active",
        description="Enables scheduled detection of approaching budget windows, renewal dates, and callbacks.",
        group="Commercial Triggers & Renewals", type="bool",
    ),
    AutomationSettingDef(
        key="sales012_lead_days", label="Opportunity lead time (days)",
        description="How many days in advance of a budget window or renewal date to pre-draft the sales follow-up email.",
        group="Commercial Triggers & Renewals", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales012_no_date_delay_days", label="Undated signal follow-up delay (days)",
        description="Days after initial mention to prompt a follow-up when a commercial signal mentions no explicit due date.",
        group="Commercial Triggers & Renewals", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales012_max_per_run", label="Max commercial triggers queued per run",
        description="Maximum commercial follow-up drafts queued per scheduled run.",
        group="Commercial Triggers & Renewals", type="int", min=1,
    ),

    # ---- SALES-005 - personal touchpoint reminders ----
    AutomationSettingDef(
        key="automations_personal_touchpoints_scan_enabled", label="Personal touchpoints active",
        description="Enables reminders for client returns from leave, milestones, and personal occasions.",
        group="Personal Touchpoints", type="bool",
    ),
    AutomationSettingDef(
        key="sales005_lead_days", label="Advance notice window (days)",
        description="Days before a scheduled personal date to prepare the relationship-building draft.",
        group="Personal Touchpoints", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales005_no_date_delay_days", label="Undated touchpoint delay (days)",
        description="Days after initial correspondence to suggest a follow-up for undated personal mentions.",
        group="Personal Touchpoints", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sales005_max_per_run", label="Max touchpoints queued per run",
        description="Maximum personal touchpoint drafts queued per cycle.",
        group="Personal Touchpoints", type="int", min=1,
    ),

    # ---- SALES-013 - morning follow-up queue ranking ----
    AutomationSettingDef(
        key="sales013_weight_urgency", label="Urgency ranking weight (0.0–1.0)",
        description="Priority weighting assigned to task due dates and overdue intervals in the Morning Queue.",
        group="Morning Queue Prioritization", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="sales013_weight_value", label="Deal value ranking weight (0.0–1.0)",
        description="Priority weighting assigned to potential revenue and linked opportunity value in the Morning Queue.",
        group="Morning Queue Prioritization", type="float", min=0.0, max=1.0,
    ),
    AutomationSettingDef(
        key="sales013_value_cap", label="Maximum deal value threshold (£)",
        description="Deal size treated as the maximum ceiling for value-based ranking normalization.",
        group="Morning Queue Prioritization", type="float", min=1.0,
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
    # ---- Sales Order Register ----
    AutomationSettingDef(
        key="automations_sor_client_match_scan_enabled", label="Client matching active",
        description="Daily: links order-register clients to CRM companies (exact matches automatically, likely matches sent for review).",
        group="Sales Order Register", type="bool",
    ),
    AutomationSettingDef(
        key="sor_match_max_per_run", label="Max match suggestions per run",
        description="Upper limit on new 'is this the same company?' review items created in one run.",
        group="Sales Order Register", type="int", min=1,
    ),
    AutomationSettingDef(
        key="automations_sor_invoice_chase_scan_enabled", label="Uninvoiced booking scan active",
        description="Weekdays: flags booked orders with no invoice number once their issue has published or event has run.",
        group="Sales Order Register", type="bool",
    ),
    AutomationSettingDef(
        key="sor_invoice_grace_days", label="Grace period after publication (days)",
        description="How long after an issue publishes or an event runs before a still-uninvoiced booking is flagged.",
        group="Sales Order Register", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sor_invoice_snooze_days", label="'Remind me later' delay (days)",
        description="How long a booking stays out of the queue after someone chooses 'Not yet - remind me later'.",
        group="Sales Order Register", type="int", min=1,
    ),
    AutomationSettingDef(
        key="sor_invoice_max_per_run", label="Max uninvoiced bookings flagged per run",
        description="Upper limit on new uninvoiced-booking review items created in one run.",
        group="Sales Order Register", type="int", min=1,
    ),
    AutomationSettingDef(
        key="automations_sor_renewal_scan_enabled", label="Renewal outreach active",
        description="Weekdays: drafts a renewal email for last year's advertisers approaching the anniversary of their booking who haven't rebooked (SALES-021).",
        group="Sales Order Register", type="bool",
    ),
    AutomationSettingDef(
        key="sor_renewal_lead_days", label="Renewal lead time (days)",
        description="How many days before the anniversary of last year's booking the renewal draft is queued.",
        group="Sales Order Register", type="int", min=0,
    ),
    AutomationSettingDef(
        key="sor_renewal_max_per_run", label="Max renewals drafted per run",
        description="Upper limit on renewal drafts created in one run (each may use one AI call).",
        group="Sales Order Register", type="int", min=1,
    ),
]

_BY_KEY = {d.key: d for d in AUTOMATION_SETTING_DEFS}


def get_def(key: str) -> AutomationSettingDef | None:
    return _BY_KEY.get(key)
