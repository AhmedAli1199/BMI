"""The life of a meeting job, as a small state machine.

    scheduled -> joining -> waiting_room -> recording -> processing -> completed
                    \\            \\              \\
                     `-> not_admitted / failed / cancelled (final)

Only moves listed in ALLOWED are accepted, so a late or repeated webhook can never send a finished
meeting backwards.
"""
from __future__ import annotations

SCHEDULED, JOINING, WAITING_ROOM, RECORDING, PROCESSING = "scheduled", "joining", "waiting_room", "recording", "processing"
COMPLETED, FAILED, NOT_ADMITTED, CANCELLED = "completed", "failed", "not_admitted", "cancelled"

FINAL = {COMPLETED, FAILED, NOT_ADMITTED, CANCELLED}
ACTIVE = {JOINING, WAITING_ROOM, RECORDING}
ORDER = [SCHEDULED, JOINING, WAITING_ROOM, RECORDING, PROCESSING, COMPLETED]

ALLOWED: dict[str, set[str]] = {
    SCHEDULED: {JOINING, WAITING_ROOM, RECORDING, PROCESSING, FAILED, NOT_ADMITTED, CANCELLED},
    JOINING: {WAITING_ROOM, RECORDING, PROCESSING, FAILED, NOT_ADMITTED, CANCELLED},
    WAITING_ROOM: {JOINING, RECORDING, PROCESSING, FAILED, NOT_ADMITTED, CANCELLED},
    RECORDING: {PROCESSING, FAILED, CANCELLED},
    PROCESSING: {COMPLETED, FAILED},
}

LABELS = {
    SCHEDULED: "Scheduled", JOINING: "Joining the call", WAITING_ROOM: "Waiting to be let in", RECORDING: "Recording",
    PROCESSING: "Writing up the notes", COMPLETED: "Notes ready", FAILED: "Couldn't record", NOT_ADMITTED: "Not let into the call",
    CANCELLED: "Cancelled",
}


def can_move(current: str, new: str) -> bool:
    return new != current and new in ALLOWED.get(current, set())
