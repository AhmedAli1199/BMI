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

    # AI provider preference (see app/automations/llm.py's docstring for
    # the full contract): every AI call - text drafting AND vision - tries
    # Gemini first if GEMINI_API_KEY is set, falling back to OpenAI
    # automatically on any Gemini failure or if that key isn't set at all.
    # OpenAI is the only key strictly required (it's the fallback everything
    # lands on); Gemini is additive. No separate provider-selection setting
    # to keep in sync - which provider actually served a call is entirely
    # determined by which key(s) are present.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str = ""
    gemini_text_model: str = "gemini-3.6-flash"
    # gemini-2.0-flash was retired - Google's own 404 response when it was
    # first tried against a real key explicitly named this as the
    # replacement ("models/gemini-2.0-flash is no longer available...use
    # models/gemini-3.6-flash"), so this is taken directly from that
    # response, not guessed. If Google retires this one too, the error
    # will name its replacement the same way - update this default (or
    # just set GEMINI_VISION_MODEL/GEMINI_TEXT_MODEL directly, no code
    # change needed) then.
    gemini_vision_model: str = "gemini-3.6-flash"

    # Reliability: every real Gemini/OpenAI call in app/automations/llm.py
    # retries this many times (with exponential backoff) on a transient/
    # rate-limit error specifically - not on a genuine bad-request/auth
    # error, which retrying would never fix. Set to 0 to disable retries
    # entirely (immediate single-attempt, old behavior).
    llm_max_retries: int = 3
    llm_retry_base_delay_seconds: float = 2.0

    # Throttle: a minimum gap enforced between successive LLM calls made
    # from the SAME scan run's loop (inbound_capture.py, bounce_handling.py)
    # - spreads a burst of 20+ calls out over several seconds instead of
    # firing them back to back, which is what was tripping Gemini's
    # per-minute rate limit in production and silently defaulting every
    # capped-out classification to "can't tell, assume genuine".
    llm_call_min_interval_seconds: float = 1.1

    # Cost dashboard (/api/automations/llm-usage, see app/models/llm_usage.py)
    # - $ per 1,000,000 tokens, input vs output, per provider, used as the
    # fallback for any model with no entry in llm_cost_overrides_json
    # below. Neither provider's API response includes a dollar cost field -
    # token counts are exact (read straight off the response), the $ figure
    # is always this rate table multiplied by those tokens, same as every
    # third-party LLM cost tracker does it. Editable at runtime
    # (Automations Settings) since list prices change; historical usage
    # rows already store their own computed cost and are never rewritten
    # retroactively.
    #
    # Gemini default = gemini-3.6-flash's actual current list price,
    # confirmed 2026-09-22 against https://ai.google.dev/gemini-api/docs/pricing:
    # $0.75 input / $3.75 output per 1M tokens through 2026-12-31 (output
    # price explicitly includes thinking tokens), rising to $1.50 / $7.50
    # from 2027-01-01 - update this (or add a dated llm_cost_overrides_json
    # entry) when that takes effect.
    llm_cost_gemini_input_per_1m: float = 0.75
    llm_cost_gemini_output_per_1m: float = 3.75
    # OpenAI default = gpt-4o-mini's published rate at the time this was
    # written - not re-verified as carefully as the Gemini figure above;
    # confirm against https://openai.com/api/pricing before relying on it.
    llm_cost_openai_input_per_1m: float = 0.15
    llm_cost_openai_output_per_1m: float = 0.60

    # Exact-model overrides, as a JSON object: {"<model name>": {"input":
    # <$/1M tokens>, "output": <$/1M tokens>}, ...}. Checked before the
    # provider-level defaults above - lets each model actually in use
    # (settings.gemini_text_model, gemini_vision_model, openai_model) have
    # its own real rate instead of one flat per-provider guess, without a
    # code change when a model is swapped. Malformed JSON is ignored (logged,
    # falls back to the provider default) rather than blocking a call.
    # Defaults to an explicit gemini-3.6-flash entry mirroring the verified
    # rate above, as a concrete example of the override shape.
    llm_cost_overrides_json: str = '{"gemini-3.6-flash": {"input": 0.75, "output": 3.75}}'

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
    # Same cap-and-defer mechanism as inbound_capture_llm_max_per_run above,
    # for the OOO replacement-extraction call - smaller default since OOO
    # volume runs much lower than inbound capture.
    ooo_llm_max_per_run: int = 25

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
    # Hard cap on how many messages get the LLM intent-classification call
    # (new_inquiry/reply/spam/...) in ONE run, across all mailboxes
    # combined - bounds cost on a traffic spike. Anything past the cap
    # isn't lost: the cursor only advances past what was actually
    # processed this run, so the rest is picked up on the next tick.
    inbound_capture_llm_max_per_run: int = 40

    # SALES-002 (Business Card Dedupe & Group Assignment) - see
    # app/automations/business_card.py. An MS Teams "Incoming Webhook"
    # connector URL a batch-confirm summary (added/updated/skipped) is
    # posted to. Left blank, the summary is just logged - nothing fails or
    # blocks a write for lack of a webhook.
    teams_webhook_url: str = ""

    # SALES-012 (Budget-Window & Renewal Triggers) - see
    # app/automations/signal_triggers.py.
    automations_signal_triggers_scan_enabled: bool = False
    sales012_lead_days: int = 14  # trigger a dated signal once its due_date is this many days out
    sales012_no_date_delay_days: int = 3  # trigger an undated signal this many days after it was first extracted
    sales012_max_per_run: int = 25


settings = Settings()
