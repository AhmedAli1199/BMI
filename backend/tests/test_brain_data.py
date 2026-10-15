"""The assistant's data side (phase 2): the search index over notes and history, who can see what, the figures
(matching the Sales Orders overview exactly), and the client at a glance."""
import hashlib
import math
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from tests.conftest import make_user
from tests.test_orders import w  # noqa: F401 - fixture

from app.brain import metrics, registry, tools  # noqa: F401 (registers the tools)
from app.brain import search as bs
from app.core.identity import Identity
from app.models import Company, Contact, HistoryEntry, Note, SalesEdition, SalesOrder, SalesOrderCredit


def fake_embed(texts, task):
    """Bag of words hashed into the vector - similar words, similar vectors; deterministic."""
    out = []
    for t in texts:
        v = [0.0] * bs.DIMS
        for word in t.lower().split():
            v[int(hashlib.md5(word.strip(".,:£").encode()).hexdigest(), 16) % bs.DIMS] += 1
        out.append(v if any(v) else [1.0] + [0.0] * (bs.DIMS - 1))
    return out


@pytest.fixture
def crm(w, monkeypatch):
    db = w["db"]
    bs.set_embedder(fake_embed)
    st = w["titles"]["selling-travel"]
    e25 = w["ed"]("selling-travel", "AprMay2025", date(2025, 4, 1))
    e26 = w["ed"]("selling-travel", "AprMay2026", date(2026, 4, 1))
    carib = Company(id=uuid.uuid4(), name="Caribbean Journal Ltd", source_db="onboard", source_act_id=str(uuid.uuid4()))
    other = Company(id=uuid.uuid4(), name="Alpine Tours", source_db="sellingtravel", source_act_id=str(uuid.uuid4()))
    db.add_all([carib, other])
    db.flush()
    sarah = Contact(id=uuid.uuid4(), full_name="Sarah Jones", company_id=carib.id, source_db="onboard", source_act_id=str(uuid.uuid4()))
    db.add(sarah)
    db.flush()
    writer = make_user(db, role="sales", name="Kirsty")
    db.add_all([
        Note(id=uuid.uuid4(), entity_type="company", entity_id=carib.id, body="Budget for 2027 is around £40,000 - they decide in November.",
             source_db="onboard", source_act_id=str(uuid.uuid4()), act_created_at=datetime(2026, 3, 12, tzinfo=timezone.utc)),
        Note(id=uuid.uuid4(), entity_type="company", entity_id=carib.id, body="Private: their marketing director is leaving in the spring.",
             is_private=True, created_by_user_id=writer.id, source_db="onboard", source_act_id=str(uuid.uuid4())),
        Note(id=uuid.uuid4(), entity_type="company", entity_id=other.id, body="Alpine budget is tight this year.", source_db="sellingtravel",
             source_act_id=str(uuid.uuid4())),
        HistoryEntry(id=uuid.uuid4(), entity_type="contact", entity_id=sarah.id, history_type="Call Completed",
                     subject="Rate for the full page", details="<p>Agreed <b>£2,450</b> for a full page in AprMay.</p>",
                     occurred_at=datetime(2025, 2, 1, tzinfo=timezone.utc), source_db="onboard", source_act_id=str(uuid.uuid4())),
    ])
    rep = w["reps"]["SP"]

    def item(ed, value, *, status="booked", invoice=None, client="Caribbean Journal", company=carib, size="Full page"):
        o = SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name=client, company_id=company.id if company else None, value_gbp=value,
                       status=status, extra={}, size=size, invoice_number=invoice, invoice_value_gbp=value if invoice else None,
                       booked_on=ed.edition_date, rep_id=rep.id)
        db.add(o)
        db.flush()
        db.add(SalesOrderCredit(id=uuid.uuid4(), order_id=o.id, rep_id=rep.id, amount_gbp=value))
        return o
    item(e25, 2450, invoice="INV-1001")
    item(e26, 2600, size="Double page")
    item(e26, 999, status="pencilled")
    item(e25, 1200, client="Alpine Tours", company=other, invoice="INV-1002")
    db.flush()
    yield {"db": db, "carib": carib, "other": other, "sarah": sarah, "writer": writer, "st": st, "e25": e25, "e26": e26}
    bs.set_embedder(None)


def test_index_picks_up_new_changed_and_deleted(crm):
    db = crm["db"]
    first = bs.index_pending(db)
    assert first["indexed"] == 4 and first["embedded"] == 4
    assert bs.index_pending(db)["indexed"] == 0                 # nothing changed: nothing to do
    head = db.execute(text("SELECT header, body FROM brain_chunks WHERE source_type = 'history'")).one()
    assert head.header == "History (Call Completed) · Caribbean Journal Ltd · Sarah Jones · 1 Feb 2025"
    assert "<b>" not in head.body and "£2,450" in head.body         # the HTML from Outlook is cleaned
    n = db.query(Note).filter(Note.body.like("Alpine%")).one()
    n.body = "Alpine budget is tight this year, maybe a newsletter only."
    db.flush()
    assert bs.index_pending(db)["indexed"] == 1                 # changed: re-indexed
    db.delete(n)
    db.flush()
    assert bs.index_pending(db)["removed"] == 1                 # deleted: gone from the index


def test_long_texts_are_split_with_overlap():
    parts = bs.pieces(("This is a sentence about the budget. " * 120).strip())
    assert len(parts) > 1 and all(len(p) <= bs.CHUNK_CHARS for p in parts)
    assert parts[0][-50:] in parts[1] or parts[1][:40] in parts[0]   # overlapping, so nothing falls between


