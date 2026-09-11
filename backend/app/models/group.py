import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import ProvenanceMixin, TimestampMixin, UUIDPk


class Group(Base, UUIDPk, ProvenanceMixin, TimestampMixin):
    """An Act! Group - BMI's equivalent of a tag/segment/list (titles,
    regions, campaign lists, etc. - meaning varies, see the per-database
    schema docs). Hierarchical, same as Act!.
    """

    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("source_db", "source_act_id", name="uq_groups_source"),)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256))
    hier_level: Mapped[int | None] = mapped_column(Integer)
    hier_path: Mapped[str | None] = mapped_column(String(556))
    parent_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True
    )

    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class GroupMembership(Base, UUIDPk):
    """Contact <-> Group, flattened 1:1 from Act!'s TBL_GROUP_CONTACT junction."""

    __tablename__ = "group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "contact_id", name="uq_group_memberships"),)

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True
    )
