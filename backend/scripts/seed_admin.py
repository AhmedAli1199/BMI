"""Create or update the initial admin user.

Usage:
    ADMIN_EMAIL=you@example.com ADMIN_PASSWORD=secret ADMIN_NAME="Your Name" \
        python -m scripts.seed_admin
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    email = os.environ["ADMIN_EMAIL"].lower()
    password = os.environ["ADMIN_PASSWORD"]
    name = os.environ.get("ADMIN_NAME", "Admin")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.hashed_password = hash_password(password)
            user.name = name
            print(f"Updated existing user {email}")
        else:
            user = User(
                email=email,
                name=name,
                hashed_password=hash_password(password),
                role="admin",
            )
            db.add(user)
            print(f"Created new user {email}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
