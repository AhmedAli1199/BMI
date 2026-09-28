"""One command to refresh the Sales Order Register from BMI's SOR
spreadsheets - everything that used to be six manual steps:

  1. Brings the database schema up to date (alembic upgrade head).
  2. Downloads SOR.zip from Google Drive (or uses a local zip/folder).
  3. Unzips it to a temporary folder.
  4. Checks nobody has added or edited bookings in the app since the last
     import - those would be wiped by a re-import, so it stops unless
     you pass --force.
  5. Clears the unanswered "is this the same company?" review items from
     the previous import (they point at bookings about to be replaced).
  6. Re-imports every workbook, re-links clients to CRM companies, and
     prints the check against each sheet's own totals.

Steps 5-6 run in ONE database transaction: if anything fails, nothing
changes and the app keeps its current data.

Usage, from the backend folder (in the Dokploy container: `cd /app`):
    python -m scripts.refresh_sor
    python -m scripts.refresh_sor --drive-id <id>      # a different file on Drive
    python -m scripts.refresh_sor --source /path/SOR.zip   # or an unzipped SOR folder
    python -m scripts.refresh_sor --dry-run            # download + checks only, change nothing

The Drive file must be shared as "Anyone with the link".
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import func, select, text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import FieldChange, SalesEdition, SalesOrder  # noqa: E402
from app.sales.matching import MATCH_KIND, match_clients  # noqa: E402
from app.sales.sor_import import import_sor  # noqa: E402

# SOR.zip in BMI's shared Drive folder.
DEFAULT_DRIVE_ID = "1PaA2CzLegM-IR1ThqSo6_EgADgruJjj9"


def step(n: int, msg: str) -> None:
    print(f"\n[{n}/6] {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"\nSTOPPED: {msg}\nNothing in the app was changed.", file=sys.stderr)
    sys.exit(1)


def upgrade_schema() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")


def download(drive_id: str, dest: Path) -> None:
    url = f"https://drive.usercontent.google.com/download?id={drive_id}&export=download&confirm=t"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (BMI SOR refresh)"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)
    if not zipfile.is_zipfile(dest):
        fail("Google Drive didn't return a zip file. Make sure SOR.zip is shared as "
             "'Anyone with the link' (or pass --source with a local copy).")
    print(f"  downloaded {dest.stat().st_size / 1_048_576:.1f} MB")


def find_sor_root(folder: Path) -> Path:
    """The folder holding the year sub-folders (2023, 2024...), wherever
    the zip put it (SOR/2026/... or 2026/... at the top)."""
    for candidate in [folder, *sorted(p for p in folder.rglob("*") if p.is_dir())]:
        if "__MACOSX" in candidate.parts:
            continue
        if any(c.is_dir() and c.name.isdigit() and len(c.name) == 4 for c in candidate.iterdir()):
            return candidate
    fail(f"No year folders (2023, 2024, ...) found inside {folder}.")
    raise AssertionError


def app_edits(db) -> tuple[int, int]:
    """(bookings added in the app to imported editions, edits made in the
    app to imported bookings) - both lost on a re-import."""
    imported_eds = select(SalesEdition.id).where(SalesEdition.source_file.isnot(None))
    added = db.scalar(select(func.count()).select_from(SalesOrder).where(
        SalesOrder.edition_id.in_(imported_eds), SalesOrder.source_file.is_(None))) or 0
    imported_orders = select(SalesOrder.id).where(SalesOrder.source_file.isnot(None))
    edited = db.scalar(select(func.count(func.distinct(FieldChange.entity_id))).where(
        FieldChange.entity_type == "sales_order", FieldChange.entity_id.in_(imported_orders))) or 0
    return added, edited


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the Sales Order Register from the SOR spreadsheets.")
    parser.add_argument("--drive-id", default=DEFAULT_DRIVE_ID, help="Google Drive file id of SOR.zip")
    parser.add_argument("--source", type=Path, help="a local SOR.zip or unzipped SOR folder instead of downloading")
    parser.add_argument("--force", action="store_true", help="re-import even if bookings were added/edited in the app (they will be lost)")
    parser.add_argument("--dry-run", action="store_true", help="download and check only; change nothing")
    parser.add_argument("--skip-migrations", action="store_true")
    args = parser.parse_args()

    step(1, "Updating the database schema")
    if args.skip_migrations or args.dry_run:
        print("  skipped")
    else:
        upgrade_schema()
        print("  up to date")

    work = Path(tempfile.mkdtemp(prefix="sor-refresh-"))
    try:
        step(2, "Getting the SOR spreadsheets")
        if args.source and args.source.is_dir():
            folder = args.source
            print(f"  using folder {folder}")
        else:
            zip_path = args.source if args.source else work / "SOR.zip"
            if not args.source:
                download(args.drive_id, zip_path)
            elif not zipfile.is_zipfile(zip_path):
                fail(f"{zip_path} is not a zip file.")
            step(3, "Unzipping")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(work / "unzipped")
            folder = work / "unzipped"
        root = find_sor_root(folder)
        years = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name.isdigit())
        files = sum(1 for p in root.rglob("*.xls*") if not p.name.startswith("."))
        print(f"  found {files} workbooks for {', '.join(years)}")

        db = SessionLocal()
        try:
            step(4, "Checking for work done in the app since the last import")
            already_imported = db.scalar(select(func.count()).select_from(SalesEdition).where(SalesEdition.source_file.isnot(None)))
            added, edited = app_edits(db)
            print(f"  {added} bookings added in the app to imported editions, {edited} imported bookings edited in the app")
            if (added or edited) and not args.force:
                fail("Re-importing would throw that work away. Check those bookings first, then run again with "
                     "--force if they can go. (Editions created in the app, and their bookings, are never touched.)")
            if args.dry_run:
                print("\nDry run - stopping before any change.")
                return

            step(5, "Clearing unanswered client-match questions from the previous import")
            n = db.execute(text("DELETE FROM review_queue WHERE kind = :k AND status = 'pending'"), {"k": MATCH_KIND}).rowcount
            print(f"  {n} removed")

            step(6, "Importing and linking clients")
            report = import_sor(db, root, replace=bool(already_imported))
            linked, queued = match_clients(db)
            db.commit()
        except SystemExit:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            fail(f"import failed ({type(exc).__name__}: {exc}).")
        finally:
            db.close()

        print(f"\nDone. Imported {report.orders} bookings in {report.editions} editions from {report.files} workbooks "
              f"({report.warnings} flagged for a check).")
        print(f"Clients: {linked} bookings linked to CRM companies, {queued} likely matches queued for review.")
        for skipped in report.skipped_files:
            print(f"  skipped {skipped}")
        diffs = [c for c in report.checks if c[4] is not None and abs(c[3] - c[4]) >= 1]
        for title, year, edition, imported, sheet_total in diffs:
            print(f"  DIFF {year} {title} / {edition}: imported £{imported:,.2f}, sheet says £{sheet_total:,.2f}")
        print(f"{len(report.checks) - len(diffs)} of {len(report.checks)} editions match their sheet total.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    os.chdir(BACKEND)
    main()
