"""Activity <-> Contact / Company / Group associations, plus invitees and
attachments - all pulled from Act! junction tables the original migration
never touched (etl.py only read TBL_ACTIVITY itself). See
migration/README.md's "Known simplifications" section, corrected: Act!
*does* have these links (TBL_CONTACT_ACTIVITY, TBL_COMPANY_ACTIVITY,
TBL_GROUP_ACTIVITY, TBL_ACCESSOR_ACTIVITY, TBL_ATTACHMENT all carry real
row data, especially in the Prospects database) - the original pass just
didn't query them.

One activity can legitimately touch several contacts/companies at once in
Act! (e.g. a meeting with three attendees from the same company, or a call
associated with both a contact and their employer), so these are proper
many-to-many junction tables, not a single nullable FK on Activity itself.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class ActivityContact(Base, UUIDPk):
    """Contact <-> Activity, flattened from Act!'s TBL_CONTACT_ACTIVITY."""

    __tablename__ = "activity_contacts"
    __table_args__ = (UniqueConstraint("activity_id", "contact_id", name="uq_activity_contacts"),)

    activity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True)
    # Act!'s own ISINVITED flag on the junction row - a call/meeting can
    # list a contact as "associated with" without them being an invitee.
    is_invited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ActivityCompany(Base, UUIDPk):
    """Company <-> Activity, flattened from Act!'s TBL_COMPANY_ACTIVITY."""

    __tablename__ = "activity_companies"
    __table_args__ = (UniqueConstraint("activity_id", "company_id", name="uq_activity_companies"),)

    activity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)


class ActivityGroup(Base, UUIDPk):
    """Group <-> Activity, flattened from Act!'s TBL_GROUP_ACTIVITY. Low
    volume everywhere (2 rows total across all three databases) but kept
    for completeness rather than silently dropped."""

    __tablename__ = "activity_groups"
    __table_args__ = (UniqueConstraint("activity_id", "group_id", name="uq_activity_groups"),)

    activity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)


class ActivityInvitee(Base, UUIDPk):
    """Who's invited to a call/meeting - Act!'s "Invitee" column in the
    Task List, from TBL_ACCESSOR_ACTIVITY (accessor = an Act! user
    account). Stored as a plain display name, NOT a FK to our own `users`
    table: Act!'s accessor accounts have no established mapping to our CRM
    user accounts (same gap as Activity.created_by_user_id/ORGANIZEUSERID -
    see activity.py's docstring and BACKLOG.md) - resolving that mapping is
    a human decision ("Clare Hunter in Act! = which of our user accounts?"),
    parked for the final cutover migration. Denormalizing the name now
    means the Invitee column can render correctly today without waiting on
    that mapping; a real user_id FK can be backfilled once it exists,
    without needing to touch this table's shape.
    """

    __tablename__ = "activity_invitees"
    __table_args__ = (UniqueConstraint("activity_id", "accessor_name", name="uq_activity_invitees"),)

    activity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False, index=True)
    accessor_name: Mapped[str] = mapped_column(String(256), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)


class Attachment(Base, UUIDPk):
    """A file attached to a Note, History entry, or Activity - from Act!'s
    TBL_ATTACHMENT. Act! stores a filesystem path (FILEPATH/MACHINENAME)
    into wherever Act!'s own file store lived, which is meaningless outside
    that machine - so this migrates the *metadata* (there was a file named
    X attached to record Y) as a record of what existed, not a working
    download link. Real row data: 215 in Prospects, 2 in Onboard, 0 in
    SellingTravel.
    """

    __tablename__ = "attachments"
    __table_args__ = (UniqueConstraint("source_db", "source_act_id", name="uq_attachments_source"),)

    source_db: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_act_id: Mapped[str] = mapped_column(String(64), nullable=False)

    note_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("notes.id"), index=True)
    history_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("history_entries.id"), index=True)
    activity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("activities.id"), index=True)

    file_name: Mapped[str | None] = mapped_column(String(512))
    display_name: Mapped[str | None] = mapped_column(String(512))
