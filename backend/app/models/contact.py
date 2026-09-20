import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
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

    # Act!'s MANAGEUSERID ("Record Manager") backfilled from the source .bak
    # (see migration/backfill_owner.py) - only set when that Act! user
    # resolves to a real, current CRM login; for anyone else (a former
    # employee, a shared/system account), custom_fields["_original_record_manager"]
    # still carries the raw Act! name for context, but this stays null - a
    # dangling owner pointing at nobody would be worse than no owner at all
    # for anything that filters/ranks by it (e.g. the morning follow-up queue).
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
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
    last_email_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Act!'s free-text company name (COMPANYNAME) - distinct from company_id
    # above (the linked Company row). Many contacts carry one and not the
    # other; kept as-is rather than guessed into a link.
    company_name_freetext: Mapped[str | None] = mapped_column(String(256))
    last_results: Mapped[str | None] = mapped_column(String(256))  # Act!'s "Last Results" picklist value

    # Act! Marketing Automation fields - directly relevant to the CS-001
    # bounce-handling automation (app/automations/bounce_handling.py), which
    # currently has no historical bounce signal to start from.
    is_email_opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_bounced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    engagement_score: Mapped[int | None] = mapped_column(Integer)  # Act!'s AMA_SCORE

    # Decoded custom fields, keyed by real label - see Company.custom_fields
    # docstring for the same rule. This is where bmi_notes, print_subscription,
    # the CUST_SL_* Sage fields, newsletter opt-in flags, etc. all live.
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    act_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    act_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContactCompanyLink(Base, UUIDPk):
    """Contact <-> Company, flattened from Act!'s TBL_COMPANY_CONTACT -
    SEPARATE from Contact.company_id above. Act! lets one contact belong to
    several companies (a board member, a consultant working two accounts);
    company_id only ever holds one. 7,959 of these in Prospects alone, so
    genuinely more than an edge case there. row_source records whether Act!
    made the link automatically or a user did.
    """

    __tablename__ = "contact_company_links"
    __table_args__ = (UniqueConstraint("contact_id", "company_id", name="uq_contact_company_links"),)

    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    row_source: Mapped[str | None] = mapped_column(String(1))
