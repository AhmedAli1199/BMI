from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BMI Sales Brain API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/bmi"
    cors_origins: list[str] = ["http://localhost:3000"]
    api_key: str = "dev-only-change-me"

    # Automation producer jobs (see app/automations/scheduler.py) - each
    # defaults OFF so adding a job never starts writing to the review
    # queue on its own. Flip to true + restart the container to turn one
    # on; no code change or redeploy needed for that switch alone.
    automations_bounce_scan_enabled: bool = False  # CS-001 + CS-002 (bounce classification, OOO mining)
    automations_departure_scan_enabled: bool = False  # CS-003 (departure & successor finding)
    automations_followup_scan_enabled: bool = False  # Follow-up Engine + Morning Queue (SALES-005/012/013)
    automations_dedupe_scan_enabled: bool = False  # CS-004 (duplicate/moved-person merge)

    # CS-004 tuning - see app/automations/dedupe.py.
    dedupe_max_per_run: int = 30
    dedupe_confidence_floor: float = 0.55  # below this, don't even suggest it - see MATCH_THRESHOLD-style gating elsewhere

    # How many contacts the scan examines as match candidates per run -
    # NOT the same thing as dedupe_max_per_run (which caps queued output).
    # This bounds the actual query cost, which scales with how many
    # contacts get driven through the trigram lookup, not with how many
    # pairs end up confident enough to queue - see dedupe.py's
    # scan_for_duplicates() docstring for why that distinction matters at
    # real contact-table scale.
    dedupe_batch_size: int = 500

    # How far the follow-up scan looks for "due" Activities - see
    # app/automations/followup_queue.py's module docstring for why this is
    # bounded rather than "every incomplete activity ever". Configurable
    # since the right window depends on how forward-looking your actual
    # data is - freshly-migrated historical data may need a much wider
    # lookback to surface anything at all, vs. a CRM in daily live use
    # where a narrow "due this week" window is exactly right.
    followup_lookback_days: int = 14
    followup_lookahead_days: int = 1
    followup_max_per_run: int = 40

    # OpenAI - used only by app/automations/llm.py to draft follow-up text
    # (and any future automation that needs generated prose). Left empty by
    # default; llm.py falls back to a plain templated draft (no AI) rather
    # than crashing when this is unset, so the follow-up scan still works -
    # just without AI-personalized wording - until a key is added. See
    # llm.py's docstring for exactly where this is read.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Microsoft Graph app registration (client-credentials flow, no per-user
    # login) - used by /api/diagnostics/graph-mailboxes to confirm which of
    # BMI's mailboxes are actually readable before CS-001/002/003 depend on
    # them, and later by the real mailbox-scanning jobs themselves. Left
    # empty by default; the diagnostics route reports "not configured"
    # rather than crashing when they're unset.
    graph_tenant_id: str = ""
    graph_client_id: str = ""
    graph_client_secret: str = ""

    # Comma-separated mailbox addresses the CS-001/002 scan actually reads
    # (app/automations/bounce_handling.py) - separate from diagnostics.py's
    # own hardcoded probe list, since which mailboxes are worth continuously
    # scanning is an operational choice that may end up narrower (or wider)
    # than "every address IT confirmed is readable". Empty by default - the
    # scan logs and does nothing rather than guessing which mailboxes matter.
    graph_scan_mailboxes: str = ""

    # How far back the bounce/OOO scan looks the very first time it runs
    # for a given mailbox (before it has its own cursor to resume from) -
    # see app/automations/state.py. Every run after that only asks for what
    # arrived since the previous run, however often the job fires.
    bounce_scan_initial_lookback_minutes: int = 1440

    # SALES-010-lite (Email Exchange Summarising) - see
    # app/automations/email_summary.py. Deliberately OFF by default and a
    # separate mailbox list from graph_scan_mailboxes above: this scan reads
    # a salesperson's own 1:1 correspondence with known contacts (not a
    # shared bounce inbox), so which mailboxes belong here is a real
    # business-role decision, not just "whatever IT gave Graph access to".
    automations_email_summary_scan_enabled: bool = False
    graph_email_summary_mailboxes: str = ""
    email_summary_max_recipients: int = 3  # drop anything with more people on the thread - group mail, not 1:1 sales talk
    email_summary_min_body_chars: int = 40  # drop pure one-line acks ("Thanks!") - nothing there to extract
    email_summary_initial_lookback_minutes: int = 1440
    # BMI's own email domains - a thread where BOTH the sender and the
    # matched contact are on one of these is staff-to-staff internal mail
    # that happened to match a legacy/duplicate Contact row (e.g. a record
    # manager who also has their own contact record from the Act! import),
    # never a real client conversation. Comma-separated, case-insensitive.
    email_summary_internal_domains: str = "bmipublishing.co.uk,onboardhospitality.com,sellingtravel.com"

    # SALES-011 (Inbound Contact Capture) - see
    # app/automations/inbound_capture.py. A distinct mailbox list from both
    # of the above: this scan wants a shared enquiry/enquiries-style inbox
    # that receives genuinely new senders, not a salesperson's personal
    # mailbox or the bounce-handling shared inbox.
    automations_inbound_capture_scan_enabled: bool = False
    # Each entry is "mailbox:source_db" - which Act! database's companies/
    # groups a lead from that mailbox should be matched/suggested against
    # (a business mapping, not something derivable from the address alone).
    graph_inbound_capture_mailboxes: str = ""
    inbound_capture_max_recipients: int = 3
    inbound_capture_min_body_chars: int = 30
    inbound_capture_initial_lookback_minutes: int = 1440

    # SALES-002 (Business Card Dedupe & Group Assignment) - see
    # app/automations/business_card.py. An MS Teams "Incoming Webhook"
    # connector URL a batch-confirm summary (added/updated/skipped) is
    # posted to. Left blank, the summary is just logged - nothing fails or
    # blocks a write for lack of a webhook.
    teams_webhook_url: str = ""


settings = Settings()
