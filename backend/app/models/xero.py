"""Xero (accounting) - read-only. BMI's sales invoices are copied in so the
order register can show, per booking, whether its invoice has actually
been paid (SALES-026: booked vs invoiced vs paid).

XeroConnection: the one connected Xero organisation and its (encrypted)
OAuth tokens. XeroInvoice: one row per sales invoice (ACCREC), keyed on
Xero's own id and matched to SalesOrder.invoice_number by number."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class XeroConnection(Base, UUIDPk):
    __tablename__ = "xero_connections"

    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_name: Mapped[str | None] = mapped_column(String(255))
    refresh_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Next sync asks Xero only for invoices changed since this (If-Modified-Since).
    synced_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class XeroInvoice(Base, UUIDPk):
    __tablename__ = "xero_invoices"

    xero_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Upper-cased, spaces removed - what SalesOrder.invoice_number is matched on.
    number_key: Mapped[str | None] = mapped_column(String(60), index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(60))
    contact_name: Mapped[str | None] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(255))
    # What the invoice lines say they're for ("One Table at the London event", "Page within OBH 94"),
    # joined with " | " - the strongest clue to which booking an invoice belongs to.
    line_text: Mapped[str | None] = mapped_column(Text)
    # Xero's rate for a foreign-currency invoice (units of that currency per £1), to compare with a £ booking.
    currency_rate: Mapped[float | None] = mapped_column(Numeric(14, 6))
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # DRAFT|SUBMITTED|AUTHORISED|PAID|VOIDED|DELETED
    currency: Mapped[str | None] = mapped_column(String(3))
    issued_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date)
    paid_on: Mapped[date | None] = mapped_column(Date)
    sub_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    total_tax: Mapped[float | None] = mapped_column(Numeric(12, 2))
    total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    amount_paid: Mapped[float | None] = mapped_column(Numeric(12, 2))
    amount_due: Mapped[float | None] = mapped_column(Numeric(12, 2))
    amount_credited: Mapped[float | None] = mapped_column(Numeric(12, 2))
    updated_at_xero: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
