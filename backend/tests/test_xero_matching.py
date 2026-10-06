"""Matching Xero invoices to bookings: clear matches applied on their own,
everything else waiting in the review queue with the reasons."""
import uuid
from datetime import date, timedelta

import pytest
from tests.conftest import identity_headers, make_user
from tests.test_sales_orders import _order, sor  # noqa: F401 - fixture + helper reuse

from app.automations import xero_matching as xm
from app.automations.state import get_state
from app.models import FieldChange, ReviewQueueItem, SalesOrder, XeroInvoice
from app.sales import invoice_match as im
from app.sales.invoice_numbers import canonical, canonical_sql, find_invoice

TODAY = date.today()


def invoice(db, number, contact, net, *, ref="", lines="", cur="GBP", rate=None, issued=None, status="PAID", paid=True, due=None):
    inv = XeroInvoice(id=uuid.uuid4(), xero_id=str(uuid.uuid4()), invoice_number=number, number_key=canonical(number),
                      contact_name=contact, reference=ref, line_text=lines, status=status, currency=cur, currency_rate=rate,
                      issued_on=issued or TODAY - timedelta(days=5), due_on=due or TODAY + timedelta(days=25),
                      sub_total=net, total_tax=0 if cur != "GBP" else net * 0.2, total=net * (1 if cur != "GBP" else 1.2),
                      amount_paid=net if paid else 0, amount_due=0 if paid else net)
    db.add(inv)
    db.flush()
    return inv


def booking(db, sor, client, value, *, edition="this", rep="SP", booked=None, **kw):
    return _order(db, sor[edition], client, value, sor["reps"][rep], booked_on=booked or TODAY - timedelta(days=20), **kw)


def run(db, **kw):
    return xm.run_matching(db, auto_link=kw.pop("auto_link", True), max_new=kw.pop("max_new", 50), **kw)


def items(db, status=None):
    q = db.query(ReviewQueueItem).filter_by(kind=xm.KIND)
    return q.filter_by(status=status).all() if status else q.all()


def test_clear_match_is_linked_on_its_own_and_recorded(db_session, sor):
    b = booking(db_session, sor, "Foodcase", 1000)
    inv = invoice(db_session, "56300", "Foodcase Ltd", 1000, ref="OBH 105")
    assert run(db_session)["auto"] == 1
    db_session.refresh(b)
    assert (b.invoice_number, b.xero_invoice_id, b.xero_link_source) == ("56300", inv.id, "auto")
    assert float(b.invoice_value_gbp) == 1000 and b.invoiced_on == inv.issued_on
    history = {c.field: c.new_value for c in db_session.query(FieldChange).filter_by(entity_id=b.id)}
    assert "automatically" in history["xero_link"] and history["invoice_number"] == "56300"
    assert items(db_session) == []   # an automatic link is not put in the review queue - the booking's history says it
    assert run(db_session) == {"typed_links": 0, "no_fit": 0}  # nothing new the second time


def test_turning_auto_link_off_sends_even_clear_matches_to_review(db_session, sor):
    b = booking(db_session, sor, "Foodcase", 1000)
    invoice(db_session, "56300", "Foodcase Ltd", 1000, ref="OBH 105")
    assert run(db_session, auto_link=False)["review"] == 1
    db_session.refresh(b)
    assert b.invoice_number is None
    assert "switched off" in items(db_session, "pending")[0].payload["invoice_match"]["reason"]


def test_timing_alone_can_settle_which_booking_it_is(db_session, sor):
    old = booking(db_session, sor, "Delta", 650, edition="last", booked=TODAY - timedelta(days=300))
    new = booking(db_session, sor, "Delta", 650, edition="this", booked=TODAY - timedelta(days=20))
    invoice(db_session, "56290", "Delta Air Lines", 650)
    assert run(db_session)["auto"] == 1
    db_session.refresh(old), db_session.refresh(new)
    assert (old.invoice_number, new.invoice_number) == (None, "56290")


