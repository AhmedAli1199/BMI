"""Creates (or updates the role/access of) BMI's real team accounts, per
the Act! User & Role sheet Clare shared. Idempotent by email - re-running
never resets an existing person's password, only their role/access, so
it's safe to re-run after adjusting the ROSTER below.

Passwords are only ever generated and printed once, at creation time -
this script deliberately never re-prints or logs a password for someone
who already exists.

Usage (run against whichever DATABASE_URL is currently set):
    python -m scripts.seed_team
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Group, User, UserAccess  # noqa: E402

# access: list of (source_db, group_name | None) - group_name is resolved
# to a Group.id by name+source_db at run time, never hardcoded, so this
# works against any environment's actual group IDs.
ROSTER = [
    ("Kay Fisher", "kay.fisher@bmipublishing.co.uk", "data_manager",
     [("onboard", None), ("prospects", None), ("sellingtravel", None)]),
    ("Shani Kunar", "shani.kunar@bmipublishing.co.uk", "data_manager",
     [("prospects", None), ("sellingtravel", None)]),
    ("Kirsty Hicks", "kirsty.hicks@bmipublishing.co.uk", "sales",
     [("prospects", "BUSINESS")]),
    ("Neil Dargie", "neil.dargie@bmipublishing.co.uk", "sales",
     [("prospects", "BUSINESS")]),
    ("Steven Thompson", "steven.thompson@bmipublishing.co.uk", "sales",
     [("prospects", "1 Selling Travel")]),
    ("Sally Parker", "sally.parker@bmipublishing.co.uk", "sales",
     [("prospects", "1 Selling Travel")]),
    ("David Wilcox", "david.wilcox@bmipublishing.co.uk", "sales",
     [("prospects", "1 Selling Travel")]),
    ("Susan Thompson", "susan.thompson@bmipublishing.co.uk", "data_manager",
     [("sellingtravel", None)]),
    ("Craig McQuinn", "craig.mcquinn@bmipublishing.co.uk", "sales",
     [("onboard", None)]),
    ("Sue Williams", "sue.williams@onboardhospitality.com", "sales",
     [("onboard", None)]),
    ("Clare Hunter", "clare.hunter@bmipublishing.co.uk", "admin", []),  # admin needs no access rows
]


def resolve_group_id(db, source_db: str, group_name: str):
    group = db.scalar(select(Group).where(Group.source_db == source_db, Group.name == group_name))
    if not group:
        raise SystemExit(f"Group {group_name!r} not found in {source_db!r} - check it was migrated.")
    return group.id


def main() -> None:
    db = SessionLocal()
    created: list[tuple[str, str, str]] = []  # (name, email, password)
    try:
        for name, email, role, access in ROSTER:
            email = email.lower()
            user = db.scalar(select(User).where(User.email == email))
            if user:
                user.name = name
                user.role = role
                print(f"Updated {email} (role={role}) - password left unchanged")
            else:
                password = secrets.token_urlsafe(12)
                user = User(email=email, name=name, hashed_password=hash_password(password), role=role)
                db.add(user)
                db.flush()
                created.append((name, email, password))
                print(f"Created {email} (role={role})")

            db.execute(UserAccess.__table__.delete().where(UserAccess.user_id == user.id))
            for source_db, group_name in access:
                group_id = resolve_group_id(db, source_db, group_name) if group_name else None
                db.add(UserAccess(user_id=user.id, source_db=source_db, group_id=group_id))
            db.commit()

        if created:
            print("\n--- New account passwords (shown once - save these now) ---")
            for name, email, password in created:
                print(f"{name} <{email}>: {password}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
