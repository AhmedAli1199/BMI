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


settings = Settings()
