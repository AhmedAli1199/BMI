"""The Brain (AI Hub chat + Ask AI): streaming answers, history replay that keeps the prompt cache warm,
tools running as the asking person, "Show me" kept only for real labels, ratings, "This didn't help"."""
import json
import re

import pytest
from google.genai import types
from tests.conftest import identity_headers, make_user
from tests.test_orders import w  # noqa: F401 - fixture

from app.brain import agent, knowledge, prompt, registry, runner
from app.models import BrainConversation, BrainMessage, Feedback


class ScriptedModel:
    """Stands in for Gemini: calls sales_order_explain when a booking number is mentioned, then answers."""

    def __new__(cls):
        from google.adk.models.base_llm import BaseLlm
        from google.adk.models.llm_response import LlmResponse

        class _M(BaseLlm):
            model: str = "scripted"
            requests: list = []

            async def generate_content_async(self, req, stream=False):
                self.requests.append(req)
                last = req.contents[-1]
                usage = types.GenerateContentResponseUsageMetadata(prompt_token_count=5000, cached_content_token_count=4000, candidates_token_count=40)
                if any(p.function_response for p in last.parts):
                    result = next(p.function_response.response for p in last.parts if p.function_response)
                    if "card" in result or "error" in result:
                        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=result.get("error") or "It's on the card for you to confirm.")]),
                                          partial=False, usage_metadata=usage)
                        return
                    why = (result.get("you") or {}).get("why_not") or "you can change it"
                    text = (f"Booking {result.get('number')} is {result.get('status')}. {why} Press **Change** [[show:Change]] "
                            "or **Launch rockets** [[show:Launch rockets]]. [[ask:When will it be invoiced?]] [[ask:Who checked it?]]")
                    yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text[:20])]), partial=True)
                    yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]), partial=False, usage_metadata=usage)
                    return
                said = " ".join(p.text or "" for p in last.parts)
                if "remind me" in said.split("\n")[0].lower():
                    from datetime import date, timedelta
                    yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
                        name="propose_reminder", args={"when": f"{date.today() + timedelta(days=1)} 10:30", "note": "Call Daniel"}))]),
                        usage_metadata=usage)
                    return
                m = re.search(r"booking (\d+)", said)
                if m:
                    yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
                        name="sales_order_explain", args={"booking": m.group(1)}))]), usage_metadata=usage)
                    return
                yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="Press **New booking** to start.")]),
                                  partial=False, usage_metadata=usage)

        return _M()


class _Shared:
    """The test's own session for the tools (they normally open their own); closing it is a no-op."""

    def __init__(self, s):
        self._s = s

    def __getattr__(self, k):
        return getattr(self._s, k)

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def model(db_session, monkeypatch):
    from app.api.routes import brain as routes
    m = ScriptedModel()
    m.requests.clear()
    agent.set_model(m)
    monkeypatch.setattr(registry, "session_factory", lambda: _Shared(db_session))
    monkeypatch.setattr(routes, "_log_usage", lambda trace: None)
    yield m
    agent.set_model(None)


def events(resp) -> list[tuple[str, dict]]:
    """The AG-UI stream as (type, event) pairs."""
    out = []
    for block in resp.text.strip().split("\n\n"):
        data = json.loads(re.search(r"^data: (.*)$", block, re.M).group(1))
        out.append((data["type"], data))
    return out


def test_guides_load_and_match_pages():
    gs = knowledge.guides()
    assert len(gs) >= 8 and all(g.title and g.summary and g.screens for g in gs)
    assert knowledge.guides_for_path("/sales/deals/1b2c3d4e-0000-0000-0000-000000000000")[0].id == "sales-orders/booking-page"
    assert knowledge.guides_for_path("/sales/deals/new")[0].id == "sales-orders/booking-form"
    assert knowledge.search("unlock booking accounts")
    text = prompt.static_instruction()
    assert "sales-orders/invoicing" in text and "<guide id=" not in text      # only the list; guides come on demand
    g = runner.page_guide("/sales/deals/1b2c3d4e-0000-0000-0000-000000000000", set(), [])
    assert g.startswith('\n\n<guide id="sales-orders/booking-page"')
    assert runner.page_guide("/sales/deals/x", set(), [("user", "q " + g)]) == ""          # already in this conversation
    assert runner.page_guide("/sales/deals/x", {"orders"}, []) == ""                       # can't open that page
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", prompt.RULES)   # nothing that changes day to day in the fixed part


