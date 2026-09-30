"""Small persistent key/value store for automation producer jobs that need
to remember something across runs (and across container restarts/deploys) -
e.g. "the last message timestamp we already processed for mailbox X", so a
15-minute scan doesn't reread the same messages forever. Deliberately
generic (one table, arbitrary JSONB value) rather than a bespoke column
somewhere, since the only two operations needed are "read what I stored" and
"replace it" - see app/automations/state.py.
"""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AutomationState(Base):
    __tablename__ = "automation_state"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
