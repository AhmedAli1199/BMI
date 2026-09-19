"""Turns one raw Microsoft Graph message object (see graph_client.py's
_MESSAGE_SELECT for exactly which fields we ask for) into the handful of
plain values the bounce/OOO scan actually needs, plus cheap, free
(no-AI-call) heuristics for "does this look like a bounce" and "does this
look like an out-of-office/auto-reply" - the two questions that decide
whether a message needs an LLM call at all (see bounce_handling.py).

Kept separate from bounce_handling.py specifically so this - the "the API
response is complex, extract what we need" piece - is independently
readable and testable against a handful of saved sample payloads, without
needing a live Graph connection or the scan's DB/review-queue plumbing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ParsedMessage:
    message_id: str  # Graph's internal id - stable, used for the review-queue dedupe key
    internet_message_id: str | None  # the RFC 5322 Message-ID header, if present
    from_address: str | None
    from_name: str | None
    subject: str
    received_at: datetime
    body_text: str  # plain text, truncated to a sane length for prompts/storage
    headers: dict[str, str] = field(default_factory=dict)  # lower-cased header names -> value
    failed_recipients: list[str] = field(default_factory=list)  # addresses a bounce NDR says it couldn't deliver to


_MAX_BODY_CHARS = 4000

# Non-delivery report subjects are one of the few things mail servers write
# consistently across providers/languages-in-English-orgs - matching these
# up front avoids spending an LLM call on the large majority of bounces,
# which are entirely mechanical.
_NDR_SUBJECT_RE = re.compile(
    r"^(undeliverable|delivery status notification|delivery has failed|mail delivery failed|"
    r"returned mail|failure notice|non-delivery report|message undeliverable)",
    re.IGNORECASE,
)

# RFC 3834 / common autoresponder markers - "Auto-Submitted" is the
# standards header; the rest are what Exchange/Outlook/Gmail actually send
# in practice for out-of-office replies.
_OOO_SUBJECT_RE = re.compile(
    r"^(automatic reply|auto[- ]?reply|out of office|away from|on leave)",
    re.IGNORECASE,
)

# Pulls email addresses out of an NDR body's "failed recipients" section -
# deliberately a plain email regex rather than trying to parse every mail
# server's own NDR body format (they all differ), since we only need the
# addresses, not the full diagnostic text.
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def _plain_body(raw: dict) -> str:
    body = raw.get("body") or {}
    content = body.get("content") or raw.get("bodyPreview") or ""
    if (body.get("contentType") or "").lower() == "html":
        # Graph is asked for text via the Prefer header (see graph_client.py),
        # but falls back to HTML for a handful of message types regardless -
        # strip tags crudely rather than pulling in a full HTML parser for
        # what only needs to be "readable enough for a classifier."
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()
    return content[:_MAX_BODY_CHARS]


def _headers(raw: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in raw.get("internetMessageHeaders") or []:
        name = (h.get("name") or "").strip().lower()
        if name:
            out[name] = h.get("value") or ""
    return out


def parse_message(raw: dict) -> ParsedMessage:
    """Never raises on a malformed/partial message - Graph payloads vary
    message to message (a calendar invite, an NDR, and a plain human email
    don't carry the same optional fields), and one oddly-shaped message
    should degrade to "fields we couldn't find are None/empty", never
    abort the whole scan batch."""
    sender = (raw.get("from") or {}).get("emailAddress") or {}
    body_text = _plain_body(raw)
    headers = _headers(raw)

    failed_recipients = []
    if _NDR_SUBJECT_RE.match(raw.get("subject") or ""):
        failed_recipients = list(dict.fromkeys(_EMAIL_RE.findall(body_text)))

    received_raw = raw.get("receivedDateTime")
    received_at = datetime.fromisoformat(received_raw.replace("Z", "+00:00")) if received_raw else datetime.now()

    return ParsedMessage(
        message_id=raw["id"],
        internet_message_id=raw.get("internetMessageId"),
        from_address=(sender.get("address") or "").strip().lower() or None,
        from_name=sender.get("name"),
        subject=raw.get("subject") or "(no subject)",
        received_at=received_at,
        body_text=body_text,
        headers=headers,
        failed_recipients=failed_recipients,
    )


def looks_like_bounce(msg: ParsedMessage) -> bool:
    """Cheap, deterministic pre-filter - no LLM call needed to notice a
    subject line every mail server on earth spells almost the same way."""
    if _NDR_SUBJECT_RE.match(msg.subject):
        return True
    # Exchange/most MTAs mark automated delivery reports this way even
    # when the subject has been localized to something the regex above
    # won't catch.
    content_type = msg.headers.get("content-type", "")
    return "report-type=delivery-status" in content_type.lower()


def looks_like_ooo(msg: ParsedMessage) -> bool:
    """Same idea for out-of-office/auto-reply detection - RFC 3834's
    Auto-Submitted header is the reliable signal when present; the subject
    regex covers the common case where a sender's mail system doesn't set
    it (a lot of consumer/Google Workspace auto-replies skip it)."""
    auto_submitted = msg.headers.get("auto-submitted", "").lower()
    if auto_submitted and auto_submitted != "no":
        return True
    return bool(_OOO_SUBJECT_RE.match(msg.subject))
