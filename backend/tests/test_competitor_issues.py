"""SALES-006/007: a competitor's issue read for its advertisers, compared with ours, and an approach drafted."""
import io
import uuid
from datetime import date, timedelta

import pytest
from docx import Document

from tests.conftest import identity_headers, make_user
from tests.test_sales_orders import _NoCloseSession

from app.automations import competitor_issues as ci
from app.automations import llm
from app.models import Company, Contact, Email, Note, ReviewQueueItem, SalesEdition, SalesOrder, SalesTitle
from app.sales import deals as dl
from app.sales.reference import ensure_reference_data

needs_pdf = pytest.mark.skipif(not dl.pdf_available(), reason="LibreOffice isn't installed here")


def _pdf(pages: list[str]) -> bytes:
    d = Document()
    for i, text in enumerate(pages):
        d.add_paragraph(text)
        if i < len(pages) - 1:
            d.add_page_break()
    buf = io.BytesIO()
    d.save(buf)
    import subprocess, tempfile, pathlib
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(tmp) / "x.docx"
        src.write_bytes(buf.getvalue())
        subprocess.run(["soffice", "--headless", f"-env:UserInstallation=file://{tmp}/p", "--convert-to", "pdf", "--outdir", tmp, str(src)],
                       check=True, capture_output=True, timeout=90)
        return (pathlib.Path(tmp) / "x.pdf").read_bytes()


def _world(db):
    ensure_reference_data(db)
    st = db.query(SalesTitle).filter_by(slug="selling-travel").one()
    ed = SalesEdition(id=uuid.uuid4(), title_id=st.id, year=date.today().year, name="Oct", edition_date=date.today())
    db.add(ed)
    cos = {}
    for name, booked in (("Visit Malta", date.today() - timedelta(days=30)), ("Tourism Ireland", date.today() - timedelta(days=700)),
                         ("Saga Holidays", None)):
        co = Company(id=uuid.uuid4(), source_db="sellingtravel", source_act_id=uuid.uuid4().hex, name=name)
        db.add(co)
        db.flush()
        c = Contact(id=uuid.uuid4(), source_db="sellingtravel", source_act_id=uuid.uuid4().hex, full_name=f"{name} Person", first_name="Al",
                    company_id=co.id, job_title="Marketing Manager", custom_fields={})
        db.add(c)
        db.flush()
        db.add(Email(id=uuid.uuid4(), source_db="sellingtravel", source_act_id=uuid.uuid4().hex, contact_id=c.id,
                     address=f"al@{name.split()[0].lower()}.example", is_primary=True))
        if booked:
            db.add(SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name=name, company_id=co.id, booked_on=booked, status="booked"))
        cos[name] = (co, c)
    db.flush()
    return st, cos


ADS = {"advertisers": [{"company": "Visit Malta", "page": 2, "website": "visitmalta.com", "kind": "advert"},
                       {"company": "Tourism Ireland", "page": 3, "website": None, "kind": "sponsored"},
                       {"company": "Saga Holidays Ltd", "page": 4, "website": "saga.co.uk", "kind": "advert"},
                       {"company": "Fjord Cruises", "page": 5, "website": "www.fjordcruises.no", "kind": "advert"},
                       {"company": "Travel Weekly", "page": 1, "website": None, "kind": "advert"}]}


@needs_pdf
def test_upload_reads_the_issue_and_the_buttons_work(client, db_session, monkeypatch):
    st, cos = _world(db_session)
    sally = make_user(db_session, role="sales", name="Sally")
    db_session.commit()
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(llm, "extract_json", lambda *a, **k: ADS)
    monkeypatch.setattr(llm, "extract_json_from_image", lambda *a, **k: {"is_advert": False})
    pdf = _pdf(["Travel Weekly news this week " * 5, "Visit Malta advert " * 5, "Tourism Ireland sponsored " * 5,
                "Saga Holidays " * 5, "Fjord Cruises www.fjordcruises.no " * 4])
    h = identity_headers(sally, access=[("sellingtravel", None)])
    opts = client.get("/api/automations/competitor-issues/options", headers=h).json()
    assert str(st.id) in [t["id"] for t in opts["titles"]] and "Travel Weekly" in opts["competitors"]
    r = client.post("/api/automations/competitor-issues/upload", headers=h,
                    data={"title_id": str(st.id), "competitor": "Travel Weekly", "issue": "30 October"},
                    files={"file": ("tw.pdf", pdf, "application/pdf")})
    assert r.status_code == 200 and r.json()["started"]
    card = db_session.query(ReviewQueueItem).filter_by(kind="competitor_issue").one()
    p = card.payload
    assert p["owner_user_id"] == str(sally.id)
    assert p["summary"] == "4 advertisers in Travel Weekly 30 October: 2 to approach, 1 new to us"   # the competitor itself left out
    labels = [(d["label"].strip(), d["value"]) for d in p["details"]]
    assert ("Advertising with us now", "1") in labels and ("Advertised with us before", "1") in labels
    assert ("On our database, never booked", "1") in labels and ("New to us", "1") in labels
    assert any(d.get("href") == f"/companies/{cos['Saga Holidays'][0].id}" for d in p["details"])
    assert sorted(p["merge"]["contact_ids"]) == sorted([str(cos["Tourism Ireland"][1].id), str(cos["Saga Holidays"][1].id)])
    assert "Travel Weekly" not in p["merge"]["body"] and "{{company}}" in p["merge"]["body"]
    assert p["new_companies"] == [{"company": "Fjord Cruises", "website": "fjordcruises.no", "page": 5}]

    r = client.post(f"/api/review-queue/{card.id}/actions/open_merge", json={"fields": {"add_new": "true"}}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["payload"]["open_href"] == f"/mail-merge?review={card.id}"
    fj = db_session.query(Company).filter_by(name="Fjord Cruises").one()
    assert fj.website == "fjordcruises.no" and fj.source_db == "sellingtravel"
    assert "Travel Weekly 30 October (page 5)" in db_session.query(Note).filter_by(entity_id=fj.id).one().body


def test_without_the_brain_the_web_addresses_are_listed(db_session):
    pages = [{"n": 1, "text": "Book now at www.fjordcruises.no or email us at info@gmail.com"}, {"n": 2, "text": ""}]
    found, brain = ci.find_advertisers(b"", pages, use_brain=False, picture_pages=0)
    assert not brain and found == [{"company": "Fjordcruises", "page": 1, "website": "fjordcruises.no", "kind": "web address"}]


def test_a_file_that_isnt_a_pdf_is_refused(client, db_session):
    st, _ = _world(db_session)
    h = identity_headers(make_user(db_session, role="sales"))
    r = client.post("/api/automations/competitor-issues/upload", headers=h, data={"title_id": str(st.id), "competitor": "TTG"},
                    files={"file": ("x.docx", b"PK\x03\x04", "application/octet-stream")})
    assert r.status_code == 422 and "isn't a PDF" in r.json()["detail"]
