"""Who's actually calling the API, carried over from the frontend's
already-verified session - not re-verified here (see the trust model
note below), just read off trusted headers `backend.ts` now attaches to
every request.

Trust model: the ONLY thing that gets a request past this backend at all
is the shared BACKEND_API_KEY (see app/api/deps.py / main.py's API-key
check) - that key is held only by the Next.js server, never the browser.
Everything in this file is a second, finer-grained layer ON TOP of that:
once a request already holds the master key, it also carries who it's
really on behalf of, so a route can scope data to that person instead of
returning everything the master key can see. It is not a replacement for
the API-key check, and it fails OPEN (identity absent -> unrestricted)
rather than closed, deliberately: an internal script or a caller that
doesn't (yet) forward these headers already had full access before this
existed, and nothing here should silently break that. What it prevents
is the frontend showing a real, logged-in rep more than their own
data - which is the actual problem this phase is closing.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field

from fastapi import Header

from app.roles import ROLE_ADMIN

logger = logging.getLogger("app.core.identity")


@dataclass(frozen=True)
class Identity:
    user_id: str | None = None
    role: str | None = None
    # (source_db, group_id | None) pairs - mirrors UserAccess exactly.
    access: list[tuple[str, str | None]] = field(default_factory=list)

    @property
    def is_known(self) -> bool:
        """False when no identity headers were forwarded at all (an
        internal/out-of-band caller) - the one case every scoping
        function below treats as unrestricted, see module docstring."""
        return self.role is not None

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def user_uuid(self) -> uuid.UUID | None:
        """user_id as a real UUID for a FK column (FieldChange.changed_by_
        user_id, etc.) - None for anything that isn't one, most notably
        the frontend's local-dev bypass identity (sub="local-dev", see
        frontend/src/lib/session.ts), which is a real, known identity
        (role is set) but was never issued a database user row. Every
        caller that writes this into a FK column should use this instead
        of parsing user_id directly - a non-UUID id must never fail the
        request itself (fail-open, same as the rest of this module), it
        should just mean "can't attribute this one to a real user"."""
        if not self.user_id:
            return None
        try:
            return uuid.UUID(self.user_id)
        except ValueError:
            return None

    def allowed_source_dbs(self) -> set[str] | None:
        """None = unrestricted (admin, or no identity forwarded). An
        empty set (a real, known non-admin identity with zero access
        rows) correctly means "nothing" - fail closed for that case,
        it's a real person with no grants, not a missing header."""
        if not self.is_known or self.is_admin:
            return None
        return {source_db for source_db, _ in self.access}


def get_identity(
    x_user_id: str | None = Header(default=None, alias="X-BMI-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-BMI-User-Role"),
    x_user_access: str | None = Header(default=None, alias="X-BMI-User-Access"),
) -> Identity:
    access: list[tuple[str, str | None]] = []
    if x_user_access:
        try:
            parsed = json.loads(x_user_access)
            if isinstance(parsed, list):
                access = [
                    (a["source_db"], a.get("group_id"))
                    for a in parsed
                    if isinstance(a, dict) and a.get("source_db")
                ]
        except (ValueError, TypeError, KeyError):
            logger.warning("identity: ignoring malformed X-BMI-User-Access header")

    return Identity(user_id=x_user_id or None, role=x_user_role or None, access=access)
