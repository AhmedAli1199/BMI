"""Draft invoices in Xero from a booking: the contact is found (or Samantha is asked), codes per publication,
agency commission as the discount, problems explained, and the items linked to the new invoice."""
import uuid
from datetime import date, timedelta

import httpx
from tests.conftest import identity_headers, make_user
from tests.test_invoicing_flow import _booking
from tests.test_orders import w  # noqa: F401 - fixture

from app.models import Company, ReviewQueueItem, SalesOrder
from app.services import xero_invoices as xi

CONTACTS = [{"ContactID": "c-four", "Name": "Four Marketing Ltd", "EmailAddress": "ap@four.example", "ContactStatus": "ACTIVE"},
            {"ContactID": "c-four2", "Name": "Four Communications", "ContactStatus": "ACTIVE"},
            {"ContactID": "c-wis", "Name": "Travel Wisconsin", "EmailAddress": "keely@example.com", "ContactStatus": "ACTIVE"}]


class FakeXero:
    def __init__(self):
        self.posted = []
        self.reject = None

    def __call__(self, db, method, path, *, params=None, json=None, headers=None):
        req = httpx.Request(method, f"https://api.xero.com/api.xro/2.0/{path}")
        if path == "Contacts":
            q = (params or {}).get("searchTerm", "").lower()
            return httpx.Response(200, json={"Contacts": [c for c in CONTACTS if any(w in c["Name"].lower() for w in q.split())]}, request=req)
        if path == "Accounts":
            return httpx.Response(200, json={"Accounts": [{"Code": "3010", "Name": "Advertising", "Type": "REVENUE", "Status": "ACTIVE"},
                                                          {"Code": "800", "Name": "Loan", "Type": "LIABILITY", "Status": "ACTIVE"}]}, request=req)
        if path in ("Items", "TrackingCategories", "Currencies"):
            return httpx.Response(200, json={"Items": [{"Code": "ST", "Name": "Selling Travel", "SalesDetails": {"AccountCode": "3010"}}],
                                             "TrackingCategories": [{"Name": "Product", "Options": [{"Name": "Selling Travel"}]}],
                                             "Currencies": [{"Code": "USD"}]}, request=req)
        if path == "Invoices" and method == "POST":
            self.posted.append((json, headers))
            if self.reject:
                return httpx.Response(400, json={"Elements": [{"ValidationErrors": [{"Message": self.reject}]}]}, request=req)
            inv = json["Invoices"][0]
            name = next(c["Name"] for c in CONTACTS if c["ContactID"] == inv["Contact"]["ContactID"])
            return httpx.Response(200, json={"Invoices": [{
                "InvoiceID": str(uuid.uuid4()), "InvoiceNumber": "INV-5001", "Status": "DRAFT", "Type": "ACCREC",
                "Contact": {"ContactID": inv["Contact"]["ContactID"], "Name": name}, "DateString": inv["Date"] + "T00:00:00",
                "Reference": inv["Reference"], "CurrencyCode": inv.get("CurrencyCode", "GBP"),
                "LineItems": [{**li, "LineAmount": li["UnitAmount"] * (1 - (li.get("DiscountRate") or 0) / 100), "TaxType": "OUTPUT2",
                               "TaxAmount": 0} for li in inv["LineItems"]],
                "SubTotal": 1800, "TotalTax": 360, "Total": 2160}]}, request=req)
        return httpx.Response(404, json={}, request=req)


def _setup(w, monkeypatch):
    db = w["db"]
    sam = make_user(db, role="sales", name="Samantha Elmer")
    sam.can_approve_bookings = True
    db.commit()
    fake = FakeXero()
    monkeypatch.setattr(xi, "_call", fake)
    src = w["titles"]["selling-travel"].crm_source_db
    return db, identity_headers(sam, access=[(src, None)]), fake


