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
    RoleDef(ROLE_ADMIN, "Administrator", "Sees everything and manages the team."),
    RoleDef(ROLE_DATA_MANAGER, "Data Manager", "Full access to their assigned database(s)."),
    RoleDef(ROLE_SALES, "Sales", "Their own contacts, tasks, and queue only."),
]

# role -> whether it can reach the Automations Hub (job status, settings,
# LLM cost, the data-reset action) and every review-queue kind, not just
# the sales-audience ones - see app/automations/registry.py's
# ReviewKind.audience. Kept as the narrower, admin-facing set its name
# always meant; CAN_VIEW_OWN_QUEUE below is the new, wider one.
CAN_USE_AUTOMATIONS = {ROLE_ADMIN, ROLE_DATA_MANAGER}
# role -> whether it can see a Today/Review Queue view AT ALL - every
# role gets this now; WHAT they see within it is scoped separately (see
# app/core/identity.py + review_queue.py/automations.py's filtering) by
# audience + source_db(+owner for a sales rep's own queue).
CAN_VIEW_OWN_QUEUE = {ROLE_ADMIN, ROLE_DATA_MANAGER, ROLE_SALES}
# role -> whether it can manage other users' accounts/access.
CAN_MANAGE_USERS = {ROLE_ADMIN}
# role -> whether it can register a new database (Publication).
CAN_ADD_DATABASE = {ROLE_ADMIN}
