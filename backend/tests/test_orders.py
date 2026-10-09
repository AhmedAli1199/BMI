"""Multi-item orders and order confirmations (app/sales/deals.py, api/routes/deals.py), using BMI's own
confirmations as worked examples: SunExpress (4 insertions, 10% agency), Travel Wisconsin (a £3,000
package of four dated items), AMEX GBT (a schedule of works with free added-value columns)."""
import io
import uuid
from datetime import date, timedelta

import docx
import pytest
from tests.conftest import identity_headers, make_user
from tests.test_sales_orders import _row, _sheet_rows, _write_book

from app.models import SalesDeal, SalesEdition, SalesOrder, SalesOrderCredit, SalesRep, SalesTitle
from app.sales import commission as cm
from app.sales import deals as dl
from app.sales.commission_seed import load_structure
from app.sales.reference import ensure_reference_data
from app.sales.sor_import import import_sor


# ---- pricing ----------------------------------------------------------------------------------

def test_price_items_discounts_free_items_and_agency():
    lines = [
        {"description": "Full page", "unit_price": 2777.78, "list_price": 2777.78, "placements": [{}, {}, {}, {}]},
        {"description": "Digital column", "unit_price": 750, "list_price": 750, "added_value": True, "placements": [{}, {}]},
    ]
    pr = dl.price(lines, agency_pct=0.10)
    assert pr.total_gbp == 11111.12 and pr.agency_gbp == 1111.11 and pr.payable_gbp == 10000.01
    assert pr.added_value_gbp == 1500 and pr.rate_card_gbp == 12611.12
    assert sum(p["value_gbp"] for p in pr.lines[0]["placements"]) == pr.total_gbp
    assert sum(p["agency_gbp"] for ln in pr.lines for p in ln["placements"]) == pr.agency_gbp
    assert all(p["value_gbp"] == 0 for p in pr.lines[1]["placements"])
    # a line's own % off, then % off the whole order
    pr = dl.price([{"unit_price": 1000, "discount_pct": 0.1, "placements": [{}, {}]}, {"unit_price": 500, "placements": [{}]}], discount_pct=0.05)
    assert pr.gross_gbp == 2300 and pr.discount_gbp == 115 and pr.total_gbp == 2185


def test_price_package_shared_by_rate_card_evenly_or_typed():
    lines = [{"description": "Sponsored feature", "list_price": 2500, "placements": [{}]},
             {"description": "Online article", "list_price": 995, "placements": [{}]},
             {"description": "Solus email", "list_price": 1750, "placements": [{}]},
             {"description": "News story", "list_price": 250, "placements": [{}]}]
    pr = dl.price(lines, pricing="package", package_price=3000)
    vals = [ln["placements"][0]["value_gbp"] for ln in pr.lines]
    assert sum(vals) == 3000 and vals[0] > vals[2] > vals[1] > vals[3]
    assert pr.off_rate_card_pct == round(100 * (1 - 3000 / 5495), 2)
    pr = dl.price(lines, pricing="package", package_price=3000, package_split="even")
    assert [ln["placements"][0]["value_gbp"] for ln in pr.lines] == [750, 750, 750, 750]
    typed = [dict(ln, share_gbp=s) for ln, s in zip(lines, (2000, 500, 400, 100))]
    pr = dl.price(typed, pricing="package", package_price=3000, package_split="manual")
    assert [ln["placements"][0]["value_gbp"] for ln in pr.lines] == [2000, 500, 400, 100] and not pr.warnings
    with pytest.raises(dl.OrderError):
        dl.price([{"description": "x", "placements": []}])


# ---- orders through the API --------------------------------------------------------------------

@pytest.fixture()
def w(db_session):
    ensure_reference_data(db_session)
    load_structure(db_session)
    titles = {t.slug: t for t in db_session.query(SalesTitle).all()}
    reps = {r.code: r for r in db_session.query(SalesRep).all()}

    def ed(slug, name, pub, kind="issue"):
        e = SalesEdition(id=uuid.uuid4(), title_id=titles[slug].id, year=pub.year, name=name, edition_date=pub, kind=kind)
        db_session.add(e)
        db_session.flush()
        return e

    admin = make_user(db_session, role="admin")
    return {"db": db_session, "ed": ed, "titles": titles, "reps": reps, "h": identity_headers(admin)}