def test_search_finds_by_words_and_meaning_and_keeps_to_access(crm):
    db = crm["db"]
    bs.index_pending(db)
    everyone = Identity(user_id=str(uuid.uuid4()), role="admin")
    hits = bs.search(db, everyone, "budget decided in November")
    assert hits and hits[0]["what"].startswith("Note · Caribbean Journal Ltd") and hits[0]["link"] == f"/companies/{crm['carib'].id}"
    assert any("£2,450" in h["text"] for h in bs.search(db, everyone, "£2,450 full page"))
    # private notes only for the person who wrote them
    assert not any("leaving" in h["text"] for h in bs.search(db, everyone, "marketing director leaving"))
    writer = Identity(user_id=str(crm["writer"].id), role="sales", access=[("onboard", None)])
    assert any("leaving" in h["text"] for h in bs.search(db, writer, "marketing director leaving"))
    # someone with only the Onboard database never sees Alpine (Selling Travel database)
    onboard_only = Identity(user_id=str(uuid.uuid4()), role="sales", access=[("onboard", None)])
    assert not any("Alpine" in h["text"] for h in bs.search(db, onboard_only, "budget"))
    assert any("Alpine" in h["text"] for h in bs.search(db, everyone, "budget"))
    # one client only, and dates
    only = bs.search(db, everyone, "budget", company_id=crm["other"].id)
    assert only and all("Alpine" in h["what"] for h in only)
    assert bs.search(db, everyone, "rate", since=datetime(2026, 1, 1, tzinfo=timezone.utc), kinds=["history"]) == []


def test_figures_match_the_sales_overview(crm, client, w):
    db = crm["db"]
    r = metrics.compute(db, measure="booked", year=2025, basis="calendar")
    assert r["total"] == 3650 and "pencilled" in r["definition"]
    ov = client.get("/api/sales/overview", params={"year": 2025, "basis": "calendar"}, headers=w["h"]).json()
    assert ov["booked_gbp"] == r["total"] and ov["invoiced_gbp"] == metrics.compute(db, measure="invoiced", year=2025, basis="calendar")["total"]
    by = metrics.compute(db, measure="booked", group_by="client", year=2025, basis="calendar")
    assert [(x["name"], x["value"]) for x in by["rows"]] == [("Caribbean Journal Ltd", 2450), ("Alpine Tours", 1200)]
    rep = metrics.compute(db, measure="booked", group_by="salesperson", year=2026, basis="calendar", compare_last_year=True)
    assert rep["total"] == 2600 and rep["last_year"]["total"] == 3650          # pencilled 999 left out
    assert metrics.compute(db, measure="awaiting_invoice", year=2026, basis="calendar")["total"] == 2600
    assert metrics.compute(db, measure="advertisers", year=2025, basis="calendar")["total"] == 2
    with pytest.raises(metrics.MetricError):
        metrics.compute(db, title="Nonsense Weekly")


class Ctx:
    def __init__(self, identity: Identity):
        self.state = registry.identity_state(identity)

        class S:
            id = str(uuid.uuid4())
        self.session = S()


def _tool(name, identity, monkeypatch, db, **kw):
    monkeypatch.setattr(registry, "session_factory", lambda: _Shared(db))
    return registry.TOOLS[name].adk_fn(tool_context=Ctx(identity), **kw)


class _Shared:
    def __init__(self, s):
        self._s = s

    def __getattr__(self, k):
        return getattr(self._s, k)

    def rollback(self):
        pass

    def close(self):
        pass


def test_client_at_a_glance(crm, monkeypatch):
    db = crm["db"]
    bs.index_pending(db)
    admin = make_user(db, role="admin", name="Ahmed")
    me = Identity(user_id=str(admin.id), role="admin")
    out = _tool("crm_client_snapshot", me, monkeypatch, db, client="Caribbean Journal Ltd")
    assert out["last_bought"]["value_gbp"] == 2600 and out["last_bought"]["what"] == "Double page"
    assert out["booked_by_year"] == {"2025": 2450, "2026": 2600} or out["booked_by_year"] == {"2024/25": 2450, "2025/26": 2600}
    assert out["people"][0]["name"] == "Sarah Jones" and out["people"][0]["link"].startswith("/contacts/")
    assert "Budget for 2027" in out["latest_notes"][0]["text"]
    vague = _tool("crm_client_snapshot", me, monkeypatch, db, client="a")   # matches both
    assert "which_one" in vague
    found = _tool("crm_find", me, monkeypatch, db, query="Sarah")
    assert found["people"][0]["company"] == "Caribbean Journal Ltd"
    # someone who can't see the Onboard database
    st_only = make_user(db, role="sales", name="Tom")
    them = Identity(user_id=str(st_only.id), role="sales", access=[("sellingtravel", None)])
    assert "error" in _tool("crm_client_snapshot", them, monkeypatch, db, client=str(crm["carib"].id))
    assert _tool("crm_find", them, monkeypatch, db, query="Caribbean")["companies"] == []


def test_switched_off_screens_stay_off(crm, monkeypatch):
    from app import ui_sections
    db = crm["db"]
    tom = make_user(db, role="sales", name="Tom")
    ui_sections.save(db, {"sales": ["sales_overview", "bookings", "editions"]})
    out = _tool("sales_metrics", Identity(user_id=str(tom.id), role="sales"), monkeypatch, db)
    assert "switched off" in out["error"]
    ok = _tool("sales_metrics", Identity(user_id=str(make_user(db, role="admin").id), role="admin"), monkeypatch, db, year=2025, basis="calendar")
    assert ok["total"] == 3650


def test_vectors_are_unit_length():
    v = bs.embed(["hello world"]) if bs._embedder else None
    bs.set_embedder(fake_embed)
    try:
        v = bs.embed(["hello world budget"])[0]
        assert abs(math.sqrt(sum(x * x for x in v)) - 1) < 1e-6
    finally:
        bs.set_embedder(None)
