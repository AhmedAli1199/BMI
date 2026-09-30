"""Imports BMI's SOR workbooks into the Sales Order Register, then links
clients to CRM companies (exact matches linked, likely matches queued for
review). Prints a per-edition check of imported total vs. the sheet's own
"Cumulative value" figure.

The folder is the unzipped SOR.zip - one sub-folder per year:
    SOR/2023/*.xls, SOR/2024/..., SOR/2026/...

Usage (run against whichever DATABASE_URL is currently set):
    python -m scripts.import_sor /path/to/SOR            # first import
    python -m scripts.import_sor /path/to/SOR --replace  # wipe imported editions and reimport
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal  # noqa: E402
from app.sales.matching import match_clients  # noqa: E402
from app.sales.sor_import import import_sor  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--show-all", action="store_true", help="print every edition's check, not only mismatches")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = import_sor(db, args.folder, replace=args.replace)
        linked, queued = match_clients(db)
        db.commit()
    finally:
        db.close()

    print(f"Imported {report.orders} bookings in {report.editions} editions from {report.files} workbooks "
          f"({report.warnings} bookings flagged for a check).")
    print(f"Clients: {linked} bookings linked to CRM companies, {queued} likely matches queued for review.")
    for skipped in report.skipped_files:
        print(f"  skipped {skipped}")
    mismatches = 0
    for title, year, edition, imported, sheet_total in report.checks:
        ok = sheet_total is None or abs(imported - sheet_total) < 1
        mismatches += not ok
        if args.show_all or not ok:
            flag = "OK " if ok else "DIFF"
            st = "n/a" if sheet_total is None else f"£{sheet_total:,.2f}"
            print(f"  {flag} {year} {title} / {edition}: imported £{imported:,.2f}, sheet says {st}")
    print(f"{len(report.checks) - mismatches} of {len(report.checks)} editions match their sheet total.")


if __name__ == "__main__":
    main()