def _wisconsin(w):
    feat = w["ed"]("selling-travel", "AprMay2026", date(2026, 4, 1))
    may = w["ed"]("selling-travel-online", "May 2026", date(2026, 5, 1), kind="month")
    jun = w["ed"]("selling-travel-online", "June 2026", date(2026, 6, 1), kind="month")
    return {
        "client_name": "Travel Wisconsin", "contact_name": "Keely Burton", "contact_email": "keely@example.com",
        "confirmation_address": "Cellet Travel Services Ltd\nBloxham", "rep_id": str(w["reps"]["SP"].id), "booked_on": "2026-01-13",
        "publication_label": "Selling Travel", "pricing": "package", "package_price_gbp": 3000, "package_label": "Marketing package for Travel Wisconsin",
        "lines": [
            {"description": "Sponsored feature", "list_price": 2500, "placements": [{"edition_id": str(feat.id)}]},
            {"description": "Online article", "list_price": 995, "placements": [{"edition_id": str(feat.id), "item_date": "2026-04-22"}]},
            {"description": "Solus html email", "list_price": 1750, "placements": [{"edition_id": str(may.id), "item_date": "2026-05-13"}]},
            {"description": "News story", "list_price": 250, "placements": [{"edition_id": str(jun.id), "item_date": "2026-06-10", "copy_due": "2026-06-01"}]},
        ],
    }


def test_order_makes_one_booking_per_item_and_commission_is_earned_item_by_item(w, client):
    r = client.post("/api/sales/deals", json=_wisconsin(w), headers=w["h"])
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "pencilled" and d["totals"]["total_gbp"] == 3000 and len(d["schedule"]) == 4
    items = w["db"].query(SalesOrder).filter_by(deal_id=uuid.UUID(d["id"])).all()
    assert len(items) == 4 and round(sum(float(o.value_gbp) for o in items), 2) == 3000
    assert {o.status for o in items} == {"pencilled"}
    # pencilled orders don't earn commission
    ctx = cm.Ctx.build(w["db"])
    assert cm.core(ctx, w["reps"]["SP"], "2026-05")["lines"] == []
    r = client.post(f"/api/sales/deals/{d['id']}/status", json={"status": "confirmed"}, headers=w["h"])
    assert r.json()["status"] == "confirmed" and r.json()["confirmed_at"]
    ctx = cm.Ctx.build(w["db"])
    months = {p: [ln["client"] for ln in cm.core(ctx, w["reps"]["SP"], p)["lines"]] for p in ("2026-04", "2026-05", "2026-06")}
    assert [len(v) for v in months.values()] == [2, 1, 1]   # the email earns in May, the news story in June
    credits = w["db"].query(SalesOrderCredit).filter(SalesOrderCredit.order_id.in_([o.id for o in items])).all()
    assert round(sum(float(c.amount_gbp) for c in credits), 2) == 3000
    # all on the first deal: new business for every item
    assert all(ln["new_business"] == "new" for p in ("2026-04", "2026-05") for ln in cm.core(ctx, w["reps"]["SP"], p)["lines"])
    # the document reads like BMI's
    doc = client.get(f"/api/sales/deals/{d['id']}/document", headers=w["h"]).json()
    assert doc["heading"] == "ORDER CONFIRMATION" and doc["package"]["price"] == 3000 and doc["insertions"] == "April, May, June 2026"
    assert doc["rows"][2]["when"] == ["13th May"] and doc["copy_dates"][0]["date"] == "2026-06-01"
    x = client.get(f"/api/sales/deals/{d['id']}/document.docx", headers=w["h"])
    text = "\n".join(c.text for t in docx.Document(io.BytesIO(x.content)).tables for row in t.rows for c in row.cells)
    assert "Marketing package for Travel Wisconsin" in text and "£3,000.00" in text and "Solus html email - 13th May" in text


def test_editing_an_order_keeps_items_in_step_and_protects_invoiced_ones(w, client):
    body = _wisconsin(w)
    d = client.post("/api/sales/deals", json={**body, "status": "confirmed"}, headers=w["h"]).json()
    sched = {s["description"]: s for s in d["schedule"]}
    news = w["db"].get(SalesOrder, uuid.UUID(sched["News story"]["order_id"]))
    news.invoice_number = "INV-77"
    w["db"].flush()
    # the item's price can't be changed on its own
    r = client.patch(f"/api/sales/orders/{news.id}", json={"value_gbp": 10}, headers=w["h"])
    assert r.status_code == 409 and "part of order" in r.json()["detail"]
    assert client.patch(f"/api/sales/orders/{news.id}", json={"invoice_note": "raised"}, headers=w["h"]).status_code == 200
    # drop the news story and the online article from the order, switch to item prices
    lines = d["lines"][:1] + d["lines"][2:3]
    lines[0]["unit_price"], lines[1]["unit_price"] = 2500, 1750
    r = client.put(f"/api/sales/deals/{d['id']}", json={**body, "pricing": "items", "lines": lines}, headers=w["h"])
    assert r.status_code == 200, r.text
    assert r.json()["totals"]["total_gbp"] == 4250 and any("already invoiced" in n for n in r.json()["notes"])
    w["db"].expire_all()
    left = w["db"].query(SalesOrder).filter_by(deal_id=uuid.UUID(d["id"])).all()
    assert sorted((o.description, o.status) for o in left) == [("News story", "cancelled"), ("Solus html email", "booked"), ("Sponsored feature", "booked")]
    # cancelling keeps what has already run
    r = client.post(f"/api/sales/deals/{d['id']}/status", json={"status": "cancelled", "reason": "Budget cut"}, headers=w["h"])
    assert r.json()["status"] == "cancelled"
    assert client.delete(f"/api/sales/deals/{d['id']}", headers=w["h"]).status_code == 409


