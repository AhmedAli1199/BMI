"""Shared mixins for migrated (Act!-sourced) tables.

Every table that holds data migrated from Act! carries the same three groups
of columns, defined once here so they can't drift table to table:

- `id`: our own primary key, a fresh UUID. Never reuse Act!'s own GUIDs as
  our PKs (see ProvenanceMixin) - keeps our schema independent of the
  source system's ID scheme.
- ProvenanceMixin: `source_db` + `source_act_id` - permanent audit trail of
  "where did this row originally come from", per CONTEXT.md. Not a
  temporary migration artifact - never drop these columns after go-live.
- TimestampMixin: `created_at` / `updated_at` - when *our* system first
  ingested/last touched the row, separate from `act_created_at` /
  `act_edited_at` (the original Act! timestamps), which live on the
  individual models that carry them.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# The three source Act! databases, exactly as documented in docs/act-schema/.
# Used as the allowed values for every source_db column - keep in sync with
# migration/etl.py's SOURCE_DBS.
SOURCE_DBS = ("onboard", "prospects", "sellingtravel")


class UUIDPk:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class ProvenanceMixin:
    """Where this row came from in Act!. Always set together, always kept.

    source_db is a Publication.slug (see app/models/publication.py) - 64
    chars wide to match PUBLICATION_SLUG_PATTERN's max, not just the three
    original Act! slugs, since "add a new database" lets someone create a
    longer one directly in the CRM.
    """

    source_db: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_act_id: Mapped[str] = mapped_column(String(64), nullable=False)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def fk_uuid(target: str, nullable: bool = True):
    """Shorthand for a nullable/required UUID foreign key column."""
    return mapped_column(UUID(as_uuid=True), ForeignKey(target), nullable=nullable)
