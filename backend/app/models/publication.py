import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Publication(Base):
    """A "database" in the sense BMI uses the word - one of the three
    original Act! titles (OnBoard/Prospects/SellingTravel), or a new one
    added directly in the CRM. This does NOT create a new Postgres
    database or schema - it's a label. `slug` is exactly what's stored in
    every other table's `source_db` column, so adding a row here is what
    makes a new source_db value valid to pick when creating a contact or
    company (see app/api/routes/contacts.py / companies.py's source_db
    validation).
    """

    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256))
    # Both purely cosmetic - a key the frontend maps to a fixed palette of
    # colors/icons (see frontend/src/lib/publication-style.tsx), never
    # raw CSS/markup, so a bad value can't inject anything.
    color: Mapped[str] = mapped_column(String(32), nullable=False, default="slate")
    icon: Mapped[str] = mapped_column(String(32), nullable=False, default="newspaper")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
