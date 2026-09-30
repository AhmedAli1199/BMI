"""Posts a short summary to an MS Teams "Incoming Webhook" connector -
currently only used for SALES-002's batch-confirm summary (added/updated/
skipped). Deliberately fire-and-forget: a failed or unconfigured webhook
never blocks or fails the write it's summarizing - this is a notification,
not a step in the automation's own contract.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.automations import runtime_settings

logger = logging.getLogger("app.automations.teams_notify")


def post_summary(db: Session, text: str) -> None:
    webhook_url = runtime_settings.get_str(db, "teams_webhook_url").strip()
    if not webhook_url:
        logger.info("teams_notify: no webhook configured (Automations Settings) - summary logged only: %s", text)
        return
    try:
        # Legacy Office 365 Connector card shape - the simplest payload a
        # Teams incoming webhook accepts, no adaptive-card schema needed
        # for a one-line summary.
        resp = httpx.post(webhook_url, json={"text": text}, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("teams_notify: failed to post summary (%s) - continuing anyway: %s", text, exc)
