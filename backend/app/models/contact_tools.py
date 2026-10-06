"""Bulk updates and imports of contacts (Act! feedback B3 / B4).

Both keep enough to be undone: a bulk update remembers each contact's old
value; an import remembers which contacts it created and what it changed on
the ones that already existed.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class BulkEdit(Base, UUIDPk):
    __tablename__ = "bulk_edits"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    field_label: Mapped[str] = mapped_column(String(200), nullable=False)
    op: Mapped[str] = mapped_column(String(12), nullable=False)  # set | clear | replace
    new_value: Mapped[str | None] = mapped_column(Text)
    find_text: Mapped[str | None] = mapped_column(Text)
    scope_label: Mapped[str | None] = mapped_column(String(300))
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # {contact_id: previous value (null = it had none)} - what Undo puts back.
    before: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="applied")  # applied | undone
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContactImport(Base, UUIDPk):
    __tablename__ = "contact_imports"

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_kind: Mapped[str] = mapped_column(String(8), nullable=False)  # xlsx | xls | csv | pdf
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="mapping", index=True)  # mapping | imported | undone
    sheet_name: Mapped[str | None] = mapped_column(String(200))
    sheets: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    has_header: Mapped[bool] = mapped_column(default=True)
    header_row: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    headers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rows: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # list of list of text
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # {"<column index>": {"field": "<FieldDef.key>|skip|new_custom", "name": "<new custom field name>", "type": "<phone type>"}}
    mapping: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    suggestions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # what the matcher proposed and why
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    excluded: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # row numbers the user unticked
    notes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # plain-English parsing notes
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_contact_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_before: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
