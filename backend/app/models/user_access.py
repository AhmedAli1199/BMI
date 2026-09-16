import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserAccess(Base):
    """One database (Publication.slug) a user can see, optionally scoped
    to a single Group's subtree within it. An admin's access is implicit
    (their role alone grants everything) and never needs rows here.

    group_id is NULL for "the whole database"; set for "just this group
    and its subgroups" - see the recursive query in
    app/api/routes/contacts.py's group_id filter. A user can hold several
    rows (e.g. full OnBoard + a group-scoped slice of Prospects).
    """

    __tablename__ = "user_access"
    __table_args__ = (
        UniqueConstraint("user_id", "source_db", "group_id", name="uq_user_access_scope"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_db: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
