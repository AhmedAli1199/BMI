"""Key dates made by a brand's own deadline rules remember which rule made them.

Issues' extra key dates (sales_editions.milestones, [{"label", "date"}]) used to be matched to the brand's rules by
name, so renaming a rule left the old date behind and "Use the usual rules" added a second one. Each rule-made key
date now carries "rule": <the rule's key>. This tags the ones already there: a key date whose name matches one of
its brand's extra rules (not the three standard deadlines) gets that rule's key. Key dates people added stay as they are.

Revision ID: 0062
Revises: 0061
Create Date: 2026-10-18
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision: str = "0062"
down_revision: str | None = "0061"
branch_labels = None
depends_on = None

STANDARD = ("editorial", "advertising", "copy")
# Which brand each sales title belongs to, as in app/sales/brands.py when this was written.
BRAND_TITLES = {
    "obh": ("obh", "obh-web", "obh-awards", "obh-forum-asia"),
    "tbtm": ("tbtm", "tbtm-events"),
    "stm": ("selling-travel", "selling-travel-online", "selling-travel-supplements", "selling-travel-guides", "selling-travel-events",
            "stm-connect-events", "travel-for-every-body-awards", "selling-canada", "selling-australia", "visit-usa-planner", "visit-usa-online"),
}


def upgrade() -> None:
    conn = op.get_bind()
    rules = {b: {r.get("label"): r["key"] for r in (rs or []) if r.get("key") and r["key"] not in STANDARD and r.get("label")}
             for b, rs in conn.execute(sa.text("SELECT brand, deadline_rules FROM editorial_settings"))}
    for brand, slugs in BRAND_TITLES.items():
        by_label = rules.get(brand)
        if not by_label:
            continue
        rows = conn.execute(sa.text("SELECT e.id, e.milestones FROM sales_editions e JOIN sales_titles t ON t.id = e.title_id "
                                    "WHERE t.slug = ANY(:slugs) AND jsonb_array_length(e.milestones) > 0"), {"slugs": list(slugs)})
        for eid, ms in rows:
            new = [{**m, "rule": by_label[m.get("label")]} if not m.get("rule") and m.get("label") in by_label else m for m in ms]
            if new != ms:
                conn.execute(sa.text("UPDATE sales_editions SET milestones = CAST(:ms AS jsonb) WHERE id = :id"), {"ms": json.dumps(new), "id": eid})


def downgrade() -> None:
    op.execute("UPDATE sales_editions SET milestones = (SELECT coalesce(jsonb_agg(x.m - 'rule' ORDER BY x.i), '[]'::jsonb) "
               "FROM jsonb_array_elements(milestones) WITH ORDINALITY AS x(m, i)) WHERE jsonb_array_length(milestones) > 0")
