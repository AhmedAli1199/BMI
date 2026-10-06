"""Reading invoice numbers the way people write them.

Staff typed invoice numbers into the sheets by hand, so the same number shows
up as "INV-0309", "inv 0309", "Inv0309", "INV 309", "invoice no. 309" or
just "309". Xero has its own spelling. All of those should be recognised as
the same invoice - but a *different* number must never match.

canonical() boils a number down to its meaning:
  - capital letters and digits only (so case, spaces, dashes, dots, slashes,
    underscores, # and : don't matter);
  - a spelled-out "no." / "number" / "nr" in front of the digits is dropped;
  - leading zeros inside the digits don't matter (INV-0309 = INV-309).
Two numbers match when their canonical forms are equal. canonical_sql() is
the same rule as a database expression - tests check the two agree.

When only the digits were typed ("309") or only the digits are in Xero, the
digits alone match - but only if exactly one invoice ends in those digits,
so a short number can't be mistaken for another invoice's.
"""
from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import XeroInvoice

_WORD_NO = re.compile(r"\b(?:NO|NUM|NUMBER|NR)\b\.?\s*(?=[0-9])")
_LEADING_ZEROS = re.compile(r"(^|[A-Z])0+([0-9])")

# The same two rules, written for Postgres (regexp_replace, flag 'g').
_SQL_WORD_NO = r"\m(NO|NUM|NUMBER|NR)\M\.?\s*(?=[0-9])"
_SQL_LEADING_ZEROS = r"(^|[A-Z])0+([0-9])"


def canonical(number: str | None) -> str | None:
    if not number or not number.strip():
        return None
    s = _WORD_NO.sub("", number.upper())
    s = re.sub(r"[^A-Z0-9]", "", s)
    s = _LEADING_ZEROS.sub(r"\1\2", s)
    return s or None


def canonical_sql(column):
    """The canonical() rule as an SQL expression over a text column (NULL stays NULL)."""
    s = func.regexp_replace(func.upper(column), _SQL_WORD_NO, "", "g")
    s = func.regexp_replace(s, "[^A-Z0-9]", "", "g")
    s = func.regexp_replace(s, _SQL_LEADING_ZEROS, r"\1\2", "g")
    return func.nullif(s, "")


def tail_digits(key: str | None) -> str | None:
    m = re.search(r"([0-9]+)$", key or "")
    return m.group(1) if m else None


def find_invoice(db: Session, number: str | None) -> XeroInvoice | None:
    """The Xero invoice this typed number means, or None. Exact canonical
    match first; then the digits-only fallback described above."""
    key = canonical(number)
    if not key:
        return None
    exact = db.scalars(select(XeroInvoice).where(XeroInvoice.number_key == key)
                       .order_by(XeroInvoice.updated_at_xero.desc().nulls_last())).first()
    if exact:
        return exact
    live = XeroInvoice.status.notin_(("VOIDED", "DELETED", "DRAFT"))
    if key.isdigit():
        # "309" typed; Xero has "INV-309" (letters, then exactly these digits)
        hits = db.scalars(select(XeroInvoice).where(live, XeroInvoice.number_key.op("~")(f"^[A-Z]*{key}$"))).all()
    else:
        tail = tail_digits(key)
        # "INV 309" typed; Xero has just "309"
        hits = db.scalars(select(XeroInvoice).where(live, XeroInvoice.number_key == tail)).all() if tail else []
    return hits[0] if len(hits) == 1 else None