def test_two_bookings_that_fit_go_to_review_and_a_person_picks(client, db_session, sor):
    a = booking(db_session, sor, "Delta", 650, edition="this")
    b = booking(db_session, sor, "Delta", 650, edition="last", booked=TODAY - timedelta(days=12))
    inv = invoice(db_session, "56301", "Delta Air Lines", 650)  # says nothing about the issue
    assert run(db_session) == {"typed_links": 0, "no_fit": 0, "review": 1}
    item = items(db_session, "pending")[0]
    match = item.payload["invoice_match"]
    assert len(match["candidates"]) == 2 and "equally well" in match["reason"]
    assert match["invoice"]["number"] == "56301" and match["invoice"]["url"].endswith(inv.xero_id)
    first = match["candidates"][0]
    assert {r["key"] for r in first["reasons"]} >= {"client", "amount", "issue"} and first["bookings"][0]["edition"]

    rep = make_user(db_session, role="sales")
    db_session.commit()
    h = identity_headers(rep, access=[("onboard", None)])
    keys = [c["key"] for c in match["candidates"]]
    # picking nothing is refused, a bulk apply can't skip the choice either
    r = client.post(f"/api/review-queue/{item.id}/actions/link", headers=h, json={})
    assert r.status_code == 400 and "Pick which booking" in r.json()["detail"]
    assert client.post(f"/api/review-queue/{item.id}/actions/link", headers=h, json={"chosen_entity_id": str(uuid.uuid4())}).status_code == 400
    r = client.post(f"/api/review-queue/{item.id}/actions/link", headers=h, json={"chosen_entity_id": keys[1]})
    assert r.status_code == 200, r.text
    db_session.expire_all()
    linked = [o for o in (a, b) if db_session.get(SalesOrder, o.id).invoice_number == "56301"]
    assert len(linked) == 1
    row = db_session.get(SalesOrder, linked[0].id)
    assert row.xero_link_source == "confirmed" and row.xero_invoice_id == inv.id
    done = db_session.get(ReviewQueueItem, item.id)
    assert done.status == "approved" and done.payload["linked"]["auto"] is False


def test_agency_invoice_waits_with_an_explanation_then_the_name_is_learned(client, db_session, sor):
    booking(db_session, sor, "Visit St Pete Clearwater", 1990)
    invoice(db_session, "56302", "Rooster", 1990)
    assert run(db_session)["review"] == 1
    item = items(db_session, "pending")[0]
    assert "different" in item.payload["invoice_match"]["reason"] or "isn't the booking's client" in item.payload["invoice_match"]["reason"]
    reasons = {r["key"]: r for r in item.payload["invoice_match"]["candidates"][0]["reasons"]}
    assert reasons["client"]["ok"] is False and reasons["amount"]["ok"] is True

    admin = make_user(db_session, role="admin")
    db_session.commit()
    assert client.post(f"/api/review-queue/{item.id}/actions/link", headers=identity_headers(admin), json={"chosen_entity_id": item.payload["invoice_match"]["candidates"][0]["key"]}).status_code == 200
    # next time the same agency bills the same client, it is recognised and applied on its own
    nxt = booking(db_session, sor, "Visit St Pete Clearwater", 2400, booked=TODAY - timedelta(days=3))
    invoice(db_session, "56399", "Rooster", 2400, ref="OBH 105")
    assert run(db_session)["auto"] == 1
    db_session.refresh(nxt)
    assert nxt.invoice_number == "56399" and nxt.xero_link_source == "auto"


def test_one_invoice_for_several_bookings(db_session, sor):
    a = booking(db_session, sor, "Visit Mesa", 700)
    b = booking(db_session, sor, "Visit Mesa", 800, booked=TODAY - timedelta(days=21))
    invoice(db_session, "56303", "Visit Mesa", 1500, ref="OBH 105")
    assert run(db_session)["auto"] == 1
    for o in (a, b):
        db_session.refresh(o)
        assert o.invoice_number == "56303" and float(o.invoice_value_gbp) == float(o.value_gbp)  # each keeps its own share


def test_foreign_currency_invoice_is_converted(db_session, sor):
    b = booking(db_session, sor, "Visit Florida", 1000)
    invoice(db_session, "56304", "Visit Florida", 1350, cur="USD", rate=1.35, ref="OBH 105")
    assert run(db_session)["auto"] == 1
    db_session.refresh(b)
    assert float(b.invoice_value_gbp) == 1000


