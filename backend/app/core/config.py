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


settings = Settings()
