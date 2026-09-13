import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, TimestampMixin, UUIDPk


class Contact(Base, UUIDPk, ProvenanceMixin, TimestampMixin):
    """A person. One row per Act! contact per source database - see the
    "separate per-title records" decision (CONTEXT.md's open question,
    resolved 2026-09-11): the same real person appearing under more than one
    BMI title stays as separate contact rows, each with its own provenance,
    rather than being merged. Revisit only if BMI explicitly asks for a
    unified-person view later.
    """

    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("source_db", "source_act_id", name="uq_contacts_source"),)

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True
    )

    first_name: Mapped[str | None] = mapped_column(String(128))
    middle_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(256))
    full_name: Mapped[str | None] = mapped_column(String(256))
    name_prefix: Mapped[str | None] = mapped_column(String(64))
    name_suffix: Mapped[str | None] = mapped_column(String(64))
    salutation: Mapped[str | None] = mapped_column(String(64))

    job_title: Mapped[str | None] = mapped_column(String(256))
    department: Mapped[str | None] = mapped_column(String(256))
    category: Mapped[str | None] = mapped_column(String(512))
    referred_by: Mapped[str | None] = mapped_column(String(128))

    birthdate: Mapped[date | None] = mapped_column(Date)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set by the bounce-handling automation on a confirmed hard bounce -
    # never by hand-editing a field elsewhere, so it always has a note
    # explaining why right next to it.
    is_unsubscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    last_meet_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reach_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_letter_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Decoded custom fields, keyed by real label - see Company.custom_fields
    # docstring for the same rule. This is where bmi_notes, print_subscription,
    # the CUST_SL_* Sage fields, newsletter opt-in flags, etc. all live.
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    act_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    act_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
