"""The three access tiers every user account gets, and what each grants.
Kept as one small source of truth (not scattered string checks) since
both the backend (validating a role on create/update) and the frontend
(deciding what to show) need to agree on exactly these three values.

None of this enforces database/group scoping by itself - that's
UserAccess (app/models/user_access.py). Role answers "what can they DO",
UserAccess answers "on which data can they do it".
"""
from __future__ import annotations

from dataclasses import dataclass

ROLE_ADMIN = "admin"
ROLE_DATA_MANAGER = "data_manager"
ROLE_SALES = "sales"

ALL_ROLES = (ROLE_ADMIN, ROLE_DATA_MANAGER, ROLE_SALES)


@dataclass(frozen=True)
class RoleDef:
    value: str
    label: str
    description: str


ROLE_DEFS: list[RoleDef] = [
    RoleDef(
        ROLE_ADMIN,
        "Administrator",
        "Full access to every database, user management, Settings, and the Automations review queue. "
        "Can add new databases.",
    ),
    RoleDef(
        ROLE_DATA_MANAGER,
        "Data Manager",
        "Full read/write on Contacts, Companies, and Groups within their assigned database(s), plus the "
        "Automations review queue. Cannot manage other users or add new databases.",
    ),
    RoleDef(
        ROLE_SALES,
        "Sales",
        "Read/write on Contacts, Companies, and Groups within their assigned database(s) only. No "
        "Automations, no Settings beyond their own preferences, no user management.",
    ),
]

# role -> whether it can reach the Automations review queue / producer job status.
CAN_USE_AUTOMATIONS = {ROLE_ADMIN, ROLE_DATA_MANAGER}
# role -> whether it can manage other users' accounts/access.
CAN_MANAGE_USERS = {ROLE_ADMIN}
# role -> whether it can register a new database (Publication).
CAN_ADD_DATABASE = {ROLE_ADMIN}
