import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, UUIDPk


class Opportunity(Base, UUIDPk, ProvenanceMixin):
    """Migrated as-is from Act!'s TBL_OPPORTUNITY - kept per explicit
    instruction, not redesigned. Only 7 rows total across all three
    databases, so this is deliberately a thin, mostly-flat model rather
    than a full pipeline-stage system; revisit if BMI starts using
    Opportunities for real going forward.
    """

    __tablename__ = "opportunities"
    __table_args__ = (UniqueConstraint("source_db", "source_act_id", name="uq_opportunities_source"),)

    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))

    name: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str | None] = mapped_column(String(26))
    stage_name: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(128))
    competitor: Mapped[str | None] = mapped_column(String(256))
    close_reason: Mapped[str | None] = mapped_column(String(256))

    total_amount: Mapped[float | None] = mapped_column(Numeric)
    probability_pct: Mapped[int | None] = mapped_column(SmallInteger)

    open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
