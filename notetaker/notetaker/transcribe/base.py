"""The AI step. Swappable (strategy pattern): Gemini today, a self-hosted Whisper or another provider later."""
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    task: str
    owner: str | None = Field(None, description="Who said they'd do it, by name as spoken in the call")
    due: str | None = Field(None, description="When, in the words used (e.g. 'by Friday'), or null")


class MeetingNotes(BaseModel):
    title: str = Field(description="A short title for the call, 3-8 words")
    summary: str = Field(description="2-4 plain sentences: who met, what was discussed and where it was left")
    key_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    money_mentioned: list[str] = Field(default_factory=list, description="Prices, budgets or amounts discussed, with what they were for")
    dates_mentioned: list[str] = Field(default_factory=list, description="Deadlines, issue dates or follow-up dates discussed")
    next_step: str | None = Field(None, description="The single agreed next step, if any")
    sentiment: str = Field("neutral", description="One of: positive, neutral, negative - the other side's interest")


class AI(Protocol):
    def transcribe(self, audio: bytes, mime: str) -> str: ...
    def summarise(self, transcript: str, participants: list[str], instructions: str | None) -> MeetingNotes: ...
