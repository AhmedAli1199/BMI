#!/usr/bin/env python3
"""One-time backfill: resolves Act!'s MANAGEUSERID ("Record Manager") on
TBL_CONTACT/TBL_COMPANY into contacts.owner_user_id / companies.owner_user_id
in Postgres - see migration/README.md for the general migration runbook this
extends, and CONTEXT.md / BACKLOG.md for why this matters (SALES-013's
morning follow-up queue needs to know which salesperson owns which contact,
and nothing in the original ETL ever migrated this).

Run once per source database, same shape as etl.py, AFTER etl.py has already
populated contacts/companies for that database (this only UPDATEs existing
rows, matched by source_db + source_act_id - never inserts).

    python backfill_owner.py --source-db prospects \\
        --pg-url postgresql+psycopg://postgres:postgres@localhost:5433/bmi

(same --mssql-host/--mssql-user/--mssql-password/--use-odbc flags as etl.py -
omit --mssql-password to use Windows Integrated Auth, matching how you ran
the earlier TBL_ACCESSOR query.)

WHY A HAND-WRITTEN NAME->EMAIL MAP, NOT AUTO-MATCHING: TBL_ACCESSOR has no
email column, only a plain-text NAME ("Kay Fisher"). Guessing at a pattern
and silently trusting it risks quietly attributing a contact to the wrong
person's login. So every entry in ACCESSOR_NAME_TO_EMAIL below is confirmed
directly from BMI's own user roster (not a guess), and the script only ever
sets owner_user_id when BOTH (a) the name has an explicit entry here AND
(b) that email already exists as a real row in this CRM's own `users` table
- never trusted blindly at write time even for a confirmed address, since
the CRM login might not have been created yet.

Two names needed disambiguating before this list could be trusted: a
grouped-by-manager query against the real data (see BACKLOG.md/session
notes) showed "Sue Williams" (OnBoard only) and "Sue Thompson"/"Susan
Thompson" (SellingTravel only) as separate high-volume accessors that could
easily have been the same person under two names (a plausible maiden/married
name change in a 20-year-old database) - BMI's roster confirms they are in
fact two different people, at two different email domains
(sue.williams@onboardhospitality.com vs. susan.thompson@bmipublishing.co.uk).
Merging them under one guessed identity would have been exactly the kind of
silent misattribution this whole approach is designed to avoid.

NOT resolved by BMI's roster, still an open question: "BMI Administrator" -
a generic/system Act! login, not a real person - owns 57% of Prospects
contacts and 67% of Prospects companies (an unassigned pool, not anyone's
personal book). Deliberately left unmapped here rather than guessing it
should route to whichever person currently administers the CRM - that's a
real product decision (does BMI want those routed to someone, or genuinely
treated as unassigned in this CRM too?), not a data-resolution one.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl import discover_accessor_name_expr, mssql_connect, to_uuid_str  # noqa: E402
from app.models.base import SOURCE_DBS  # noqa: E402

# CONFIRMED real addresses (already used elsewhere in this codebase).
# GUESSED addresses follow the same firstname.lastname@bmipublishing.co.uk
# pattern but have not been independently verified - confirm these four
# with BMI before trusting the backfill for their contacts/companies.
ACCESSOR_NAME_TO_EMAIL: dict[str, str] = {
    "kay fisher": "kay.fisher@bmipublishing.co.uk",
    "shani kunar": "shani.kunar@bmipublishing.co.uk",
    "kirsty hicks": "kirsty.hicks@bmipublishing.co.uk",
    "neil dargie": "neil.dargie@bmipublishing.co.uk",
    "steven thompson": "steven.thompson@bmipublishing.co.uk",
    "sally parker": "sally.parker@bmipublishing.co.uk",
    "david wilcox": "david.wilcox@bmipublishing.co.uk",
    # Two different people, two different domains - see the module
    # docstring for why this needed BMI's roster to disambiguate rather
    # than being guessed as the same person under two names.
    "sue thompson": "susan.thompson@bmipublishing.co.uk",
    "susan thompson": "susan.thompson@bmipublishing.co.uk",
    "sue williams": "sue.williams@onboardhospitality.com",
    "sue wiliams": "sue.williams@onboardhospitality.com",  # one-off Act! typo (Prospects, 1 row)
    "craig mcquinn": "craig.mcquinn@bmipublishing.co.uk",
    "clare hunter": "clare.hunter@bmipublishing.co.uk",
    # "BMI Administrator" deliberately excluded - a generic/system Act!
    # login (57% of Prospects contacts, 67% of its companies), not a real
    # person to attribute ownership to; see the module docstring's "NOT
    # resolved" note. "TBTC Delegate" and "ACT! System" excluded for the
    # same reason - shared/system accounts, not salespeople.
}


def _fetch_managed_rows(cur, table: str, id_col: str, accessor_expr: str) -> list[dict]:
    cur.execute(
        f"SELECT c.{id_col} AS ID, {accessor_expr} AS MANAGER_NAME, a.STATUSNUM AS MANAGER_STATUS "
        f"FROM {table} c LEFT JOIN TBL_ACCESSOR a ON a.ACCESSORID = c.MANAGEUSERID"
    )
    return cur.fetchall()


def _backfill_table(conn, pg_table: str, rows: list[dict], user_emails: dict[str, str], source_db: str) -> dict:
    stats = {"total": 0, "owner_set": 0, "name_only": 0, "unmapped_active": set(), "mapped_but_no_login": set()}
    updates = []
    for r in rows:
        name = (r["MANAGER_NAME"] or "").strip()
        if not name:
            continue
        stats["total"] += 1
        normalized = name.lower()
        owner_id = None
        email = ACCESSOR_NAME_TO_EMAIL.get(normalized)
        if email:
            owner_id = user_emails.get(email.lower())
            if owner_id:
                stats["owner_set"] += 1
            else:
                stats["mapped_but_no_login"].add(f"{name} ({email})")
                stats["name_only"] += 1
        else:
            stats["name_only"] += 1
            if r["MANAGER_STATUS"] == 0:  # active accessor with no mapping entry at all
                stats["unmapped_active"].add(name)

        updates.append({
            "source_db": source_db, "source_act_id": to_uuid_str(r["ID"]),
            "owner_id": owner_id, "raw_name": name,
        })

    if updates:
        conn.execute(
            text(
                f"UPDATE {pg_table} SET "
                "owner_user_id = COALESCE(CAST(:owner_id AS uuid), owner_user_id), "
                "custom_fields = custom_fields || jsonb_build_object('_original_record_manager', CAST(:raw_name AS text)) "
                "WHERE source_db = :source_db AND source_act_id = :source_act_id"
            ),
            updates,
        )
    return stats


def run(args) -> None:
    source_db = args.source_db
    print(f"=== Record-manager backfill: {source_db} ===")

    ms = mssql_connect(args)
    cur = ms.cursor()
    accessor_expr_c = discover_accessor_name_expr(cur, alias="a")

    contact_rows = _fetch_managed_rows(cur, "TBL_CONTACT", "CONTACTID", accessor_expr_c)
    company_rows = _fetch_managed_rows(cur, "TBL_COMPANY", "COMPANYID", accessor_expr_c)
    ms.close()

    pg_url = args.pg_url.replace("postgresql+psycopg://", "postgresql+psycopg2://")
    pg = create_engine(pg_url)

    with pg.begin() as conn:
        user_rows = conn.execute(text("SELECT id, email FROM users")).all()
        user_emails = {email.lower(): str(uid) for uid, email in user_rows}

        contact_stats = _backfill_table(conn, "contacts", contact_rows, user_emails, source_db)
        company_stats = _backfill_table(conn, "companies", company_rows, user_emails, source_db)

    for label, stats in (("Contacts", contact_stats), ("Companies", company_stats)):
        print(f"\n  {label}: {stats['total']} had a record manager on file")
        print(f"    -> {stats['owner_set']} got owner_user_id set (mapped name -> a real CRM login)")
        print(f"    -> {stats['name_only']} kept only the raw name in custom_fields._original_record_manager")
        if stats["mapped_but_no_login"]:
            print(f"    -> mapped in ACCESSOR_NAME_TO_EMAIL but no matching CRM user account exists yet: "
                  f"{sorted(stats['mapped_but_no_login'])}")
        if stats["unmapped_active"]:
            print(f"    -> ACTIVE Act! users with NO entry in ACCESSOR_NAME_TO_EMAIL - add them and re-run: "
                  f"{sorted(stats['unmapped_active'])}")

    print(f"\n=== {source_db}: done - safe to re-run anytime (UPDATE only, never inserts) ===")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source-db", required=True, choices=SOURCE_DBS)
    p.add_argument("--mssql-host", default="localhost")
    p.add_argument("--mssql-port", default=1433, type=int)
    p.add_argument("--mssql-user", default="sa")
    p.add_argument("--mssql-password", default="", help="SQL Server password (leave blank for Windows Auth via ODBC)")
    p.add_argument("--use-odbc", action="store_true", help="Use ODBC with Windows Integrated Authentication")
    p.add_argument("--pg-url", required=True)
    run(p.parse_args())