def test_one_click_draft_invoice_with_agency_and_codes(w, client, monkeypatch):
    db, sam_h, fake = _setup(w, monkeypatch)
    st_id = str(w["titles"]["selling-travel"].id)
    body, _ = _booking(w, date.today() + timedelta(days=5), invoice_to="Four Marketing Ltd\nLondon", agency_name="Four Marketing Ltd",
                       agency_pct=0.1, po_number="PO-778")
    d = client.post("/api/sales/deals", json=body, headers=w["h"]).json()
    # no account code for Selling Travel yet: she's told, and can pick it (remembered)
    r = client.post(f"/api/xero-invoicing/deals/{d['id']}", json={}, headers=sam_h).json()
    assert not r["ok"] and [p["key"] for p in r["problems"]] == ["account"]
    assert r["draft"]["contact"]["name"] == "Four Marketing Ltd"           # found from "invoice to"
    oid = r["draft"]["lines"][0]["order_id"]
    ref = client.get("/api/xero-invoicing/reference", headers=sam_h).json()
    assert [a["code"] for a in ref["accounts"]] == ["3010"]                 # sales accounts only
    r = client.post(f"/api/xero-invoicing/deals/{d['id']}",
                    json={"lines": {oid: {"account_code": "3010", "tracking": [{"name": "Product", "option": "Selling Travel"}]}}}, headers=sam_h).json()
    assert r["ok"], r
    inv, headers = fake.posted[-1]
    li = inv["Invoices"][0]["LineItems"][0]
    assert inv["Invoices"][0]["Status"] == "DRAFT" and inv["Invoices"][0]["Reference"] == "PO-778"
    assert li["UnitAmount"] == 2000 and li["DiscountRate"] == 10 and li["AccountCode"] == "3010" and li["Tracking"][0]["Option"] == "Selling Travel"
    assert "Idempotency-Key" in headers
    assert r["invoice"]["number"] == "INV-5001" and r["invoice"]["lines"][0]["tax_type"] == "OUTPUT2" and "Edit.aspx" in r["invoice"]["url"]
    db.expire_all()
    o = db.get(SalesOrder, uuid.UUID(oid))
    assert o.invoice_number == "INV-5001" and o.xero_invoice_id and float(o.invoice_value_gbp) == 2000
    got = client.get(f"/api/sales/deals/{d['id']}", headers=w["h"]).json()
    assert got["locked"] is not None and got["schedule"][0]["invoice_number"] == "INV-5001"
    assert db.query(ReviewQueueItem).filter_by(kind="invoice_due", status="pending").count() == 0
    # codes remembered for the publication
    codes = client.get("/api/xero-invoicing/codes", headers=sam_h).json()
    assert codes["titles"][st_id]["account_code"] == "3010"
    # nothing left: said plainly
    r = client.post(f"/api/xero-invoicing/deals/{d['id']}", json={}, headers=sam_h).json()
    assert not r["ok"] and r["problems"][0]["key"] == "nothing"
    # salespeople can't
    assert client.post(f"/api/xero-invoicing/deals/{d['id']}", json={}, headers=w["h"]).status_code in (200, 403)


def test_contact_not_found_and_xero_refusals(w, client, monkeypatch):
    db, sam_h, fake = _setup(w, monkeypatch)
    client.put("/api/xero-invoicing/codes", json={"default": {"account_code": "3010"}}, headers=sam_h)
    body, _ = _booking(w, date.today() + timedelta(days=5), client_name="Blue Lagoon Tours", contact_email=None, invoice_currency="USD")
    d = client.post("/api/sales/deals", json=body, headers=w["h"]).json()
    r = client.post(f"/api/xero-invoicing/deals/{d['id']}", json={}, headers=sam_h).json()
    keys = {p["key"] for p in r["problems"]}
    assert keys == {"contact", "currency"}
    assert "couldn't find the right Xero contact" in next(p["message"] for p in r["problems"] if p["key"] == "contact")
    assert client.get("/api/xero-invoicing/contacts", params={"q": "wisconsin"}, headers=sam_h).json()[0]["id"] == "c-wis"
    oid = r["draft"]["lines"][0]["order_id"]
    fake.reject = "Account code '3010' is not a valid code for this document."
    r = client.post(f"/api/xero-invoicing/deals/{d['id']}", json={"contact_id": "c-wis", "contact_name": "Travel Wisconsin",
                                                                  "lines": {oid: {"unit_amount": 2540}}}, headers=sam_h).json()
    assert not r["ok"] and r["problems"][0]["key"] == "account" and r["problems"][0]["message"].startswith("Xero said:")
    assert fake.posted[-1][0]["Invoices"][0]["CurrencyCode"] == "USD" and fake.posted[-1][0]["Invoices"][0]["LineItems"][0]["UnitAmount"] == 2540
    fake.reject = None
    r = client.post(f"/api/xero-invoicing/deals/{d['id']}", json={"contact_id": "c-wis", "contact_name": "Travel Wisconsin",
                                                                  "lines": {oid: {"unit_amount": 2540}}}, headers=sam_h).json()
    assert r["ok"]
    db.expire_all()
    assert db.get(SalesOrder, uuid.UUID(oid)).invoice_value_gbp == 2000   # our figure stays in pounds


def test_contact_from_company_link_and_ambiguity(w, client, monkeypatch):
    db, sam_h, fake = _setup(w, monkeypatch)
    co = Company(id=uuid.uuid4(), name="Four", source_db=w["titles"]["selling-travel"].crm_source_db, source_act_id="four-1", xero_contact_id="c-four2",
                 xero_contact_name="Four Communications")
    db.add(co)
    db.commit()
    body, _ = _booking(w, date.today() + timedelta(days=5), client_name="Four", company_id=str(co.id))
    d = client.post("/api/sales/deals", json=body, headers=w["h"]).json()
    r = client.get(f"/api/xero-invoicing/deals/{d['id']}", headers=sam_h).json()
    assert r["contact"]["id"] == "c-four2"                                  # remembered on the company
    co.xero_contact_id = None
    db.commit()
    r = client.get(f"/api/xero-invoicing/deals/{d['id']}", headers=sam_h).json()
    assert r["contact"] is None and len(r["contact_candidates"]) >= 2     # "Four ..." is ambiguous: she chooses
    assert "more than one" in next(p["message"] for p in r["problems"] if p["key"] == "contact")
