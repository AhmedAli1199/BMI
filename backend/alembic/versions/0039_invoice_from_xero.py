"""Bookings remember whether their invoiced amount came from Xero, and the amounts the
"keep in step with Xero" step (7-8 Oct 2026) wrote over figures from the order register
are put back.

Revision ID: 0039
Revises: 0038
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("invoice_from_xero", sa.Boolean(), nullable=False, server_default=sa.false()))
    conn = op.get_bind()
    # Links made by the matcher (automatic or chosen by a person) always took Xero's figures.
    conn.execute(sa.text("UPDATE sales_orders SET invoice_from_xero = true WHERE xero_link_source IN ('auto', 'confirmed')"))
    marks = conn.execute(sa.text(
        "SELECT entity_id, changed_at FROM field_changes WHERE entity_type = 'sales_order' AND field = 'xero_link' "
        "AND new_value LIKE 'Invoiced amount and date taken from Xero invoice%'")).all()
    now = datetime.now(timezone.utc)
    for entity_id, at in marks:
        rows = conn.execute(sa.text(
            "SELECT field, old_value, new_value FROM field_changes WHERE entity_type = 'sales_order' AND entity_id = :e "
            "AND field IN ('invoice_value_gbp', 'invoiced_on') AND changed_at BETWEEN :a AND :b"),
            {"e": entity_id, "a": at - timedelta(seconds=2), "b": at + timedelta(seconds=2)}).all()
        for field, old, new in rows:
            cur = conn.execute(sa.text(f"SELECT {field}::text FROM sales_orders WHERE id = :e"), {"e": entity_id}).scalar()
            same = cur == new or (cur is not None and new is not None and field == "invoice_value_gbp" and abs(float(cur) - float(new)) < 0.005)
            if not same:
                continue  # someone changed it since - leave their value
            conn.execute(sa.text(f"UPDATE sales_orders SET {field} = :v WHERE id = :e"),
                         {"v": None if old in (None, "None", "") else old, "e": entity_id})
            conn.execute(sa.text(
                "INSERT INTO field_changes (id, entity_type, entity_id, field, old_value, new_value, changed_at) "
                "VALUES (:id, 'sales_order', :e, :f, :o, :n, :t)"),
                {"id": str(uuid.uuid4()), "e": entity_id, "f": field, "o": new, "n": old, "t": now})
        conn.execute(sa.text(
            "INSERT INTO field_changes (id, entity_type, entity_id, field, old_value, new_value, changed_at) "
            "VALUES (:id, 'sales_order', :e, 'xero_link', NULL, :n, :t)"),
            {"id": str(uuid.uuid4()), "e": entity_id, "n": "Invoiced amount put back to the order register's figure", "t": now})


def downgrade() -> None:
    op.drop_column("sales_orders", "invoice_from_xero")