def test_split_order_rep_access_and_numbers(w, client, db_session):
    e = w["ed"]("tbtm", "Summer 2026", date(2026, 6, 10))
    sally = make_user(db_session, role="sales")
    w["reps"]["SP"].user_id = sally.id
    db_session.flush()
    h = identity_headers(sally)
    body = {"client_name": "Shared Air", "split": [{"rep_id": str(w["reps"]["SP"].id), "pct": 0.5}, {"rep_id": str(w["reps"]["ST"].id), "pct": 0.5}],
            "lines": [{"description": "Full page", "unit_price": 1001, "placements": [{"edition_id": str(e.id)}]}]}
    d = client.post("/api/sales/deals", json=body, headers=h).json()
    assert d["rep"]["id"] == str(w["reps"]["SP"].id) and d["can_edit"]
    o = db_session.query(SalesOrder).filter_by(deal_id=uuid.UUID(d["id"])).one()
    assert sorted(float(c.amount_gbp) for c in db_session.query(SalesOrderCredit).filter_by(order_id=o.id)) == [500.5, 500.5]
    d2 = client.post("/api/sales/deals", json={**body, "split": []}, headers=w["h"]).json()
    assert d2["number"] == d["number"] + 1
    lst = client.get("/api/sales/deals?q=Shared", headers=w["h"]).json()
    assert lst["total"] == 2 and lst["total_value_gbp"] == 2002 and lst["items"][0]["items"] == 1
    other = make_user(db_session, role="sales")
    assert client.put(f"/api/sales/deals/{d2['id']}", json=body, headers=identity_headers(other)).status_code == 403
    assert client.post("/api/sales/deals", json={**body, "split": [{"rep_id": str(w["reps"]["SP"].id), "pct": 0.4}]}, headers=h).status_code == 422
    assert client.delete(f"/api/sales/deals/{d['id']}", headers=h).status_code == 204


def test_rebook_next_year_moves_items_to_matching_issues(w, client):
    a = w["ed"]("tbtm", "Summer 2026", date(2026, 6, 10))
    w["ed"]("tbtm", "Summer 2027", date(2027, 6, 9))
    w["ed"]("tbtm", "Winter 2027", date(2027, 12, 8))
    d = client.post("/api/sales/deals", json={"client_name": "AMEX GBT", "document": "schedule",
                                              "lines": [{"description": "3/4 page column", "unit_price": 2250, "placements": [{"edition_id": str(a.id), "item_date": "2026-06-03"}]}]},
                    headers=w["h"]).json()
    iss = client.get(f"/api/sales/deals/issues?title_id={w['titles']['tbtm'].id}&include={a.id}", headers=w["h"]).json()
    assert {i["label"] for i in iss} >= {"Summer 2026", "Summer 2027", "Winter 2027"}
    r = client.post(f"/api/sales/deals/{d['id']}/rebook", headers=w["h"]).json()
    assert r["status"] == "pencilled" and r["rebooked_from_number"] == d["number"] and r["document"] == "schedule"
    assert r["schedule"][0]["edition"].endswith("Summer 2027") and r["schedule"][0]["runs_on"] == "2027-06-02"  # same weekday a year on


def test_reimporting_the_order_register_keeps_orders_made_in_the_app(w, client, tmp_path):
    y = tmp_path / "2026"
    y.mkdir()
    _write_book(y / "OBH 2026.xlsx", {"105": _sheet_rows([_row("15.01.26", "Foodcase", "FP", "SP", 1250.0, sp=1250.0)])})
    import_sor(w["db"], tmp_path)
    ed = w["db"].query(SalesEdition).filter_by(name="105").one()
    d = client.post("/api/sales/deals", json={"client_name": "Monty's", "status": "confirmed",
                                              "lines": [{"description": "Half page", "unit_price": 900, "placements": [{"edition_id": str(ed.id)}]}]},
                    headers=w["h"]).json()
    # the sheet now has Monty's too: the app's booking is kept and flagged as a possible double
    _write_book(y / "OBH 2026.xlsx", {"105": _sheet_rows([_row("15.01.26", "Foodcase", "FP", "SP", 1250.0, sp=1250.0),
                                                          _row("20.01.26", "Monty's", "0.5", "SP", 900.0, sp=900.0)])})
    import_sor(w["db"], tmp_path, replace=True)
    w["db"].expire_all()
    mine = w["db"].query(SalesOrder).filter_by(deal_id=uuid.UUID(d["id"])).one()
    new_ed = w["db"].query(SalesEdition).filter_by(name="105").one()
    assert mine.edition_id == new_ed.id and "counted twice" in mine.import_warning
    assert not w["db"].query(SalesEdition).filter(SalesEdition.name.like("%[kept%")).count()
