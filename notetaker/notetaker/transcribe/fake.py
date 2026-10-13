from __future__ import annotations

from notetaker.transcribe.base import ActionItem, MeetingNotes


class FakeAI:
    """Deterministic stand-in for tests and offline demos."""
    last_usage = (1200, 300)

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def check(self) -> None:
        if self.api_key == "bad-key":
            raise ValueError("bad key")

    def transcribe(self, audio: bytes, mime: str) -> str:
        return "hello from the fake transcriber"

    def summarise(self, transcript: str, participants: list[str], instructions: str | None) -> MeetingNotes:
        first = transcript.splitlines()[0] if transcript else ""
        return MeetingNotes(
            title="Call with " + (participants[0] if participants else "a client"),
            summary=f"{len(transcript.splitlines())} lines were said. It opened with: {first[:120]}",
            key_points=["Discussed the May issue"], action_items=[ActionItem(task="Send the proposal", owner=participants[-1] if participants else None)],
            next_step="Send the proposal", sentiment="positive",
        )
