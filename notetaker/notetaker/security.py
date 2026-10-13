from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def new_api_key() -> str:
    return "nt_" + secrets.token_urlsafe(32)


def new_secret() -> str:
    return "whsec_" + secrets.token_urlsafe(32)


def same(a: str, b: str) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(a, b)


def _fernet():
    import base64

    from cryptography.fernet import Fernet

    from notetaker.config import settings
    key = settings.encryption_key or base64.urlsafe_b64encode(hashlib.sha256(("nt-enc:" + settings.internal_token).encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
