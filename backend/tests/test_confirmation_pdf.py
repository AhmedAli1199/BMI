"""FIN-007: the order confirmation as a locked PDF, Word, or both."""
import io
import uuid
from datetime import date, timedelta

import pytest
from pypdf import PdfReader

from tests.conftest import identity_headers, make_user
from tests.test_orders import w  # noqa: F401 - fixture

from app.models import MailAccount
from app.sales import deals as dl
from app.services import outlook

needs_pdf = pytest.mark.skipif(not dl.pdf_available(), reason="LibreOffice isn't installed here")


def _deal(w, client, h):
    st_id = str(w["titles"]["selling-travel"].id)
    ed = w["ed"]("selling-travel", "Dec issue", date.today() + timedelta(days=40))
    body = {"client_name": "Visit Malta", "contact_name": "Ana Borg", "contact_email": "ana@malta.example",
            "rep_id": str(w["reps"]["SP"].id), "status": "confirmed",
            "lines": [{"key": "page", "title_id": st_id, "description": "Full page advert", "unit_price": 2000,
                       "placements": [{"edition_id": str(ed.id)}]}]}
    r = client.post("/api/sales/deals", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


@needs_pdf
def test_download_as_a_locked_pdf(w, client):
    d = _deal(w, client, w["h"])
    r = client.get(f"/api/sales/deals/{d['id']}/document.pdf", headers=w["h"])
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert f'Order confirmation {d["number"]} Visit Malta.pdf' in r.headers["content-disposition"]
    pdf = PdfReader(io.BytesIO(r.content))
    assert pdf.is_encrypted and pdf.decrypt("")          # opens without a password...
    assert "Visit Malta" in pdf.pages[0].extract_text()   # ...shows the confirmation...
    assert not pdf.user_access_permissions & 8            # ...but can't be edited (bit 4 = modify)


def _sender(w, monkeypatch):
    db = w["db"]
    rep = make_user(db, role="admin")
    db.add(MailAccount(id=uuid.uuid4(), user_id=rep.id, email="rep@bmi.example", refresh_token_enc="x"))
    db.flush()
    sent = []
    monkeypatch.setattr(outlook, "send_mail", lambda db, acct, **kw: sent.append(kw))
    return identity_headers(rep), sent


@needs_pdf
def test_send_attaches_what_was_chosen(w, client, monkeypatch):
    h, sent = _sender(w, monkeypatch)
    d = _deal(w, client, h)
    draft = client.get(f"/api/sales/deals/{d['id']}/email-draft", headers=h).json()
    assert draft["pdf_available"] is True
    msg = {"to": ["ana@malta.example"], "subject": draft["subject"], "body": draft["body"]}
    for attach, types in (("pdf", ["application/pdf"]), ("word", [DOCX]), ("both", ["application/pdf", DOCX])):
        r = client.post(f"/api/sales/deals/{d['id']}/send", json={**msg, "attach": attach}, headers=h)
        assert r.status_code == 200, r.text
        assert [a[1] for a in sent[-1]["attachments"]] == types
    assert sent[-1]["attachments"][0][0].endswith(".pdf") and sent[-1]["attachments"][1][0].endswith(".docx")


def test_without_libreoffice_word_still_sends_and_pdf_says_why(w, client, monkeypatch):
    h, sent = _sender(w, monkeypatch)
    d = _deal(w, client, h)
    monkeypatch.setattr(dl, "pdf_available", lambda: False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert client.get(f"/api/sales/deals/{d['id']}/email-draft", headers=h).json()["pdf_available"] is False
    msg = {"to": ["ana@malta.example"], "subject": "Order confirmation", "body": "Hi"}
    r = client.post(f"/api/sales/deals/{d['id']}/send", json={**msg, "attach": "pdf"}, headers=h)
    assert r.status_code == 503 and "Send it as Word instead" in r.json()["detail"] and not sent
    assert client.post(f"/api/sales/deals/{d['id']}/send", json={**msg, "attach": "word"}, headers=h).status_code == 200
    assert client.get(f"/api/sales/deals/{d['id']}/document.pdf", headers=h).status_code == 503


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_vat_number_is_remembered_and_printed(w, client):
    """FIN-008: the client's VAT number is kept on the booking, printed, and filled in next time."""
    from app.models import Company

    db, h = w["db"], w["h"]
    co = Company(id=uuid.uuid4(), name="Visit Malta", source_db="manual", source_act_id=str(uuid.uuid4()))
    db.add(co)
    db.flush()
    st_id = str(w["titles"]["selling-travel"].id)
    ed = w["ed"]("selling-travel", "Dec issue", date.today() + timedelta(days=40))
    body = {"company_id": str(co.id), "client_name": "Visit Malta", "contact_name": "Ana", "contact_email": "ana@malta.example",
            "vat_number": "MT12345678", "rep_id": str(w["reps"]["SP"].id),
            "lines": [{"key": "page", "title_id": st_id, "description": "Full page advert", "unit_price": 2000,
                       "placements": [{"edition_id": str(ed.id)}]}]}
    d = client.post("/api/sales/deals", json=body, headers=h).json()
    assert d["vat_number"] == "MT12345678"
    doc = client.get(f"/api/sales/deals/{d['id']}/document", headers=h).json()
    assert doc["vat_number"] == "MT12345678"
    from docx import Document
    word = client.get(f"/api/sales/deals/{d['id']}/document.docx", headers=h).content
    text = "\n".join(c.text for t in Document(io.BytesIO(word)).tables for r in t.rows for c in r.cells)
    assert "Your VAT number: MT12345678" in text
    pre = client.get(f"/api/sales/deals/prefill?company_id={co.id}", headers=h).json()
    assert pre["vat_number"] == "MT12345678"
