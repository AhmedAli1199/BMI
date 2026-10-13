"""A pretend bot for tests and demos without a real call: it "records" a short sales conversation."""
from __future__ import annotations

import json
import uuid

from notetaker import states
from notetaker.bots.base import BotRequest, BotResult, BotUpdate, Utterance

DEMO = [
    ("Sarah Jones", "Thanks for making time. We're planning the spring campaign and wanted to hear about the May issue."),
    ("Matt Lee", "Of course. The May issue has the Caribbean feature, copy deadline is the 14th of March."),
    ("Sarah Jones", "We'd like a double page spread, and maybe the newsletter as well. What's the price for both?"),
    ("Matt Lee", "The spread is four thousand two hundred, and with the newsletter I can do five thousand for both."),
    ("Sarah Jones", "That sounds fair. I need sign-off from my director, I'll come back to you by Friday."),
    ("Matt Lee", "Great - I'll send the proposal today and pencil the spread so you don't lose the slot."),
]


class FakeBot:
    name = "fake"

    def __init__(self):
        self.created: list[BotRequest] = []
        self.cancelled: list[str] = []
        self.states: dict[str, BotUpdate] = {}   # what poll() reports, set by tests

    def create(self, req: BotRequest) -> str:
        self.created.append(req)
        return f"fake_{uuid.uuid4().hex[:10]}"

    def cancel(self, bot_id: str) -> None:
        self.cancelled.append(bot_id)

    def parse_webhook(self, body: bytes, headers: dict[str, str]) -> BotUpdate | None:
        p = json.loads(body)
        return BotUpdate(bot_id=p["bot_id"], status=p.get("status"), detail=p.get("detail"),
                         ready=p.get("status") == states.PROCESSING and p.get("ready", True), dedupe_key=p.get("key"))

    def poll(self, bot_id: str) -> BotUpdate | None:
        return self.states.get(bot_id)

    def fetch_result(self, bot_id: str) -> BotResult:
        t, out = 0, []
        for who, text in DEMO:
            out.append(Utterance(who, t, t + 6000, text))
            t += 7000
        return BotResult(transcript=out, participants=sorted({w for w, _ in DEMO}))
