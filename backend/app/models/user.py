import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # See app/roles.py for the allowed values and what each grants.
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="sales")
    # Disabling access (someone leaves BMI, a contractor's engagement
    # ends) is a flag flip, not a delete - keeps their name attributable
    # on notes/history/review-queue actions they took while active.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Sparse {preference_key: option_value} - a missing key means "use the
    # registry's default" (see app/preferences.py), so adding a new
    # preference never needs a migration or a backfill.
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
