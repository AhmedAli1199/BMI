"""Outgoing webhooks to client apps (outbox pattern): the message is saved with the change that caused
it, then a worker delivers it, retrying with growing gaps until the client answers 2xx.

Each delivery is signed so the client can trust it:
    X-Notetaker-Event:      meeting.completed
    X-Notetaker-Delivery:   <message id, the same on every retry - use it to ignore repeats>
    X-Notetaker-Timestamp:  <unix seconds>
    X-Notetaker-Signature:  sha256=<hex HMAC-SHA256 of "<timestamp>.<raw body>" with the client's webhook secret>
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetaker.config import settings
from notetaker.models import Client, OutboxMessage, now

log = logging.getLogger(__name__)


def enqueue(db: Session, client: Client, event: str, payload: dict, meeting_id: str | None = None) -> None:
    if not client.webhook_url:
        return
    from fastapi.encoders import jsonable_encoder
    db.add(OutboxMessage(client_id=client.id, meeting_id=meeting_id, event=event, payload=jsonable_encoder(payload)))


def signature(secret: str, timestamp: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def _backoff(attempts: int) -> timedelta:
    return timedelta(seconds=min(3600, 5 * 2 ** min(attempts, 10)))   # 10s, 20s, 40s ... capped at an hour


def deliver_due(db: Session, http: httpx.Client | None = None, limit: int = 20) -> int:
    """Send what's due. Uses SKIP LOCKED on Postgres so several workers never send the same message twice."""
    q = (select(OutboxMessage).where(OutboxMessage.status == "pending", OutboxMessage.next_attempt_at <= now())
         .order_by(OutboxMessage.next_attempt_at).limit(limit))
    if db.bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    msgs = db.scalars(q).all()
    http = http or httpx.Client(timeout=15)
    sent = 0
    for m in msgs:
        client = db.get(Client, m.client_id)
        if not client or not client.webhook_url:
            m.status, m.last_error = "dead", "No webhook address"
            continue
        body = json.dumps({"id": m.id, "event": m.event, "data": m.payload}, default=str).encode()
        ts = str(int(time.time()))
        m.attempts += 1
        try:
            r = http.post(client.webhook_url, content=body, headers={
                "Content-Type": "application/json", "X-Notetaker-Event": m.event, "X-Notetaker-Delivery": m.id,
                "X-Notetaker-Timestamp": ts, "X-Notetaker-Signature": signature(client.webhook_secret, ts, body)})
            if 200 <= r.status_code < 300:
                m.status, m.delivered_at, m.last_error = "delivered", now(), None
                sent += 1
                continue
            m.last_error = f"HTTP {r.status_code}"
        except httpx.HTTPError as e:
            m.last_error = type(e).__name__
        if m.attempts >= settings.webhook_max_attempts:
            m.status = "dead"
            log.error("Webhook %s to %s gave up after %s tries", m.id, client.name, m.attempts)
        else:
            m.next_attempt_at = now() + _backoff(m.attempts)
    return sent
