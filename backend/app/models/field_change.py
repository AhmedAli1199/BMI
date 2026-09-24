"""Per-user audit trail for direct field edits - "this might be a bit
obvious but the ability to identify which BMI user has made changes to
specific data" (BMI's Act pain-points doc).

Deliberately narrow, v1 scope: only Contact/Company field edits made via
their own PATCH routes (app/api/routes/contacts.py, companies.py) are
recorded here. Note/History/Activity already carry their own
created_by_user_id and don't need this table; extending to sub-records
(Address/Phone/Email) is a later, separable addition once this exists,
not something to try to cover in one pass.

One row per *changed field* per edit (not one row per PATCH call) - a
single "update job title and department" request writes two rows here,
so "what changed on this field, ever" is a direct filter, not something
that requires parsing a JSON blob of the whole request.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class FieldChange(Base, UUIDPk):
    __tablename__ = "field_changes"
    __table_args__ = (
        CheckConstraint("entity_type IN ('contact', 'company')", name="ck_field_changes_entity_type"),
    )

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    field: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)

    # Nullable for the same reason Note/History's created_by_user_id is:
    # a caller that never forwarded identity headers (see
    # core/identity.py's fail-open trust model) shouldn't block the write,
    # it just means this one row can't say who made the change.
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
