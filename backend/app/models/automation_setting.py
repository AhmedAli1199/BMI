"""Per-key runtime override for an automation's tunable setting - lets the
Automations UI change something (a mailbox list, a lookback window, a
confidence floor) without an env var edit + redeploy. Deliberately a
separate table from AutomationState (automation_state.py): that one is
internal scan-cursor bookkeeping no UI ever touches; this one is
user-facing config, listed and edited via
app/automations/settings_registry.py + the /api/automations/settings
routes.

A key with no row here means "use the env var / code default" (see
app/automations/runtime_settings.py's get()) - so nothing needs backfilling
when a new tunable setting is added, same "absence means default" pattern
used by user preferences (app/preferences.py).
"""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AutomationSetting(Base):
    __tablename__ = "automation_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)  # always {"v": <actual value>} - see runtime_settings.py
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
