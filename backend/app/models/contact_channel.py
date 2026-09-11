"""Address / Phone / Email - each attaches to exactly one Contact OR one
Company (never both, never neither - enforced by a CHECK constraint).

Act!'s versions of these tables can also attach to a Group or an
Opportunity; that's rare and not carried over here to keep the schema
simple, per the "keep things simple" instruction - a handful of
group/opportunity-level addresses are left behind in Act! rather than
migrated. If BMI later needs those, they're still recoverable from the
original .bak backups.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, UUIDPk

_OWNER_CHECK = "(contact_id IS NOT NULL) <> (company_id IS NOT NULL)"


class Address(Base, UUIDPk, ProvenanceMixin):
    __tablename__ = "addresses"
    __table_args__ = (
        UniqueConstraint("source_db", "source_act_id", name="uq_addresses_source"),
        CheckConstraint(_OWNER_CHECK, name="ck_addresses_one_owner"),
    )

    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))

    # Resolved from Act!'s TYPEID via the picklist (e.g. "Business", "Home"),
    # stored as plain text rather than a separate lookup table - simple, and
    # BMI can just type a new one if they ever need it.
    type_label: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    line1: Mapped[str | None] = mapped_column(String(512))
    line2: Mapped[str | None] = mapped_column(String(512))
    line3: Mapped[str | None] = mapped_column(String(512))
    city: Mapped[str | None] = mapped_column(String(512))
    state: Mapped[str | None] = mapped_column(String(512))
    postal_code: Mapped[str | None] = mapped_column(String(512))
    country: Mapped[str | None] = mapped_column(String(512))
    latitude: Mapped[float | None] = mapped_column(Numeric)
    longitude: Mapped[float | None] = mapped_column(Numeric)


class Phone(Base, UUIDPk, ProvenanceMixin):
    __tablename__ = "phones"
    __table_args__ = (
        UniqueConstraint("source_db", "source_act_id", name="uq_phones_source"),
        CheckConstraint(_OWNER_CHECK, name="ck_phones_one_owner"),
    )

    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))

    type_label: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    number: Mapped[str | None] = mapped_column(String(64))
    country_code: Mapped[int | None] = mapped_column(SmallInteger)


class Email(Base, UUIDPk, ProvenanceMixin):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("source_db", "source_act_id", name="uq_emails_source"),
        CheckConstraint(_OWNER_CHECK, name="ck_emails_one_owner"),
    )

    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))

    type_label: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    address: Mapped[str | None] = mapped_column(String(512), index=True)
