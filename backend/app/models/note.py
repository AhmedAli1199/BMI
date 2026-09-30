import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, UUIDPk

# Flattened from Act!'s many-to-many junction tables (TBL_CONTACT_NOTE,
# TBL_COMPANY_NOTE, TBL_GROUP_NOTE, ...) to a single entity_type +
# entity_id per note, per the schema-design recommendation in
# docs/act-schema/onboard-schema.md: in practice each note attaches to
# exactly one entity in this data, and a flat model is much simpler to
# build a UI and automations against than a true many-to-many.
# Group/Opportunity notes were dropped by the original migration pass
# (~648 group notes alone, mostly in Prospects) - added here since they're
# real data, not Act! plumbing.
NOTE_ENTITY_TYPES = ("contact", "company", "group", "opportunity")


class Note(Base, UUIDPk, ProvenanceMixin):
    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint("source_db", "source_act_id", name="uq_notes_source"),
        CheckConstraint("entity_type IN ('contact', 'company', 'group', 'opportunity')", name="ck_notes_entity_type"),
    )

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # No DB-level FK here on purpose - entity_id points at either contacts.id
    # or companies.id depending on entity_type, which a single FK can't
    # express. The ETL guarantees it always points at a row that exists.
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    note_type: Mapped[str | None] = mapped_column(String(50))  # "Note" / "AI Summary"
    body: Mapped[str | None] = mapped_column(Text)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    act_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
