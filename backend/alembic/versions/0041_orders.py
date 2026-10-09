"""Multi-item orders (order confirmations): sales_deals, deal_settings, item fields on bookings, and the
"pencilled" booking status (held for a client, not yet confirmed - not counted in sales figures).

Revision ID: 0041
Revises: 0040
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)

COMPANY = "BMI PUBLISHING LTD\n501 The Residence\nNo.1 Alexandra Terrace\nGuildford\nGU1 3DA\nUnited Kingdom"
FOOTER = ("T +44 (020) 8649 7233; Email accounts@bmipublishing.co.uk\nW www.bmipublishing.co.uk\n"
          "BMI Publishing Ltd registered in England and Wales no. 2590839. VAT reg. no. GB 574205546")
TERMS = "Your booking is subject to our Terms and Conditions. Please read them carefully at https://www.bmipublishing.co.uk/tandc.pdf"
SPECS = ("Advertisement rates are based on digital files supplied. We require files as composite CMYK PDF files created using Adobe "
         "Acrobat Distiller 4 or above. Please note double page spreads to be saved as individual pages. All files should contain "
         "images in high resolution, CMYK format with all fonts embedded at postscript stage. Files should not contain any True Type "
         "or Multiple Monster fonts, original JPEG's or copydot scan elements. Trapping must already be applied to all PDF files whilst "
         "all pantone and RGB images must be converted to CMYK prior to postscript stage. Please save PDF's as advertiser, publication "
         "and issue (eg. Advertisername_STM_Oct20). A full specification can be emailed on request. Please contact "
         "design@bmipublishing.co.uk. A colour proof created from the finished PDF should be supplied with files.")


def upgrade() -> None:
    op.create_table(
        "sales_deals",
        sa.Column("id", U, primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True, index=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="pencilled", index=True),
        sa.Column("document", sa.String(12), nullable=False, server_default="confirmation"),
        sa.Column("company_id", U, sa.ForeignKey("companies.id", ondelete="SET NULL"), index=True),
        sa.Column("client_name", sa.String(256), nullable=False),
        sa.Column("contact_id", U, sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("contact_name", sa.String(200)),
        sa.Column("contact_email", sa.String(320)),
        sa.Column("confirmation_address", sa.Text()),
        sa.Column("invoice_to", sa.Text()),
        sa.Column("invoice_email", sa.String(320)),
        sa.Column("po_number", sa.String(80)),
        sa.Column("agency_name", sa.String(200)),
        sa.Column("agency_pct", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("rep_id", U, sa.ForeignKey("sales_reps.id"), index=True),
        sa.Column("split", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("booked_on", sa.Date(), nullable=False),
        sa.Column("title_id", U, sa.ForeignKey("sales_titles.id", ondelete="SET NULL")),
        sa.Column("publication_label", sa.String(200)),
        sa.Column("insertions_label", sa.String(300)),
        sa.Column("pricing", sa.String(8), nullable=False, server_default="items"),
        sa.Column("package_price_gbp", sa.Numeric(12, 2)),
        sa.Column("package_label", sa.String(200)),
        sa.Column("package_split", sa.String(10), nullable=False, server_default="rate_card"),
        sa.Column("discount_pct", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("lines", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("total_gbp", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("invoice_plan", sa.String(14), nullable=False, server_default="on_publication"),
        sa.Column("special_instructions", sa.Text()),
        sa.Column("copy_instructions", sa.Text()),
        sa.Column("production_contact", sa.String(200)),
        sa.Column("show_artwork_specs", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text()),
        sa.Column("proposal_id", U, sa.ForeignKey("proposals.id", ondelete="SET NULL")),
        sa.Column("rebooked_from_id", U, sa.ForeignKey("sales_deals.id", ondelete="SET NULL")),
        sa.Column("created_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("confirmed_at", TS),
        sa.Column("sent_at", TS),
        sa.Column("sent_to", sa.String(400)),
        sa.Column("cancelled_reason", sa.String(300)),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "deal_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="2437"),
        sa.Column("company_block", sa.Text(), nullable=False, server_default=""),
        sa.Column("footer", sa.Text(), nullable=False, server_default=""),
        sa.Column("terms", sa.Text(), nullable=False, server_default=""),
        sa.Column("artwork_specs", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", TS),
    )
    op.get_bind().execute(sa.text("INSERT INTO deal_settings (id, next_number, company_block, footer, terms, artwork_specs) "
                                  "VALUES (1, 2437, :c, :f, :t, :s)"), {"c": COMPANY, "f": FOOTER, "t": TERMS, "s": SPECS})
    for col in (sa.Column("deal_id", U, sa.ForeignKey("sales_deals.id", ondelete="SET NULL")),
                sa.Column("deal_line", sa.String(40)), sa.Column("description", sa.String(300)), sa.Column("quantity", sa.Integer()),
                sa.Column("unit_price_gbp", sa.Numeric(12, 2)), sa.Column("list_price_gbp", sa.Numeric(12, 2)),
                sa.Column("added_value", sa.Boolean(), nullable=False, server_default=sa.false()),
                sa.Column("item_date", sa.Date()), sa.Column("copy_due", sa.Date())):
        op.add_column("sales_orders", col)
    op.create_index("ix_sales_orders_deal_id", "sales_orders", ["deal_id"])
    op.create_index("ix_sales_orders_item_date", "sales_orders", ["item_date"])
    op.drop_constraint("ck_sales_orders_status", "sales_orders", type_="check")
    op.create_check_constraint("ck_sales_orders_status", "sales_orders", "status IN ('booked', 'cancelled', 'contra', 'moved', 'pencilled')")


def downgrade() -> None:
    op.execute("UPDATE sales_orders SET status = 'cancelled' WHERE status = 'pencilled'")
    op.drop_constraint("ck_sales_orders_status", "sales_orders", type_="check")
    op.create_check_constraint("ck_sales_orders_status", "sales_orders", "status IN ('booked', 'cancelled', 'contra', 'moved')")
    op.drop_index("ix_sales_orders_item_date", "sales_orders")
    op.drop_index("ix_sales_orders_deal_id", "sales_orders")
    for c in ("copy_due", "item_date", "added_value", "list_price_gbp", "unit_price_gbp", "quantity", "description", "deal_line", "deal_id"):
        op.drop_column("sales_orders", c)
    op.drop_table("deal_settings")
    op.drop_table("sales_deals")