def test_invoice_that_fits_nothing_is_listed_not_queued(client, db_session, sor):
    booking(db_session, sor, "Foodcase", 1000)
    invoice(db_session, "56305", "Somebody Else", 123456)
    assert run(db_session)["no_fit"] == 1 and items(db_session) == []
    listed = client.get("/api/sales/xero/unmatched").json()
    assert [i["number"] for i in listed["items"]] == ["56305"] and listed["as_of"]


def test_typed_numbers_get_a_real_link_and_hand_edits_keep_it_in_step(client, db_session, sor):
    b = booking(db_session, sor, "Foodcase", 1000, invoice_number="inv 7")
    inv = invoice(db_session, "INV7", "Foodcase", 1000)
    assert run(db_session)["typed_links"] == 1
    db_session.refresh(b)
    assert b.xero_invoice_id == inv.id and b.xero_link_source == "typed"
    out = client.get("/api/sales/orders").json()["items"][0]["xero"]
    assert out["link"] == "typed" and out["url"].endswith(inv.xero_id) and out["state"] == "paid"
    # typing a different number moves the link; clearing it removes it
    other = invoice(db_session, "INV8", "Foodcase", 1000)
    assert client.patch(f"/api/sales/orders/{b.id}", json={"invoice_number": "INV8"}).status_code == 200
    db_session.refresh(b)
    assert b.xero_invoice_id == other.id
    client.patch(f"/api/sales/orders/{b.id}", json={"invoice_number": ""})
    db_session.refresh(b)
    assert b.xero_invoice_id is None and b.xero_link_source is None


def test_a_waiting_item_is_withdrawn_if_someone_types_the_number_first(db_session, sor):
    a = booking(db_session, sor, "Delta", 650, edition="this")
    booking(db_session, sor, "Delta", 650, edition="last", booked=TODAY - timedelta(days=12))
    invoice(db_session, "56306", "Delta Air Lines", 650)
    run(db_session)
    assert len(items(db_session, "pending")) == 1
    a.invoice_number = "56306"
    db_session.flush()
    out = run(db_session)
    assert out["withdrawn"] == 1 and out["typed_links"] == 1
    assert items(db_session, "pending") == [] and items(db_session, "approved")[0].resolved_action == "linked_elsewhere"


def test_old_auto_link_items_are_tidied_away_and_an_undone_one_is_remembered(db_session, sor):
    b = booking(db_session, sor, "Foodcase", 1000)
    inv = invoice(db_session, "56320", "Foodcase", 1000, ref="OBH 105")
    run(db_session)
    # an item left by an earlier version, for a link that has since been undone
    db_session.add(ReviewQueueItem(id=uuid.uuid4(), kind=xm.KIND, status="approved", resolved_action="auto_link",
                                   payload={"invoice_id": str(inv.id), "invoice_match": {}}))
    im.unlink_order(db_session, db_session.get(SalesOrder, b.id), None)
    db_session.flush()
    run(db_session)
    assert items(db_session) == [] and db_session.get(SalesOrder, b.id).invoice_number is None


def test_undo_clears_the_link_and_the_invoice_is_not_offered_again(client, db_session, sor):
    b = booking(db_session, sor, "Foodcase", 1000)
    invoice(db_session, "56307", "Foodcase", 1000, ref="OBH 105")
    run(db_session)
    r = client.post(f"/api/sales/orders/{b.id}/xero-unlink")
    assert r.status_code == 200 and r.json()["invoice_number"] is None and r.json()["xero"] is None
    db_session.refresh(b)
    assert b.xero_invoice_id is None and b.invoiced_on is None
    run(db_session)  # not re-linked: the earlier decision is remembered
    db_session.refresh(b)
    assert b.invoice_number is None
    # hand-typed links can't be undone with this button
    c = booking(db_session, sor, "Other", 500, invoice_number="INV9")
    invoice(db_session, "INV9", "Other", 500)
    run(db_session)
    assert client.post(f"/api/sales/orders/{c.id}/xero-unlink").status_code == 400


