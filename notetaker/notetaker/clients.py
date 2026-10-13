from __future__ import annotations

from sqlalchemy.orm import Session

from notetaker.models import Client
from notetaker.security import hash_key, new_api_key, new_secret


def create_client(db: Session, name: str, webhook_url: str | None = None, **extra) -> tuple[Client, str]:
    """Returns the client and its API key (shown once - only a hash is stored)."""
    key = new_api_key()
    c = Client(name=name, api_key_hash=hash_key(key), key_hint=key[:7], webhook_url=webhook_url, webhook_secret=new_secret(), **extra)
    db.add(c)
    db.flush()
    return c, key


def rotate_key(db: Session, c: Client) -> str:
    key = new_api_key()
    c.api_key_hash, c.key_hint = hash_key(key), key[:7]
    return key


def rotate_secret(c: Client) -> str:
    from notetaker.security import new_secret
    c.webhook_secret = new_secret()
    return c.webhook_secret
