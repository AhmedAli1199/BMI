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