def test_confirming_refuses_stale_or_already_linked_bookings(client, db_session, sor):
    a = booking(db_session, sor, "Delta", 650, edition="this")
    booking(db_session, sor, "Delta", 650, edition="last", booked=TODAY - timedelta(days=12))
    invoice(db_session, "56308", "Delta Air Lines", 650)
    run(db_session)
    item = items(db_session, "pending")[0]
    cand = item.payload["invoice_match"]["candidates"][0]["bookings"][0]["id"]
    target = db_session.get(SalesOrder, uuid.UUID(cand))
    target.status = "cancelled"
    admin = make_user(db_session, role="admin")
    db_session.commit()
    r = client.post(f"/api/review-queue/{item.id}/actions/link", headers=identity_headers(admin),
                    json={"chosen_entity_id": item.payload["invoice_match"]["candidates"][0]["key"]})
    assert r.status_code == 400 and "cancelled" in r.json()["detail"]


def test_two_invoices_cannot_take_the_same_booking_in_one_run(db_session, sor):
    b = booking(db_session, sor, "Foodcase", 1000)
    invoice(db_session, "56309", "Foodcase", 1000, ref="OBH 105")
    invoice(db_session, "56310", "Foodcase", 1000, ref="OBH 105")
    out = run(db_session)
    assert out["auto"] == 1 and out["review"] == 1
    assert "Another invoice" in items(db_session, "pending")[0].payload["invoice_match"]["reason"]
    assert db_session.get(SalesOrder, b.id).invoice_number in ("56309", "56310")


def test_review_cap_defers_the_rest_to_the_next_run(db_session, sor):
    for i in range(3):
        booking(db_session, sor, f"Client {i}", 1000 + i)
        invoice(db_session, f"6000{i}", f"Totally Different {i}", 1000 + i)
    assert run(db_session, max_new=2)["deferred"] == 1
    assert run(db_session, max_new=2)["review"] == 1


def test_drafts_and_voided_invoices_are_ignored(db_session, sor):
    booking(db_session, sor, "Foodcase", 1000)
    invoice(db_session, "56311", "Foodcase", 1000, status="DRAFT")
    invoice(db_session, "56312", "Foodcase", 1000, status="VOIDED")
    assert run(db_session) == {"typed_links": 0, "no_fit": 0}


def test_settings_and_job_are_registered(db_session):
    from app.automations.scheduler import all_jobs
    from app.automations.settings_registry import get_def

    job = next(j for j in all_jobs() if j.id == "xero_invoice_match_scan")
    assert job.enabled_flag == "automations_xero_match_enabled"
    assert get_def("xero_match_auto_link") and get_def("xero_match_max_per_run")
    from app.core.config import settings
    assert settings.automations_xero_match_enabled is False  # off until someone switches it on


def test_name_helpers():
    assert im.norm("Delta Air Lines Ltd.") == "delta air lines"
    assert im.norm("Tripstax & Co") == "tripstax"


# ---- invoice numbers written in different styles ------------------------------------------

SAME = [
    ("INV-0309", "inv 0309"), ("INV-0309", "Inv0309"), ("INV-0309", "INV 309"), ("INV-0309", "inv-309"),
    ("INV-0309", "INV_0309"), ("INV-0309", "inv.0309"), ("INV-0309", "INV/0309"), ("INV-0309", "#INV 0309 "),
    ("INV-0309", "Invoice"[:3] + " No. 0309"), ("INV-0309", "INV – 0309"), ("inv4434", "INV-4434"), ("INV-4434", "inv 04434"),
    ("56264", " 56264"), ("56264", "056264"),
]
DIFFERENT = [("INV-0309", "INV-0310"), ("INV-0309", "INV-3090"), ("INV-0309", "CN-0309"), ("INV-1000", "INV-100"),
             ("56264", "56265"), ("INV-0309", "INV-0309-1")]


@pytest.mark.parametrize("a, b", SAME)
def test_the_same_number_written_differently_is_recognised(a, b):
    assert canonical(a) == canonical(b)


@pytest.mark.parametrize("a, b", DIFFERENT)
def test_a_different_number_is_never_matched(a, b):
    assert canonical(a) != canonical(b)


def test_empty_numbers_mean_nothing():
    assert canonical(None) is None and canonical("") is None and canonical("  -  ") is None


def test_the_database_rule_agrees_with_the_python_rule(db_session):
    from sqlalchemy import select

    for n in [a for a, _ in SAME] + [b for _, b in SAME] + [a for a, _ in DIFFERENT] + [b for _, b in DIFFERENT] + ["INV No 5", "Nr. 007", "0", "000", "INV00"]:
        assert db_session.scalar(select(canonical_sql(n))) == canonical(n), n


