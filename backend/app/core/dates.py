"""One rule for dates that can't be right.

BMI's records start in the 2000s, so a date before 2000 is a typing or spreadsheet slip - usually an Excel cell
formatted as a date that holds a small number (3 shows as "03/01/1900"), or a two-digit year read as 19xx.
The importer leaves such a date blank and flags the row to check, and the app refuses one when it's typed, so
nothing (new-business checks, invoice matching, renewals, commission) ever reasons from 1900.
"""
from __future__ import annotations

from datetime import date

from fastapi import HTTPException

EARLIEST = date(2000, 1, 1)


def plausible(d: date | None) -> bool:
    return d is None or d >= EARLIEST


def check(**dates: date | None) -> None:
    """Raises a plain 422 for the first date before 2000. Keyword names become the words in the message
    (booking_date -> "booking date")."""
    for name, d in dates.items():
        if not plausible(d):
            raise HTTPException(422, f"The {name.replace('_', ' ')} ({d.day} {d:%b %Y}) can't be right - check the year.")
