"""Cheap, free (no LLM call) text/sender signals shared across the mailbox
scans - the "obviously not relevant, don't even spend an LLM call on it"
first pass. Kept in one place so a pattern only needs updating once; see
inbound_capture.py and bounce_handling.py for where these are used.
"""
from __future__ import annotations

import re

# System/automated senders - never a real person writing in, so never a
# genuine inbound lead or a genuine out-of-office reply from someone.
_AUTOMATED_SENDER_PREFIXES = (
    "noreply", "no-reply", "donotreply", "do-not-reply", "notifications",
    "notification", "alerts", "alert", "calendar", "auto-reply", "autoreply",
    "automated", "mailer-daemon", "postmaster",
)

_REPLY_SUBJECT_RE = re.compile(r"^\s*(re|fw|fwd|aw)\s*:", re.IGNORECASE)

_UNSUBSCRIBE_TEXT_RE = re.compile(r"\bunsubscribe\b", re.IGNORECASE)

# Someone asking to be REMOVED - the opposite of a lead, and the opposite
# of a marketing email that merely contains an unsubscribe footer link
# (see is_marketing_unsubscribe_text below, which this deliberately
# doesn't overlap with: a marketing footer says "unsubscribe here", a
# removal request says "please unsubscribe/remove/delete ME/THIS/THESE").
_UNSUBSCRIBE_REQUEST_RE = re.compile(
    r"(unsubscribe|remove|delete)\s+(me|us|the following|these names|my|our)\b"
    r"|(remove|delete|unsubscribe).{0,40}(from your (mailing )?list|from your database|from your records)",
    re.IGNORECASE,
)


def is_automated_sender(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    local = email.split("@", 1)[0].strip().lower()
    return any(local == p or local.startswith(p) for p in _AUTOMATED_SENDER_PREFIXES)


def is_reply_subject(subject: str | None) -> bool:
    """A "RE:"/"FW:"/"FWD:" (or German "AW:") prefix - a reply/forward in
    an existing thread, not a first contact. Cheap and imperfect (someone
    could reply to their own cold-pitch and drop the prefix, or an email
    client could localize it differently) but it's the single highest-
    leverage signal against "reply from an existing relationship treated
    as a brand-new lead" - see docs/automation-tuning-baseline.md."""
    return bool(_REPLY_SUBJECT_RE.match(subject or ""))


def contains_unsubscribe_text(body: str) -> bool:
    """Catches marketing sends whose unsubscribe link is only in the
    visible footer, not the List-Unsubscribe header."""
    return bool(_UNSUBSCRIBE_TEXT_RE.search(body or ""))


def looks_like_unsubscribe_request(body: str) -> bool:
    """Someone ASKING to be removed, not a marketing email's own footer -
    see the regex's own comment for how these are told apart. A cheap,
    imperfect heuristic; the LLM classification tier (see
    inbound_capture.py) still catches whatever this misses."""
    return bool(_UNSUBSCRIBE_REQUEST_RE.search(body or ""))