def test_a_typed_number_in_another_style_links_to_the_invoice_instead_of_going_to_review(db_session, sor):
    cases = [("INV 0309", "INV-0309"), ("inv4434", "INV-4434"), ("Inv-0511", "INV-511"), ("56264 ", "056264")]
    pairs = []
    for i, (typed, in_xero) in enumerate(cases):
        o = booking(db_session, sor, f"Client {i}", 100 + i, invoice_number=typed)
        pairs.append((o, invoice(db_session, in_xero, f"Client {i}", 100 + i)))
    out = run(db_session)
    assert out["typed_links"] == 4 and out.get("review", 0) == 0 and items(db_session) == []
    for o, inv in pairs:
        db_session.refresh(o)
        assert o.xero_invoice_id == inv.id and o.xero_link_source == "typed"


def test_digits_only_matches_when_exactly_one_invoice_fits(db_session, sor):
    a = booking(db_session, sor, "Alpha", 100, invoice_number="309")
    only = invoice(db_session, "INV-0309", "Alpha", 100)
    assert find_invoice(db_session, "309").id == only.id
    # two invoices end in these digits -> too ambiguous to guess
    invoice(db_session, "CN-309", "Beta", 50)
    assert find_invoice(db_session, "309") is None
    assert find_invoice(db_session, "INV-0309").id == only.id  # a full number is still exact
    # sheet has a prefix, Xero is digits-only
    solo = invoice(db_session, "77123", "Gamma", 10)
    assert find_invoice(db_session, "INV 77123").id == solo.id
    assert find_invoice(db_session, "INV 99999") is None


def test_an_old_pending_item_is_withdrawn_once_the_number_is_recognised(db_session, sor):
    b = booking(db_session, sor, "Rifkin Research", 310, invoice_number="INV 0309")
    inv = invoice(db_session, "INV-0309", "Rifkin Research", 310)
    inv.number_key = "INV-0309"          # keys written by the old rule: the dash made them differ
    db_session.add(ReviewQueueItem(id=uuid.uuid4(), kind=xm.KIND, status="pending",
                                   payload={"invoice_id": str(inv.id), "invoice_match": {}}))
    inv.number_key = canonical(inv.invoice_number)   # what the migration does
    out = run(db_session)
    assert out["typed_links"] == 1 and out["withdrawn"] == 1
    db_session.refresh(b)
    assert b.xero_invoice_id == inv.id and items(db_session, "pending") == []


def test_payment_state_follows_a_differently_written_number(client, db_session, sor):
    booking(db_session, sor, "Foodcase", 1000, invoice_number="inv 0309")
    invoice(db_session, "INV-0309", "Foodcase", 1000)
    first = client.get("/api/sales/orders").json()["items"][0]
    assert first["xero"]["state"] == "paid" and first["xero"]["invoice_number"] == "INV-0309"
    assert client.get("/api/sales/orders?xero=paid").json()["total"] == 1


# ---- review queue: filters and sorting for these items ------------------------------------

def _waiting(db, sor, specs):
    """Several waiting items: (client, rep, value, days ago booked, paid) each with a different-name invoice."""
    for i, (client, rep, value, days, paid) in enumerate(specs):
        booking(db, sor, client, value, rep=rep, booked=TODAY - timedelta(days=days))
        invoice(db, f"7000{i}", f"Agency {i}", value, paid=paid)
    run(db)


def test_kind_advertises_its_filters_and_date_sort(client, db_session):
    admin = make_user(db_session, role="admin")
    db_session.commit()
    kind = next(k for k in client.get("/api/review-queue/kinds", headers=identity_headers(admin)).json() if k["kind"] == xm.KIND)
    assert [f["key"] for f in kind["facets"]] == ["salesperson", "title", "payment", "match", "why"]
    assert kind["date_sort_label"] == "booking"