def test_chat_streams_explains_the_booking_and_keeps_the_cache_warm(w, client, model):
    db, h = w["db"], w["h"]
    from datetime import date, timedelta
    ed = w["ed"]("selling-travel", "Dec issue", date.today() + timedelta(days=40))
    d = client.post("/api/sales/deals", json={"client_name": "Visit Malta", "rep_id": str(w["reps"]["SP"].id), "status": "confirmed",
                                              "lines": [{"key": "a", "title_id": str(w["titles"]["selling-travel"].id), "description": "Full page",
                                                         "unit_price": 2000, "placements": [{"edition_id": str(ed.id)}]}]}, headers=h).json()
    db.commit()
    ctx = {"page_path": f"/sales/deals/{d['id']}", "page_title": f"Booking {d['number']}", "record": {"kind": "booking", "id": d["id"]},
           "elements": [{"label": "Change", "role": "button", "heading": "Booking", "source": ["components/deals/deal-actions.tsx:10"]}]}
    r = client.post("/api/brain/chat", json={"message": f"Why can't I edit booking {d['number']}?", "context": ctx}, headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = events(r)
    kinds = [k for k, _ in ev]
    assert kinds[0] == "RUN_STARTED" and "STEP_STARTED" in kinds and "TEXT_MESSAGE_CONTENT" in kinds and kinds[-1] == "RUN_FINISHED"
    assert dict(ev)["STEP_STARTED"]["stepName"] == "Looking at the booking"
    assert kinds.index("STEP_FINISHED") < kinds.index("TEXT_MESSAGE_START") < kinds.index("TEXT_MESSAGE_END")
    assert ev[-1][1]["outcome"]["type"] == "success"
    done = ev[-1][1]["result"]["message"]
    assert done["text"].startswith(f"Booking {d['number']} is confirmed")
    assert "[[ask:" not in done["text"] and done["context"]["suggestions"] == ["When will it be invoiced?", "Who checked it?"]
    conv_id = ev[0][1]["threadId"]
    a = db.query(BrainMessage).filter_by(role="assistant").one()
    assert a.trace["steps"][0]["tool"] == "sales_order_explain" and a.trace["steps"][0]["ok"]
    assert a.trace["cached_tokens"] == 8000 and a.trace["llm_calls"] == 2
    q = db.query(BrainMessage).filter_by(role="user").one()
    assert q.text.startswith("Why can't I edit") and "<context>" in q.model_text and f"/sales/deals/{d['id']}" in q.model_text

    # second turn: same fixed instructions, and the first question replayed exactly as the model first saw it
    model.requests.clear()
    r2 = client.post("/api/brain/chat", json={"conversation_id": conv_id, "message": "Thanks! How do I start a new one?"}, headers=h)
    assert events(r2)[-1][1]["result"]["message"]["text"] == "Press **New booking** to start."
    req = model.requests[0]
    first_turn = req.contents[0].parts[0].text
    assert first_turn == q.model_text                     # replayed byte for byte
    assert all(not p.function_response for c in req.contents for p in c.parts)   # old tool results dropped
    assert req.config.system_instruction.startswith(prompt.RULES[:200])
    convs = client.get("/api/brain/conversations", headers=h).json()["conversations"]
    assert convs[0]["id"] == conv_id and convs[0]["title"].startswith("Why can't I edit booking")
    full = client.get(f"/api/brain/conversations/{conv_id}", headers=h).json()
    assert [m["role"] for m in full["messages"]] == ["user", "assistant", "user", "assistant"]


def test_show_me_only_for_labels_on_that_page(monkeypatch):
    monkeypatch.setattr(knowledge, "labels_for_path", lambda p: {"change", "unlock"})
    text, extras = runner.finish("Press **Change** [[show:Change]] or **Fly** [[show:Fly]]. [[ask:What next?]]", "/sales/deals/x")
    assert "[[show:Change]]" in text and "[[show:Fly]]" not in text and extras["show"] == ["Change"]
    assert extras["suggestions"] == ["What next?"]


def test_tools_run_as_the_person_and_never_raise(w, model):
    from app.core.identity import Identity
    # the registry wrapper turns a bad booking number into a plain sentence for the model
    tool = registry.TOOLS["sales_order_explain"]

    class Ctx:
        state = registry.identity_state(Identity(user_id=w["h"]["X-BMI-User-Id"], role="admin"))

        class session:
            id = "s1"
    out = tool.adk_fn(booking="999999", tool_context=Ctx())
    assert "There's no booking" in out["error"]
    assert registry.TRACES.pop("s1")[0]["ok"] is False


def test_rating_and_this_didnt_help_become_feedback(w, client, model):
    h = w["h"]
    ev = events(client.post("/api/brain/chat", json={"message": "How do I make a booking?", "context": {"page_path": "/sales/deals"}}, headers=h))
    mid = ev[-1][1]["result"]["message"]["id"]
    assert client.post(f"/api/brain/messages/{mid}/rating", json={"rating": 1}, headers=h).json()["rating"] == 1
    r = client.post(f"/api/brain/messages/{mid}/feedback", json={"note": "I meant a booking form"}, headers=h).json()
    f = w["db"].get(Feedback, __import__("uuid").UUID(r["feedback_id"]))
    assert f.kind == "confusing" and "How do I make a booking?" in f.message and f.page_path == "/sales/deals"
    assert client.post(f"/api/brain/messages/{mid}/feedback", json={}, headers=h).json()["number"] == r["number"]   # once
    other = identity_headers(make_user(w["db"], role="sales", name="Tom"))
    w["db"].commit()
    assert client.post(f"/api/brain/messages/{mid}/rating", json={"rating": -1}, headers=other).status_code == 404


def test_not_switched_on_says_so(w, client, monkeypatch):
    from app.core.config import settings
    agent.set_model(None)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    ev = events(client.post("/api/brain/chat", json={"message": "hello"}, headers=w["h"]))
    assert ev[-1][0] == "RUN_ERROR" and ev[-1][1]["message"] == runner.NOT_ON
    assert w["db"].query(BrainMessage).filter_by(role="assistant").one().context.get("error") is True


def test_suggestions_come_from_the_guide(w, client):
    r = client.get("/api/brain/suggestions", params={"page": "/sales/deals/new"}, headers=w["h"]).json()
    assert r["guide"] and len(r["questions"]) >= 2 and all(q.endswith("?") for q in r["questions"])


def test_eval_questions_are_well_formed():
    import json
    from pathlib import Path

    from app.brain.evals.__main__ import check
    qs = json.loads((Path(knowledge.HELP_DIR).parent / "evals" / "questions.json").read_text())
    assert len(qs) >= 10 and all(q["q"].endswith("?") and q["page"].startswith("/") and (q.get("all") or q.get("any")) for q in qs)
    assert check("Press **Request a change**.", qs[0]) == []
    assert check("It's a deal.", qs[0])     # wrong word and missing button


def test_actions_wait_for_confirm_and_run_as_the_person(w, client, model):
    """Phase 4: the Brain only proposes - a card (AG-UI tool call + interrupt); Confirm runs it, Cancel doesn't."""
    from app.models import BrainAction, Reminder
    db, h = w["db"], w["h"]
    ev = events(client.post("/api/brain/chat", json={"message": "Remind me tomorrow to call Daniel"}, headers=h))
    kinds = [k for k, _ in ev]
    assert "TOOL_CALL_START" in kinds and kinds[-1] == "RUN_FINISHED"
    start = dict(ev)["TOOL_CALL_START"]
    assert start["toolCallName"] == "confirm_action"
    card = json.loads(dict(ev)["TOOL_CALL_ARGS"]["delta"])
    assert card["title"] == "Set a reminder" and card["status"] == "pending" and ["Note", "Call Daniel"] in card["lines"]
    outcome = ev[-1][1]["outcome"]
    assert outcome["type"] == "interrupt" and outcome["interrupts"][0]["id"] == card["id"] == start["toolCallId"]
    assert db.query(Reminder).count() == 0                     # nothing done yet
    conv = ev[0][1]["threadId"]
    answer = db.query(BrainMessage).filter_by(role="assistant").one()
    assert answer.context["actions"][0]["id"] == card["id"]

    # someone else can't answer it
    other = identity_headers(make_user(db, role="sales", name="Tom"))
    db.commit()
    r = client.post("/api/brain/chat", json={"conversation_id": conv, "resume": [{"interruptId": card["id"], "status": "resolved"}]}, headers=other)
    assert r.status_code == 404 and db.query(Reminder).count() == 0

    ev = events(client.post("/api/brain/chat", json={"conversation_id": conv, "resume": [{"interruptId": card["id"], "status": "resolved"}]}, headers=h))
    assert [k for k, _ in ev][:2] == ["RUN_STARTED", "TOOL_CALL_RESULT"] and ev[-1][0] == "RUN_FINISHED"
    assert json.loads(ev[1][1]["content"])["status"] == "done"
    assert ev[-1][1]["result"]["message"]["text"].startswith("Reminder set for")
    rem = db.query(Reminder).one()
    assert rem.note == "Call Daniel" and rem.status == "open"
    db.refresh(answer)
    assert answer.context["actions"][0]["status"] == "done"   # a reopened chat shows how the card ended
    # a second click does nothing twice
    client.post("/api/brain/chat", json={"conversation_id": conv, "resume": [{"interruptId": card["id"], "status": "resolved"}]}, headers=h)
    assert db.query(Reminder).count() == 1

    # Cancel leaves everything as it was; a new question cancels cards left waiting
    ev = events(client.post("/api/brain/chat", json={"conversation_id": conv, "message": "Remind me tomorrow to call Daniel"}, headers=h))
    c2 = json.loads(dict(ev)["TOOL_CALL_ARGS"]["delta"])["id"]
    events(client.post("/api/brain/chat", json={"conversation_id": conv, "resume": [{"interruptId": c2, "status": "cancelled"}]}, headers=h))
    assert db.query(Reminder).count() == 1 and db.get(BrainAction, __import__("uuid").UUID(c2)).status == "cancelled"
    ev = events(client.post("/api/brain/chat", json={"conversation_id": conv, "message": "Remind me tomorrow to call Daniel"}, headers=h))
    c3 = json.loads(dict(ev)["TOOL_CALL_ARGS"]["delta"])["id"]
    client.post("/api/brain/chat", json={"conversation_id": conv, "message": "Never mind, thanks"}, headers=h)
    assert db.get(BrainAction, __import__("uuid").UUID(c3)).status == "cancelled"
