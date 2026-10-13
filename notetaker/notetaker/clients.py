from __future__ import annotations

from sqlalchemy.orm import Session

from notetaker.models import Client
from notetaker.security import hash_key, new_api_key, new_secret


def create_client(db: Session, name: str, webhook_url: str | None = None, **extra) -> tuple[Client, str]:
    """Returns the client and its API key (shown once - only a hash is stored)."""
    key = new_api_key()
    c = Client(name=name, api_key_hash=hash_key(key), webhook_url=webhook_url, webhook_secret=new_secret(), **extra)
    db.add(c)
    db.flush()
    return c, key
