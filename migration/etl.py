#!/usr/bin/env python3
"""Migrate ONE restored Act! SQL Server database into the target Postgres
CRM schema. Run once per source database (onboard / prospects /
sellingtravel) - see migration/README.md for the full runbook.

This script is intentionally simple and linear: extract each entity type
with one SQL query against the source, transform it in Python, bulk-insert
into Postgres, print a summary. No ORM sessions, no clever abstraction -
easy to read top to bottom and easy to audit against the row counts in
docs/act-schema/*.md.

Usage:
    python etl.py --source-db onboard \\
        --mssql-host localhost --mssql-port 1433 --mssql-password '...' \\
        --pg-url postgresql://postgres:postgres@localhost:5432/bmi

Safe to re-run: every insert is keyed on (source_db, source_act_id) with
ON CONFLICT DO NOTHING, so re-running after a partial failure only adds
what's missing, never duplicates.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import pymssql
import sqlalchemy as sa
from sqlalchemy import create_engine

# So `from app.models import ...` resolves to backend/app regardless of the
# current working directory this script is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models.base import SOURCE_DBS  # noqa: E402
from custom_fields import CUSTOM_FIELD_MAPS, decode_custom_fields  # noqa: E402
from app.models.history import HISTORY_TYPES_KEPT  # noqa: E402
from app.models import (  # noqa: E402
    Activity, Address, Company, Contact, Email, Group, GroupMembership,
    HistoryEntry, Note, Opportunity, Phone,
)

# Maps our --source-db key to the database name it was restored under in
# SQL Server. Matches the RESTORE DATABASE statements used during schema
# exploration (docs/act-schema/*.md) - change here, not per-query, if that
# ever differs.
MSSQL_DB_NAMES = {"onboard": "OnBoard", "prospects": "Prospects", "sellingtravel": "SellingTravel"}

CUST_CONTACT_COLS = {  # union across all 3 DBs' TBL_CONTACT custom columns
    "USER1", "USER2", "USER3", "USER4", "USER5", "USER6", "USER7", "USER8", "USER9", "USER10",
}
CUST_COMPANY_COLS: set[str] = set()
CUST_GROUP_COLS: set[str] = set()


def mssql_connect(args) -> pymssql.Connection:
    return pymssql.connect(
        server=args.mssql_host, port=str(args.mssql_port),
        user=args.mssql_user, password=args.mssql_password,
        database=MSSQL_DB_NAMES[args.source_db], as_dict=True,
    )


def discover_custom_columns(cur, table: str) -> list[str]:
    """CUST_*/USERn columns actually present on this table in this
    database - discovered live rather than hardcoded, since the exact set
    differs per source_db (see docs/act-schema/*.md). The *meaning* of each
    one comes from custom_fields.py, not from here.
    """
    cur.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = %s AND (COLUMN_NAME LIKE 'CUST_%%' OR COLUMN_NAME LIKE 'USER%%') "
        "ORDER BY ORDINAL_POSITION",
        (table,),
    )
    return [r["COLUMN_NAME"] for r in cur.fetchall()]


def to_uuid_str(v) -> str | None:
    if v is None:
        return None
    return str(v).strip("{}").lower()


class IdMap:
    """act_id (lowercased string) -> our new uuid.UUID, per entity kind."""

    def __init__(self):
        self._maps: dict[str, dict[str, uuid.UUID]] = {}

    def get_or_create(self, kind: str, act_id: str | None) -> uuid.UUID | None:
        if act_id is None:
            return None
        act_id = to_uuid_str(act_id)
        m = self._maps.setdefault(kind, {})
        if act_id not in m:
            m[act_id] = uuid.uuid4()
        return m[act_id]

    def get(self, kind: str, act_id: str | None) -> uuid.UUID | None:
        if act_id is None:
            return None
        return self._maps.get(kind, {}).get(to_uuid_str(act_id))


def bulk_upsert(conn, table, rows: list[dict], constraint: str, label: str):
    if not rows:
        print(f"  {label}: 0 rows (nothing to insert)")
        return 0
    stmt = sa.dialects.postgresql.insert(table).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint=constraint).returning(table.c.id)
    # .rowcount is unreliable for ON CONFLICT DO NOTHING with some drivers -
    # count the RETURNING rows instead, which always reflects what actually landed.
    inserted = len(conn.execute(stmt).fetchall())
    print(f"  {label}: {len(rows)} extracted, {inserted} inserted "
          f"({len(rows) - inserted} already present / skipped)")
    return inserted


def run(args):
    source_db = args.source_db
    field_maps = CUSTOM_FIELD_MAPS[source_db]

    print(f"=== ETL: {source_db} -> Postgres ===")
    ms = mssql_connect(args)
    cur = ms.cursor()

    pg = create_engine(args.pg_url)
    ids = IdMap()

    contact_cust_cols = discover_custom_columns(cur, "TBL_CONTACT")
    company_cust_cols = discover_custom_columns(cur, "TBL_COMPANY")
    group_cust_cols = discover_custom_columns(cur, "TBL_GROUP")

    with pg.begin() as conn:
        # ---- Companies (parents before children: order by HIERLEVEL) ----
        cur.execute(
            "SELECT COMPANYID, NAME, DESCRIPTION, CATEGORY, REFERREDBY, TICKERSYMBOL, "
            "NUMEMPLOYEES, INDUSTRY, SICCODE, REVENUE, TERRITORY, REGION, DIVISION, "
            "WEBADDRESS, ISPRIVATE, PARENTCOMPANYID, CREATEDATE, EDITDATE, "
            + ", ".join(f"[{c}]" for c in company_cust_cols) + (", " if company_cust_cols else "") +
            "HIERLEVEL FROM TBL_COMPANY ORDER BY HIERLEVEL ASC"
        )
        company_rows = cur.fetchall()
        for r in company_rows:
            ids.get_or_create("company", r["COMPANYID"])

        rows = []
        for r in company_rows:
            cust_raw = {c: r[c] for c in company_cust_cols}
            rows.append({
                "id": ids.get("company", r["COMPANYID"]),
                "source_db": source_db, "source_act_id": to_uuid_str(r["COMPANYID"]),
                "name": r["NAME"] or "(unnamed)", "description": r["DESCRIPTION"],
                "category": r["CATEGORY"], "referred_by": r["REFERREDBY"],
                "industry": r["INDUSTRY"], "territory": r["TERRITORY"],
                "region": r["REGION"], "division": r["DIVISION"],
                "num_employees": r["NUMEMPLOYEES"], "revenue": r["REVENUE"],
                "website": r["WEBADDRESS"], "is_private": bool(r["ISPRIVATE"]),
                "parent_company_id": ids.get("company", r["PARENTCOMPANYID"]),
                "custom_fields": decode_custom_fields(cust_raw, field_maps["company"]),
                "act_created_at": r["CREATEDATE"], "act_edited_at": r["EDITDATE"],
            })
        bulk_upsert(conn, Company.__table__, rows, "uq_companies_source", "companies")

        # ---- Groups ----
        cur.execute(
            "SELECT GROUPID, NAME, DESCRIPTION, HIERLEVEL, HIERPATH, PARENTGROUPID, "
            + ", ".join(f"[{c}]" for c in group_cust_cols) + (", " if group_cust_cols else "") +
            "GROUPID AS _ FROM TBL_GROUP ORDER BY HIERLEVEL ASC"
        )
        group_rows = cur.fetchall()
        for r in group_rows:
            ids.get_or_create("group", r["GROUPID"])
        rows = []
        for r in group_rows:
            cust_raw = {c: r[c] for c in group_cust_cols}
            rows.append({
                "id": ids.get("group", r["GROUPID"]),
                "source_db": source_db, "source_act_id": to_uuid_str(r["GROUPID"]),
                "name": r["NAME"] or "(unnamed)", "description": r["DESCRIPTION"],
                "hier_level": r["HIERLEVEL"], "hier_path": r["HIERPATH"],
                "parent_group_id": ids.get("group", r["PARENTGROUPID"]),
                "custom_fields": decode_custom_fields(cust_raw, field_maps["group"]),
            })
        bulk_upsert(conn, Group.__table__, rows, "uq_groups_source", "groups")

        # ---- Contacts ----
        cur.execute(
            "SELECT CONTACTID, COMPANYID, FIRSTNAME, MIDDLENAME, LASTNAME, FULLNAME, "
            "NAMEPREFIX, NAMESUFFIX, SALUTATION, JOBTITLE, DEPARTMENT, CATEGORY, "
            "REFERREDBY, BIRTHDATE, ISPRIVATE, LASTMEETDATE, LASTREACHDATE, "
            "LASTATTEMPTDATE, LASTLETTERDATE, CREATEDATE, EDITDATE, "
            + ", ".join(f"[{c}]" for c in contact_cust_cols) +
            " FROM TBL_CONTACT"
        )
        contact_rows = cur.fetchall()
        for r in contact_rows:
            ids.get_or_create("contact", r["CONTACTID"])
        rows = []
        for r in contact_rows:
            cust_raw = {c: r[c] for c in contact_cust_cols}
            company_id = ids.get("company", r["COMPANYID"])
            rows.append({
                "id": ids.get("contact", r["CONTACTID"]),
                "source_db": source_db, "source_act_id": to_uuid_str(r["CONTACTID"]),
                "company_id": company_id,
                "first_name": r["FIRSTNAME"], "middle_name": r["MIDDLENAME"],
                "last_name": r["LASTNAME"], "full_name": r["FULLNAME"],
                "name_prefix": r["NAMEPREFIX"], "name_suffix": r["NAMESUFFIX"],
                "salutation": r["SALUTATION"], "job_title": r["JOBTITLE"],
                "department": r["DEPARTMENT"], "category": r["CATEGORY"],
                "referred_by": r["REFERREDBY"], "birthdate": r["BIRTHDATE"],
                "is_private": bool(r["ISPRIVATE"]),
                "last_meet_date": r["LASTMEETDATE"], "last_reach_date": r["LASTREACHDATE"],
                "last_attempt_date": r["LASTATTEMPTDATE"], "last_letter_date": r["LASTLETTERDATE"],
                "custom_fields": decode_custom_fields(cust_raw, field_maps["contact"]),
                "act_created_at": r["CREATEDATE"], "act_edited_at": r["EDITDATE"],
            })
        bulk_upsert(conn, Contact.__table__, rows, "uq_contacts_source", "contacts")

        # ---- Group memberships ----
        cur.execute("SELECT GROUPID, CONTACTID FROM TBL_GROUP_CONTACT")
        rows = []
        for r in cur.fetchall():
            gid, cid = ids.get("group", r["GROUPID"]), ids.get("contact", r["CONTACTID"])
            if gid and cid:
                rows.append({"id": uuid.uuid4(), "group_id": gid, "contact_id": cid})
        bulk_upsert(conn, GroupMembership.__table__, rows, "uq_group_memberships", "group_memberships")

        # ---- Addresses / Phones / Emails (contact + company only) ----
        _migrate_channel(cur, conn, ids, source_db, "TBL_ADDRESS", Address.__table__,
                          "uq_addresses_source", "addresses",
                          extra_cols="LINE1, LINE2, LINE3, CITY, STATE, POSTALCODE, COUNTRYNAME, LATITUDE, LONGITUDE",
                          row_to_extra=lambda r: {
                              "line1": r["LINE1"], "line2": r["LINE2"], "line3": r["LINE3"],
                              "city": r["CITY"], "state": r["STATE"], "postal_code": r["POSTALCODE"],
                              "country": r["COUNTRYNAME"], "latitude": r["LATITUDE"], "longitude": r["LONGITUDE"],
                          }, id_col="ADDRESSID")
        _migrate_channel(cur, conn, ids, source_db, "TBL_PHONE", Phone.__table__,
                          "uq_phones_source", "phones",
                          extra_cols="NUMBERDISPLAY, COUNTRYCODE",
                          row_to_extra=lambda r: {"number": r["NUMBERDISPLAY"], "country_code": r["COUNTRYCODE"]},
                          id_col="PHONEID")
        _migrate_channel(cur, conn, ids, source_db, "TBL_EMAIL", Email.__table__,
                          "uq_emails_source", "emails",
                          extra_cols="ADDRESS",
                          row_to_extra=lambda r: {"address": r["ADDRESS"]},
                          id_col="EMAILID")

        # ---- Notes (flattened via junction tables) ----
        _migrate_notes(cur, conn, ids, source_db)

        # ---- History (flattened + filtered) ----
        _migrate_history(cur, conn, ids, source_db)

        # ---- Activities (kept, flat - see activity.py docstring) ----
        cur.execute(
            "SELECT a.ACTIVITYID, a.REGARDING, a.DETAILS, a.LOCATION, a.STARTTIME, a.ENDTIME, "
            "a.ISTIMELESS, t.NAME AS TYPENAME, ac.ACCESSOR_ACTIVITY_CLEAREDID "
            "FROM TBL_ACTIVITY a "
            "LEFT JOIN TBL_ACTIVITYTYPE t ON t.ACTIVITYTYPEID = a.ACTIVITYTYPEID "
            "LEFT JOIN TBL_ACCESSOR_ACTIVITY_CLEARED ac ON ac.ACTIVITYID = a.ACTIVITYID"
        )
        rows = []
        for r in cur.fetchall():
            rows.append({
                "id": uuid.uuid4(), "source_db": source_db, "source_act_id": to_uuid_str(r["ACTIVITYID"]),
                "contact_id": None, "company_id": None,  # no reliable contact link in Act!'s schema - see README
                "activity_type": r["TYPENAME"], "subject": r["REGARDING"], "details": r["DETAILS"],
                "location": r["LOCATION"], "start_at": r["STARTTIME"], "end_at": r["ENDTIME"],
                "is_timeless": bool(r["ISTIMELESS"]), "is_cleared": r["ACCESSOR_ACTIVITY_CLEAREDID"] is not None,
            })
        bulk_upsert(conn, Activity.__table__, rows, "uq_activities_source", "activities")

        # ---- Opportunities (kept, flat) ----
        cur.execute(
            "SELECT o.OPPORTUNITYID, o.NAME, o.STATUS, o.SOURCE, o.COMPETITOR, o.CLOSEREASON, "
            "o.TOTALEXTENDEDAMT, o.PROBABILITYPCT, o.OPENDATE, o.ESTIMATEDCLOSEDATE, o.ACTUALCLOSEDATE, "
            "co.CONTACTID, cmo.COMPANYID "
            "FROM TBL_OPPORTUNITY o "
            "LEFT JOIN TBL_CONTACT_OPPORTUNITY co ON co.OPPORTUNITYID = o.OPPORTUNITYID "
            "LEFT JOIN TBL_COMPANY_OPPORTUNITY cmo ON cmo.OPPORTUNITYID = o.OPPORTUNITYID"
        )
        rows, seen = [], set()
        for r in cur.fetchall():
            if r["OPPORTUNITYID"] in seen:  # a junction could in principle add duplicate rows; keep first
                continue
            seen.add(r["OPPORTUNITYID"])
            rows.append({
                "id": uuid.uuid4(), "source_db": source_db, "source_act_id": to_uuid_str(r["OPPORTUNITYID"]),
                "contact_id": ids.get("contact", r["CONTACTID"]), "company_id": ids.get("company", r["COMPANYID"]),
                "name": r["NAME"], "status": r["STATUS"], "source": r["SOURCE"],
                "competitor": r["COMPETITOR"], "close_reason": r["CLOSEREASON"],
                "total_amount": r["TOTALEXTENDEDAMT"], "probability_pct": r["PROBABILITYPCT"],
                "open_at": r["OPENDATE"], "estimated_close_at": r["ESTIMATEDCLOSEDATE"],
                "actual_close_at": r["ACTUALCLOSEDATE"],
            })
        bulk_upsert(conn, Opportunity.__table__, rows, "uq_opportunities_source", "opportunities")

    print(f"=== {source_db}: done ===")


def _migrate_channel(cur, conn, ids, source_db, table, sa_table, constraint, label, extra_cols, row_to_extra, id_col):
    extra_select = ", ".join(f"c.{col}" for col in extra_cols.split(", "))
    cur.execute(
        f"SELECT c.{id_col}, c.TYPEID, c.CONTACTID, c.COMPANYID, p.NAME AS TYPENAME, {extra_select} "
        f"FROM {table} c LEFT JOIN TBL_PICKLISTITEM p ON p.PICKLISTITEMID = c.TYPEID "
        f"WHERE c.CONTACTID IS NOT NULL OR c.COMPANYID IS NOT NULL"
    )
    rows = []
    for r in cur.fetchall():
        contact_id = ids.get("contact", r["CONTACTID"])
        company_id = ids.get("company", r["COMPANYID"])
        if not contact_id and not company_id:
            continue  # dangling reference to a contact/company we didn't migrate - skip, don't guess
        row = {
            "id": uuid.uuid4(), "source_db": source_db, "source_act_id": to_uuid_str(r[id_col]),
            "contact_id": contact_id, "company_id": company_id,
            "type_label": r["TYPENAME"], "is_primary": False,
        }
        row.update(row_to_extra(r))
        rows.append(row)
    bulk_upsert(conn, sa_table, rows, constraint, label)


def _migrate_notes(cur, conn, ids, source_db):
    cur.execute(
        "SELECT n.NOTEID, n.NOTETEXT, n.ISPRIVATE, n.CREATEDATE, nt.NAME AS TYPENAME, "
        "cn.CONTACTID, cmn.COMPANYID "
        "FROM TBL_NOTE n "
        "LEFT JOIN TBL_NOTETYPE nt ON nt.NOTETYPEID = n.NOTETYPEID "
        "LEFT JOIN TBL_CONTACT_NOTE cn ON cn.NOTEID = n.NOTEID "
        "LEFT JOIN TBL_COMPANY_NOTE cmn ON cmn.NOTEID = n.NOTEID"
    )
    rows, seen = [], set()
    for r in cur.fetchall():
        if r["NOTEID"] in seen:
            continue
        contact_id = ids.get("contact", r["CONTACTID"])
        company_id = ids.get("company", r["COMPANYID"])
        entity_type, entity_id = ("contact", contact_id) if contact_id else ("company", company_id) if company_id else (None, None)
        if not entity_id:
            continue
        seen.add(r["NOTEID"])
        rows.append({
            "id": uuid.uuid4(), "source_db": source_db, "source_act_id": to_uuid_str(r["NOTEID"]),
            "entity_type": entity_type, "entity_id": entity_id,
            "note_type": r["TYPENAME"], "body": r["NOTETEXT"], "is_private": bool(r["ISPRIVATE"]),
            "act_created_at": r["CREATEDATE"],
        })
    bulk_upsert(conn, Note.__table__, rows, "uq_notes_source", "notes")


def _migrate_history(cur, conn, ids, source_db):
    cur.execute(
        "SELECT h.HISTORYID, h.REGARDING, h.DETAILS, h.STARTTIME, h.DURATION, "
        "ht.NAME AS TYPENAME, ch.CONTACTID, cmh.COMPANYID "
        "FROM TBL_HISTORY h "
        "JOIN TBL_HISTORYTYPE ht ON ht.HISTORYTYPEID = h.HISTORYTYPEID "
        "LEFT JOIN TBL_CONTACT_HISTORY ch ON ch.HISTORYID = h.HISTORYID "
        "LEFT JOIN TBL_COMPANY_HISTORY cmh ON cmh.HISTORYID = h.HISTORYID"
    )
    rows, seen, dropped_noise, dropped_unlinked = [], set(), 0, 0
    for r in cur.fetchall():
        if r["HISTORYID"] in seen:
            continue
        if r["TYPENAME"] not in HISTORY_TYPES_KEPT:
            dropped_noise += 1
            continue
        contact_id = ids.get("contact", r["CONTACTID"])
        company_id = ids.get("company", r["COMPANYID"])
        entity_type, entity_id = ("contact", contact_id) if contact_id else ("company", company_id) if company_id else (None, None)
        if not entity_id:
            dropped_unlinked += 1
            continue
        seen.add(r["HISTORYID"])
        rows.append({
            "id": uuid.uuid4(), "source_db": source_db, "source_act_id": to_uuid_str(r["HISTORYID"]),
            "entity_type": entity_type, "entity_id": entity_id,
            "history_type": r["TYPENAME"], "subject": r["REGARDING"], "details": r["DETAILS"],
            "duration_minutes": r["DURATION"], "occurred_at": r["STARTTIME"],
        })
    print(f"  history_entries: dropped {dropped_noise} rows as Act! system noise "
          f"(type not in HISTORY_TYPES_KEPT), {dropped_unlinked} as unlinked to any migrated contact/company")
    bulk_upsert(conn, HistoryEntry.__table__, rows, "uq_history_entries_source", "history_entries")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source-db", required=True, choices=SOURCE_DBS)
    p.add_argument("--mssql-host", default="localhost")
    p.add_argument("--mssql-port", default=1433, type=int)
    p.add_argument("--mssql-user", default="sa")
    p.add_argument("--mssql-password", required=True)
    p.add_argument("--pg-url", required=True)
    run(p.parse_args())
