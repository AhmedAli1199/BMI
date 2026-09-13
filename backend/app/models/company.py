import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, TimestampMixin, UUIDPk


class Company(Base, UUIDPk, ProvenanceMixin, TimestampMixin):
    """A company/organization. One row per Act! company per source database -
    see the "separate per-title records" decision: the same real-world
    company appearing in more than one Act! database becomes more than one
    row here, each with its own provenance.
    """

    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("source_db", "source_act_id", name="uq_companies_source"),)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256))
    category: Mapped[str | None] = mapped_column(String(512))
    industry: Mapped[str | None] = mapped_column(String(128))
    territory: Mapped[str | None] = mapped_column(String(128))
    region: Mapped[str | None] = mapped_column(String(128))
    division: Mapped[str | None] = mapped_column(String(128))
    num_employees: Mapped[int | None] = mapped_column(Integer)
    revenue: Mapped[float | None] = mapped_column(Numeric)
    website: Mapped[str | None] = mapped_column(String(256))
    referred_by: Mapped[str | None] = mapped_column(String(128))
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Act!'s own company hierarchy (a company can be a subsidiary of another
    # company in the SAME source database - cross-database parents can't
    # happen since we keep records per-title).
    parent_company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True
    )

    # Every custom field (CUST_*, USER1-10) that wasn't important enough to
    # get its own column, keyed by its decoded Act! label (via
    # TBL_SYSCOLUMN.DISPLAYNAME), not its raw CUST_*_<digits> column name.
    # Per CONTEXT.md: flexible jsonb until we know which fields BMI actually
    # uses day to day. See docs/act-schema/*.md for what's in here per
    # source database - it differs significantly title to title.
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    act_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    act_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
