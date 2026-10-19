"""Each new piece of feedback posted to a Discord channel (optional: DISCORD_FEEDBACK_WEBHOOK_URL - the channel's
webhook address, kept in the server's settings, never in the code). One message per piece of feedback: what kind,
what they said, which page, who sent it, a link to it in BMI Brain (and to its GitHub issue when that's on), and the
first screenshot. A failure is logged and never gets in the way of the feedback itself."""
from __future__ import annotations

import json
import logging

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.feedback.text import KIND_LABEL
from app.models import Feedback, FeedbackImage

logger = logging.getLogger("app.feedback.discord")

# Discord colours (decimal RGB) per kind: red, amber, blue, purple
COLOURS = {"broken": 0xC0392B, "confusing": 0xD4A017, "idea": 0x0099E5, "looks_wrong": 0x8A3B5C}
ROLE_WORDS = {"admin": "Administrator", "data_manager": "Data Manager", "sales": "Sales"}
MAX_IMAGE = 8 * 1024 * 1024   # Discord's limit for a webhook upload without a boosted server


def enabled() -> bool:
    url = settings.discord_feedback_webhook_url.strip()
    return url.startswith("https://discord.com/api/webhooks/") or url.startswith("https://discordapp.com/api/webhooks/")


def message(f: Feedback, has_image: bool) -> dict:
    link = f"{settings.app_base_url.rstrip('/')}/feedback?open={f.id}"
    page = f.page_title or f.page_path
    fields = [
        {"name": "Page", "value": f"[{page[:200]}]({settings.app_base_url.rstrip('/')}{f.page_path})" if f.page_path else page[:200], "inline": True},
        {"name": "From", "value": f"{f.user_name or 'Someone'}" + (f" ({ROLE_WORDS.get(f.user_role or '', f.user_role)})" if f.user_role else ""), "inline": True},
    ]
    if f.elements:
        el = f.elements[0]
        what = (el.get("label") or el.get("text") or "").strip()
        if what:
            fields.append({"name": "Pointed at", "value": what[:200], "inline": False})
    if f.github_url:
        fields.append({"name": "GitHub", "value": f"[Issue #{f.github_number}]({f.github_url})", "inline": True})
    embed = {
        "title": f"#{f.number} · {KIND_LABEL.get(f.kind, f.kind)}"[:256],
        "url": link,
        "description": (f.message or "(no message - see the screenshot)")[:3500],
        "color": COLOURS.get(f.kind, 0x132C6B),
        "fields": fields,
        "footer": {"text": "BMI Brain feedback"},
        "timestamp": f.created_at.isoformat() if f.created_at else None,
    }
    if has_image:
        embed["image"] = {"url": "attachment://screenshot.png"}
    # No pings: a message can't @everyone or @someone by accident, whatever the feedback says.
    return {"username": "BMI Brain feedback", "embeds": [embed], "allowed_mentions": {"parse": []}}


def _client() -> httpx.Client:
    return httpx.Client(timeout=20)


def post(db: Session, f: Feedback) -> bool:
    """Sends the message. True if Discord took it."""
    if not enabled():
        return False
    img = db.query(FeedbackImage).filter_by(feedback_id=f.id).order_by(FeedbackImage.position).first()
    has_image = bool(img and img.data and len(img.data) <= MAX_IMAGE)
    payload = message(f, has_image)
    try:
        with _client() as c:
            if has_image:
                r = c.post(settings.discord_feedback_webhook_url.strip(), data={"payload_json": json.dumps(payload)},
                           files={"files[0]": ("screenshot.png", img.data, img.content_type or "image/png")})
            else:
                r = c.post(settings.discord_feedback_webhook_url.strip(), json=payload)
        if r.status_code >= 300:
            logger.warning("Discord didn't take feedback #%s: %s %s", f.number, r.status_code, r.text[:300])
            return False
        return True
    except httpx.HTTPError:
        logger.warning("Couldn't reach Discord for feedback #%s", f.number, exc_info=True)
        return False