def test_filters_have_counts_and_narrow_the_list(client, db_session, sor):
    _waiting(db_session, sor, [("Alpha Travel", "SP", 111, 30, True), ("Beta Travel", "SP", 222, 10, False), ("Gamma Travel", "ST", 333, 20, True)])
    admin = make_user(db_session, role="admin")
    db_session.commit()
    h = identity_headers(admin)
    facets = {f["key"]: {o["value"]: o["count"] for o in f["options"]} for f in client.get(f"/api/review-queue/facets?kind={xm.KIND}", headers=h).json()}
    assert facets["salesperson"] == {"Sally Parker": 2, "Steven Thompson": 1}
    assert facets["payment"] == {"Paid": 2, "Awaiting payment": 1} and facets["title"] == {"OnBoard Hospitality (OBH)": 3}
    assert facets["why"] == {"Invoice is to a different name": 3}

    def names(qs=""):
        r = client.get(f"/api/review-queue?kind={xm.KIND}{qs}", headers=h).json()
        return sorted(i["payload"]["summary"].split(" to ")[1].split(" (")[0] for i in r["items"])

    assert names("&facet=salesperson:Steven Thompson") == ["Agency 2"]
    assert names("&facet=salesperson:Sally Parker&facet=payment:Paid") == ["Agency 0"]
    assert names("&facet=salesperson:Sally Parker&facet=salesperson:Steven Thompson") == ["Agency 0", "Agency 1", "Agency 2"]  # same filter: either
    # counts beside the other filters follow what is already chosen, but a filter's own options stay available
    narrowed = {f["key"]: {o["value"]: o["count"] for o in f["options"]}
                for f in client.get(f"/api/review-queue/facets?kind={xm.KIND}&facet=salesperson:Sally Parker", headers=h).json()}
    assert narrowed["payment"] == {"Paid": 1, "Awaiting payment": 1} and narrowed["salesperson"] == {"Sally Parker": 2, "Steven Thompson": 1}


def test_sorting_by_booking_date_puts_the_latest_first(client, db_session, sor):
    _waiting(db_session, sor, [("Alpha Travel", "SP", 111, 30, True), ("Beta Travel", "SP", 222, 5, True), ("Gamma Travel", "SP", 333, 15, True)])
    admin = make_user(db_session, role="admin")
    db_session.commit()
    h = identity_headers(admin)

    def order(sort):
        items = client.get(f"/api/review-queue?kind={xm.KIND}&sort={sort}", headers=h).json()["items"]
        return [i["payload"]["sort_date"] for i in items]

    newest = order("date_desc")
    assert newest == sorted(newest, reverse=True) and newest[0] == (TODAY - timedelta(days=5)).isoformat()
    assert order("date_asc") == sorted(newest)


def test_older_items_get_their_filter_values_on_the_next_run(db_session, sor):
    booking(db_session, sor, "Alpha Travel", 111)
    inv = invoice(db_session, "70050", "Agency X", 111)
    run(db_session)
    item = items(db_session, "pending")[0]
    payload = dict(item.payload)
    del payload["facets"], payload["sort_date"]
    payload["invoice_match"] = {**payload["invoice_match"]}
    payload["invoice_match"].pop("reason_key")
    for c in payload["invoice_match"]["candidates"]:
        for b in c["bookings"]:
            b.pop("title", None)
    item.payload = payload
    db_session.flush()
    run(db_session)
    got = db_session.get(ReviewQueueItem, item.id).payload
    assert got["facets"]["why"] == "Invoice is to a different name" and got["facets"]["title"] == "OnBoard Hospitality (OBH)"
    assert got["facets"]["salesperson"] == "Sally Parker" and got["sort_date"]


def test_a_bulk_action_only_touches_the_filtered_items(client, db_session, sor):
    _waiting(db_session, sor, [("Alpha Travel", "SP", 111, 30, True), ("Beta Travel", "ST", 222, 10, False)])
    admin = make_user(db_session, role="admin")
    db_session.commit()
    h = identity_headers(admin)
    r = client.post(f"/api/review-queue/bulk-actions/none?kind={xm.KIND}&facet=salesperson:Steven Thompson", headers=h, json={})
    assert r.status_code == 200 and r.json()["succeeded"] == 1
    db_session.expire_all()
    assert [i.status for i in db_session.query(ReviewQueueItem).filter_by(kind=xm.KIND).order_by(ReviewQueueItem.created_at)].count("pending") == 1
