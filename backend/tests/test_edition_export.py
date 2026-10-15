"""The edition's Excel download, in the order register's own layout - with every kind of item on it."""
import io
import uuid
from datetime import date

import openpyxl
from tests.test_orders import w  # noqa: F401 - fixture

from app.models import SalesOrder


def test_export_with_pencilled_and_every_other_status(w, client):
    db = w["db"]
    ed = w["ed"]("selling-travel", "AprMay2026", date(2026, 4, 1))
    for status in ("booked", "pencilled", "cancelled", "contra", "moved"):
        db.add(SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name=f"Client {status}", value_gbp=100, status=status, extra={}))
    db.flush()
    r = client.get(f"/api/sales/editions/{ed.id}/export", headers=w["h"])
    assert r.status_code == 200, r.text
    ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
    rows = {row[1]: row[12] for row in ws.iter_rows(min_row=8, values_only=True) if row and row[1]}
    assert rows["Client pencilled"] == "Pencilled" and rows["Client cancelled"] == "CANX" and rows["Client booked"] in ("", None)
