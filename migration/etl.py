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
        --pg-url postgresql+psycopg://postgres:postgres@localhost:5433/bmi

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
    Activity, ActivityCompany, ActivityContact, ActivityGroup, ActivityInvitee, Address,
    Attachment, Company, Contact, ContactCompanyLink, Email, Group, GroupMembership,
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


class DictCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, *args, **kwargs):
        if args and len(args) > 0 and isinstance(args[0], str):
            sql = args[0].replace("%s", "?")
            return self._cursor.execute(sql, *args[1:], **kwargs)
        return self._cursor.execute(*args, **kwargs)

    def fetchall(self):
        desc = [c[0] for c in self._cursor.description] if self._cursor.description else []
        return [{name: val for name, val in zip(desc, row)} for row in self._cursor.fetchall()]

    def fetchone(self):
        row = self._cursor.fetchone()
        if not row:
            return None
        desc = [c[0] for c in self._cursor.description]
        return {name: val for name, val in zip(desc, row)}


class PyOdbcConnWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return DictCursorWrapper(self._conn.cursor())

    def close(self):
        return self._conn.close()


def mssql_connect(args):
    if getattr(args, "use_odbc", False) or not args.mssql_password:
        import pyodbc
        db = MSSQL_DB_NAMES[args.source_db]
        server = args.mssql_host if args.mssql_host not in ("localhost", "127.0.0.1") else "."
        conn_str = f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={db};Trusted_Connection=yes;"
        return PyOdbcConnWrapper(pyodbc.connect(conn_str))
    try:
        import pymssql
        return pymssql.connect(
            server=args.mssql_host, port=str(args.mssql_port),
            user=args.mssql_user, password=args.mssql_password,
            database=MSSQL_DB_NAMES[args.source_db], as_dict=True,
        )
    except Exception:
        import pyodbc
        db = MSSQL_DB_NAMES[args.source_db]
        server = args.mssql_host if args.mssql_host not in ("localhost", "127.0.0.1") else "."
        conn_str = f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={db};Trusted_Connection=yes;"
        return PyOdbcConnWrapper(pyodbc.connect(conn_str))



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


# TBL_ACCESSOR (Act!'s own user/salesperson table) isn't in docs/act-schema -
# it was never dumped in detail during schema exploration, so the exact
# display-name column isn't confirmed. Discovered live instead of hardcoded
# to avoid shipping a guessed column name that breaks the query against the
# real .bak; preference order matches Act!'s documented public API field
# names (most to least likely), first match wins.
_ACCESSOR_NAME_PREFERENCE = ["ACCESSORNAME", "FULLNAME", "USERNAME", "LOGONNAME", "NAME", "RECORDMANAGER"]


def discover_accessor_name_expr(cur, alias: str = "TBL_ACCESSOR") -> str:
    """A SQL expression (column ref or concat, qualified with `alias`) usable
    directly in a SELECT to get TBL_ACCESSOR's display name, whatever it's
    actually called in this database. `alias` is the table/join-alias this
    expression will be evaluated against in the calling query - pass
    whatever alias that query joins TBL_ACCESSOR in as. Always returns
    something query-safe - worst case a NULL literal, never a guessed
    column name that would fail at query time."""
    cur.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'TBL_ACCESSOR'"
    )
    present = {r["COLUMN_NAME"] for r in cur.fetchall()}
    for candidate in _ACCESSOR_NAME_PREFERENCE:
        if candidate in present:
            return f"{alias}.[{candidate}]"
    if {"FIRSTNAME", "LASTNAME"} <= present:
        return f"({alias}.[FIRSTNAME] + ' ' + {alias}.[LASTNAME])"
    print("  WARNING: could not find a display-name column on TBL_ACCESSOR - "
          "organizer/invitee names will be blank. Check the real column name "
          "with `SELECT TOP 5 * FROM TBL_ACCESSOR` and add it to "
          "_ACCESSOR_NAME_PREFERENCE above.")
    return "NULL"


def to_uuid_str(v) -> str | None:
    if v is None:
        return None
    return str(v).strip("{}").lower()


def remove_nul_bytes(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {key: remove_nul_bytes(item) for key, item in value.items()}
    if isinstance(value, list):
        return [remove_nul_bytes(item) for item in value]
    return value


class IdMap:
    """act_id (lowercased string) -> our uuid.UUID, per entity kind.

    Critical for re-running this script against already-migrated data (e.g.
    to add a new table like activity_contacts on top of contacts/activities
    that were migrated in an earlier run): get_or_create() mints a random
    uuid4() for anything not already in this in-memory map, which is only
    correct for a row that's genuinely new. For a row that was migrated
    before, bulk_upsert's ON CONFLICT DO NOTHING silently discards the
    (wrong, freshly-minted) id on the parent row itself - but without
    preload() below, any *downstream* row in the same run that references
    that id via get() would carry the wrong UUID, one that doesn't match
    what's actually in Postgres, and fail its foreign key constraint (loud
    failure, not silent corruption - but still wrong and avoidable).

    preload() fixes this by seeding the map from what's already in Postgres
    for this source_db before any get_or_create() call, so every reference
    - old or new - resolves to the real, persisted id.
    """

    def __init__(self):
        self._maps: dict[str, dict[str, uuid.UUID]] = {}

    def preload(self, conn, kind: str, table, source_db: str) -> int:
        """Seed the map for `kind` from rows already in Postgres, keyed by
        this table's own (source_db, source_act_id) uniqueness. Call once
        per kind, before the first get_or_create() for it, on every run -
        cheap even at ~118k contacts (one indexed SELECT of two columns)."""
        m = self._maps.setdefault(kind, {})
        rows = conn.execute(
            sa.select(table.c.id, table.c.source_act_id).where(table.c.source_db == source_db)
        ).all()
        for row_id, source_act_id in rows:
            m[to_uuid_str(source_act_id)] = row_id
        return len(rows)

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


def bulk_upsert(conn, table, rows: list[dict], constraint: str, label: str, refresh: bool = False):
    """refresh=False (default): ON CONFLICT DO NOTHING - safe to re-run,
    only ever adds rows that aren't there yet, never touches an existing
    one (so it can't clobber anything edited inside the CRM itself since
    migration).

    refresh=True: ON CONFLICT DO UPDATE - re-running against a newer Act!
    .bak also pulls in edits made in Act! to already-migrated rows, not
    just brand-new ones. Use this for the "catch up the CRM with a week's
    worth of Act! changes" case - see migration/README.md's "Refreshing
    after go-live" section. It will overwrite, with whatever Act! says,
    any change made directly in the CRM to a row that came from Act!
    (source_db != "manual"); rows created straight in the CRM have no
    source_act_id match in Act! and are never touched either way.
    """
    if not rows:
        print(f"  {label}: 0 rows (nothing to insert)")
        return 0
    # Keep each statement below PostgreSQL's 65,535-parameter limit.
    batch_size = 500
    inserted = 0
    for start in range(0, len(rows), batch_size):
        batch = [
            {key: remove_nul_bytes(value) for key, value in row.items()}
            for row in rows[start:start + batch_size]
        ]
        stmt = sa.dialects.postgresql.insert(table).values(batch)
        if refresh:
            update_cols = {
                key: getattr(stmt.excluded, key)
                for key in batch[0]
                if key not in ("id", "source_db", "source_act_id")
            }
            stmt = stmt.on_conflict_do_update(constraint=constraint, set_=update_cols) if update_cols \
                else stmt.on_conflict_do_nothing(constraint=constraint)
        else:
            stmt = stmt.on_conflict_do_nothing(constraint=constraint)
        stmt = stmt.returning(table.c.id)
        # .rowcount is unreliable for ON CONFLICT DO NOTHING with some drivers -
        # count the RETURNING rows instead, which always reflects what actually landed.
        inserted += len(conn.execute(stmt).fetchall())
    verb = "upserted" if refresh else "inserted"
    print(f"  {label}: {len(rows)} extracted, {inserted} {verb} "
          f"({len(rows) - inserted} unchanged/skipped)")
    return inserted


def run(args):
    source_db = args.source_db
    field_maps = CUSTOM_FIELD_MAPS[source_db]
    refresh = args.refresh

    print(f"=== ETL: {source_db} -> Postgres {'(refresh mode)' if refresh else ''} ===")
    ms = mssql_connect(args)
    cur = ms.cursor()

    pg_url = args.pg_url
    if "postgresql+psycopg://" in pg_url:
        pg_url = pg_url.replace("postgresql+psycopg://", "postgresql+psycopg2://")
    pg = create_engine(pg_url)
    ids = IdMap()

    contact_cust_cols = discover_custom_columns(cur, "TBL_CONTACT")
    company_cust_cols = discover_custom_columns(cur, "TBL_COMPANY")
    group_cust_cols = discover_custom_columns(cur, "TBL_GROUP")
    # Never discovered before - discover_custom_columns() was only ever
    # called for the three entities above, so TBL_OPPORTUNITY's USER1-8
    # custom fields were silently dropped.
    opportunity_cust_cols = discover_custom_columns(cur, "TBL_OPPORTUNITY")
    organizer_name_expr = discover_accessor_name_expr(cur, alias="org")
    invitee_name_expr = discover_accessor_name_expr(cur, alias="acc")

    with pg.begin() as conn:
        # Seed the id map from whatever's already in Postgres for this
        # source_db BEFORE any get_or_create() call below - see IdMap's
        # docstring. Matters every time this script runs against a
        # source_db that's been migrated before (adding a new table on top
        # of existing data, or a --refresh pass), not just the first time.
        for kind, table in (
            ("company", Company.__table__), ("group", Group.__table__),
            ("contact", Contact.__table__), ("activity", Activity.__table__),
            ("opportunity", Opportunity.__table__), ("note", Note.__table__),
            ("history", HistoryEntry.__table__),
        ):
            n = ids.preload(conn, kind, table, source_db)
            if n:
                print(f"  preloaded {n} existing {kind} id(s) for {source_db}")

        if args.only == "activities":
            print(f"  [Targeted run: activities, associations, invitees & attachments only]")
            _migrate_activities_full(
                cur, conn, ids, source_db, organizer_name_expr, invitee_name_expr,
                refresh=refresh, update_existing=True,
            )
            print(f"=== {source_db}: done (activities only) ===")
            return

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
                "ticker_symbol": r["TICKERSYMBOL"], "sic_code": r["SICCODE"],
                "parent_company_id": ids.get("company", r["PARENTCOMPANYID"]),
                "custom_fields": decode_custom_fields(cust_raw, field_maps["company"]),
                "act_created_at": r["CREATEDATE"], "act_edited_at": r["EDITDATE"],
            })
        bulk_upsert(conn, Company.__table__, rows, "uq_companies_source", "companies", refresh=refresh)

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
        bulk_upsert(conn, Group.__table__, rows, "uq_groups_source", "groups", refresh=refresh)

        # ---- Contacts ----
        cur.execute(
            "SELECT CONTACTID, COMPANYID, FIRSTNAME, MIDDLENAME, LASTNAME, FULLNAME, "
            "NAMEPREFIX, NAMESUFFIX, SALUTATION, JOBTITLE, DEPARTMENT, CATEGORY, "
            "REFERREDBY, BIRTHDATE, ISPRIVATE, LASTMEETDATE, LASTREACHDATE, "
            "LASTATTEMPTDATE, LASTLETTERDATE, LASTEMAILDATE, COMPANYNAME, LASTRESULTS, "
            "AEM_OPTOUT, AEM_BOUNCEBACK, AMA_SCORE, CREATEDATE, EDITDATE, "
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
                "last_email_date": r["LASTEMAILDATE"],
                "company_name_freetext": r["COMPANYNAME"], "last_results": r["LASTRESULTS"],
                "is_email_opted_out": bool(r["AEM_OPTOUT"]), "has_bounced": bool(r["AEM_BOUNCEBACK"]),
                "engagement_score": r["AMA_SCORE"],
                "custom_fields": decode_custom_fields(cust_raw, field_maps["contact"]),
                "act_created_at": r["CREATEDATE"], "act_edited_at": r["EDITDATE"],
            })
        bulk_upsert(conn, Contact.__table__, rows, "uq_contacts_source", "contacts", refresh=refresh)

        # ---- Contact <-> Company secondary links (a contact can belong to
        # several companies in Act!; contacts.company_id only holds one) ----
        cur.execute("SELECT COMPANYID, CONTACTID, ROWSOURCE FROM TBL_COMPANY_CONTACT")
        rows = []
        for r in cur.fetchall():
            cid, coid = ids.get("contact", r["CONTACTID"]), ids.get("company", r["COMPANYID"])
            if cid and coid:
                rows.append({
                    "id": uuid.uuid4(), "contact_id": cid, "company_id": coid,
                    "row_source": r["ROWSOURCE"],
                })
        bulk_upsert(conn, ContactCompanyLink.__table__, rows, "uq_contact_company_links", "contact_company_links")

        # ---- Group memberships ----
        cur.execute("SELECT GROUPID, CONTACTID FROM TBL_GROUP_CONTACT")
        rows = []
        for r in cur.fetchall():
            gid, cid = ids.get("group", r["GROUPID"]), ids.get("contact", r["CONTACTID"])
            if gid and cid:
                rows.append({"id": uuid.uuid4(), "group_id": gid, "contact_id": cid})
        bulk_upsert(conn, GroupMembership.__table__, rows, "uq_group_memberships", "group_memberships")

        # Register opportunity ids early (before Notes/History below, which
        # need to resolve an opportunity link) - the full Opportunity row
        # migration itself still happens later, in its own section; this is
        # just the id map, same pattern as company/group/contact above.
        cur.execute("SELECT OPPORTUNITYID FROM TBL_OPPORTUNITY")
        for r in cur.fetchall():
            ids.get_or_create("opportunity", r["OPPORTUNITYID"])

        # ---- Addresses / Phones / Emails (contact + company only) ----
        _migrate_channel(cur, conn, ids, source_db, "TBL_ADDRESS", Address.__table__,
                          "uq_addresses_source", "addresses",
                          extra_cols="LINE1, LINE2, LINE3, CITY, STATE, POSTALCODE, COUNTRYNAME, LATITUDE, LONGITUDE",
                          row_to_extra=lambda r: {
                              "line1": r["LINE1"], "line2": r["LINE2"], "line3": r["LINE3"],
                              "city": r["CITY"], "state": r["STATE"], "postal_code": r["POSTALCODE"],
                              "country": r["COUNTRYNAME"], "latitude": r["LATITUDE"], "longitude": r["LONGITUDE"],
                          }, id_col="ADDRESSID", refresh=refresh)
        _migrate_channel(cur, conn, ids, source_db, "TBL_PHONE", Phone.__table__,
                          "uq_phones_source", "phones",
                          extra_cols="NUMBERDISPLAY, COUNTRYCODE, SUFFIX",
                          row_to_extra=lambda r: {
                              "number": r["NUMBERDISPLAY"], "country_code": r["COUNTRYCODE"], "extension": r["SUFFIX"],
                          },
                          id_col="PHONEID", refresh=refresh)
        _migrate_channel(cur, conn, ids, source_db, "TBL_EMAIL", Email.__table__,
                          "uq_emails_source", "emails",
                          extra_cols="ADDRESS",
                          row_to_extra=lambda r: {"address": r["ADDRESS"]},
                          id_col="EMAILID", refresh=refresh)

        # ---- Notes (flattened via junction tables) ----
        _migrate_notes(cur, conn, ids, source_db, refresh=refresh)

        # ---- History (flattened + filtered) ----
        _migrate_history(cur, conn, ids, source_db, refresh=refresh)

        # ---- Activities (kept, flat - see activity.py docstring) ----
        _migrate_activities_full(
            cur, conn, ids, source_db, organizer_name_expr, invitee_name_expr,
            refresh=refresh, update_existing=False,
        )

        # ---- Opportunities (kept, flat) ----
        cur.execute(
            "SELECT o.OPPORTUNITYID, o.NAME, o.STATUS, o.SOURCE, o.COMPETITOR, o.CLOSEREASON, "
            "o.TOTALEXTENDEDAMT, o.PROBABILITYPCT, o.OPENDATE, o.ESTIMATEDCLOSEDATE, o.ACTUALCLOSEDATE, "
            "s.NAME AS STAGENAME, "
            + ", ".join(f"o.[{c}]" for c in opportunity_cust_cols) + (", " if opportunity_cust_cols else "") +
            "co.CONTACTID, cmo.COMPANYID "
            "FROM TBL_OPPORTUNITY o "
            "LEFT JOIN TBL_STAGE s ON s.STAGEID = o.STAGEID "
            "LEFT JOIN TBL_CONTACT_OPPORTUNITY co ON co.OPPORTUNITYID = o.OPPORTUNITYID "
            "LEFT JOIN TBL_COMPANY_OPPORTUNITY cmo ON cmo.OPPORTUNITYID = o.OPPORTUNITYID"
        )
        rows, seen = [], set()
        for r in cur.fetchall():
            if r["OPPORTUNITYID"] in seen:  # a junction could in principle add duplicate rows; keep first
                continue
            seen.add(r["OPPORTUNITYID"])
            cust_raw = {c: r[c] for c in opportunity_cust_cols}
            rows.append({
                "id": ids.get("opportunity", r["OPPORTUNITYID"]), "source_db": source_db,
                "source_act_id": to_uuid_str(r["OPPORTUNITYID"]),
                "contact_id": ids.get("contact", r["CONTACTID"]), "company_id": ids.get("company", r["COMPANYID"]),
                "name": r["NAME"], "status": r["STATUS"], "stage_name": r["STAGENAME"], "source": r["SOURCE"],
                "competitor": r["COMPETITOR"], "close_reason": r["CLOSEREASON"],
                "total_amount": r["TOTALEXTENDEDAMT"], "probability_pct": r["PROBABILITYPCT"],
                "open_at": r["OPENDATE"], "estimated_close_at": r["ESTIMATEDCLOSEDATE"],
                "actual_close_at": r["ACTUALCLOSEDATE"],
                # No dedicated field_maps entry for opportunity custom fields
                # (only contact/company/group exist in custom_fields.py) -
                # keep raw column names rather than guessing labels; low
                # stakes given the tiny row count (7 total).
                "custom_fields": {k: v for k, v in cust_raw.items() if v is not None},
            })
        bulk_upsert(conn, Opportunity.__table__, rows, "uq_opportunities_source", "opportunities", refresh=refresh)

    print(f"=== {source_db}: done ===")


def _migrate_channel(cur, conn, ids, source_db, table, sa_table, constraint, label, extra_cols, row_to_extra, id_col, refresh=False):
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
        extra = row_to_extra(r)
        # Act! keeps one TBL_PHONE/TBL_ADDRESS/TBL_EMAIL row per *slot*
        # (Business, Fax, Mobile, ...) whether or not it was ever filled in,
        # so most contacts carry several empty rows that only have a
        # TYPEID/type_label and nothing else. Migrating those verbatim is
        # what produced "Fax:" / "Mobile:" rows with no value on the
        # contact page - skip a row with no actual value in any of its
        # data columns, since a bare type label isn't a fact worth keeping.
        if not any(str(v).strip() for v in extra.values() if v is not None):
            continue
        row = {
            "id": uuid.uuid4(), "source_db": source_db, "source_act_id": to_uuid_str(r[id_col]),
            "contact_id": contact_id, "company_id": company_id,
            "type_label": r["TYPENAME"], "is_primary": False,
        }
        row.update(extra)
        rows.append(row)
    bulk_upsert(conn, sa_table, rows, constraint, label, refresh=refresh)


def _migrate_notes(cur, conn, ids, source_db, refresh=False):
    cur.execute(
        "SELECT n.NOTEID, n.NOTETEXT, n.ISPRIVATE, n.CREATEDATE, nt.NAME AS TYPENAME, "
        "cn.CONTACTID, cmn.COMPANYID, gn.GROUPID, on_.OPPORTUNITYID "
        "FROM TBL_NOTE n "
        "LEFT JOIN TBL_NOTETYPE nt ON nt.NOTETYPEID = n.NOTETYPEID "
        "LEFT JOIN TBL_CONTACT_NOTE cn ON cn.NOTEID = n.NOTEID "
        "LEFT JOIN TBL_COMPANY_NOTE cmn ON cmn.NOTEID = n.NOTEID "
        "LEFT JOIN TBL_GROUP_NOTE gn ON gn.NOTEID = n.NOTEID "
        "LEFT JOIN TBL_OPPORTUNITY_NOTE on_ ON on_.NOTEID = n.NOTEID"
    )
    rows, seen = [], set()
    for r in cur.fetchall():
        if r["NOTEID"] in seen:
            continue
        contact_id = ids.get("contact", r["CONTACTID"])
        company_id = ids.get("company", r["COMPANYID"])
        group_id = ids.get("group", r["GROUPID"])
        opportunity_id = ids.get("opportunity", r["OPPORTUNITYID"])
        entity_type, entity_id = next(
            ((t, i) for t, i in (
                ("contact", contact_id), ("company", company_id),
                ("group", group_id), ("opportunity", opportunity_id),
            ) if i),
            (None, None),
        )
        if not entity_id:
            continue
        seen.add(r["NOTEID"])
        rows.append({
            "id": ids.get_or_create("note", r["NOTEID"]), "source_db": source_db, "source_act_id": to_uuid_str(r["NOTEID"]),
            "entity_type": entity_type, "entity_id": entity_id,
            "note_type": r["TYPENAME"], "body": r["NOTETEXT"], "is_private": bool(r["ISPRIVATE"]),
            "act_created_at": r["CREATEDATE"],
        })
    bulk_upsert(conn, Note.__table__, rows, "uq_notes_source", "notes", refresh=refresh)


def _migrate_history(cur, conn, ids, source_db, refresh=False):
    cur.execute(
        "SELECT h.HISTORYID, h.REGARDING, h.DETAILS, h.STARTTIME, h.DURATION, "
        "ht.NAME AS TYPENAME, ch.CONTACTID, cmh.COMPANYID, gh.GROUPID, oh.OPPORTUNITYID "
        "FROM TBL_HISTORY h "
        "JOIN TBL_HISTORYTYPE ht ON ht.HISTORYTYPEID = h.HISTORYTYPEID "
        "LEFT JOIN TBL_CONTACT_HISTORY ch ON ch.HISTORYID = h.HISTORYID "
        "LEFT JOIN TBL_COMPANY_HISTORY cmh ON cmh.HISTORYID = h.HISTORYID "
        "LEFT JOIN TBL_GROUP_HISTORY gh ON gh.HISTORYID = h.HISTORYID "
        "LEFT JOIN TBL_OPPORTUNITY_HISTORY oh ON oh.HISTORYID = h.HISTORYID"
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
        group_id = ids.get("group", r["GROUPID"])
        opportunity_id = ids.get("opportunity", r["OPPORTUNITYID"])
        entity_type, entity_id = next(
            ((t, i) for t, i in (
                ("contact", contact_id), ("company", company_id),
                ("group", group_id), ("opportunity", opportunity_id),
            ) if i),
            (None, None),
        )
        if not entity_id:
            dropped_unlinked += 1
            continue
        seen.add(r["HISTORYID"])
        rows.append({
            "id": ids.get_or_create("history", r["HISTORYID"]), "source_db": source_db, "source_act_id": to_uuid_str(r["HISTORYID"]),
            "entity_type": entity_type, "entity_id": entity_id,
            "history_type": r["TYPENAME"], "subject": r["REGARDING"], "details": r["DETAILS"],
            "duration_minutes": r["DURATION"], "occurred_at": r["STARTTIME"],
        })
    print(f"  history_entries: dropped {dropped_noise} rows as Act! system noise "
          f"(type not in HISTORY_TYPES_KEPT), {dropped_unlinked} as unlinked to any migrated contact/company")
    bulk_upsert(conn, HistoryEntry.__table__, rows, "uq_history_entries_source", "history_entries", refresh=refresh)


def _upsert_activities_update_links(conn, rows: list[dict]):
    if not rows:
        print("  activities: 0 rows")
        return 0
    batch_size = 500
    updated = 0
    for start in range(0, len(rows), batch_size):
        batch = [
            {key: remove_nul_bytes(value) for key, value in row.items()}
            for row in rows[start:start + batch_size]
        ]
        stmt = sa.dialects.postgresql.insert(Activity.__table__).values(batch)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_activities_source",
            set_={
                "contact_id": stmt.excluded.contact_id,
                "company_id": stmt.excluded.company_id,
                "duration_minutes": stmt.excluded.duration_minutes,
                "organized_by_name": stmt.excluded.organized_by_name,
                "priority": stmt.excluded.priority,
            },
        ).returning(Activity.__table__.c.id)
        updated += len(conn.execute(stmt).fetchall())
    print(f"  activities: {len(rows)} extracted, {updated} updated with links/duration/organizer/priority")
    return updated


def _migrate_activities_full(cur, conn, ids, source_db, organizer_name_expr, invitee_name_expr, refresh=False, update_existing=False):
    cur.execute(
        "SELECT a.ACTIVITYID, a.REGARDING, a.DETAILS, a.LOCATION, a.STARTTIME, a.ENDTIME, "
        "a.ISTIMELESS, a.DURATION, t.NAME AS TYPENAME, ac.ACCESSOR_ACTIVITY_CLEAREDID, "
        f"{organizer_name_expr} AS ORGNAME, "
        "ap.NAME AS PRIORITYNAME "
        "FROM TBL_ACTIVITY a "
        "LEFT JOIN TBL_ACTIVITYTYPE t ON t.ACTIVITYTYPEID = a.ACTIVITYTYPEID "
        "LEFT JOIN TBL_ACCESSOR_ACTIVITY_CLEARED ac ON ac.ACTIVITYID = a.ACTIVITYID "
        "LEFT JOIN TBL_ACCESSOR org ON org.ACCESSORID = a.ORGANIZEUSERID "
        "LEFT JOIN TBL_ACCESSOR_ACTIVITY aa ON aa.ACTIVITYID = a.ACTIVITYID AND aa.ACCESSORID = a.ORGANIZEUSERID "
        "LEFT JOIN TBL_ACTIVITYPRIORITY ap ON ap.ACTIVITYPRIORITYID = aa.ACTIVITYPRIORITYID"
    )
    activity_rows = cur.fetchall()
    for r in activity_rows:
        ids.get_or_create("activity", r["ACTIVITYID"])

    cur.execute("SELECT ACTIVITYID, CONTACTID FROM TBL_CONTACT_ACTIVITY")
    act_contacts: dict[str, list] = {}
    for r in cur.fetchall():
        cid = ids.get("contact", r["CONTACTID"])
        if cid:
            act_contacts.setdefault(to_uuid_str(r["ACTIVITYID"]), []).append(cid)
    cur.execute("SELECT ACTIVITYID, COMPANYID FROM TBL_COMPANY_ACTIVITY")
    act_companies: dict[str, list] = {}
    for r in cur.fetchall():
        coid = ids.get("company", r["COMPANYID"])
        if coid:
            act_companies.setdefault(to_uuid_str(r["ACTIVITYID"]), []).append(coid)

    rows = []
    for r in activity_rows:
        act_id_str = to_uuid_str(r["ACTIVITYID"])
        linked_contacts = act_contacts.get(act_id_str, [])
        linked_companies = act_companies.get(act_id_str, [])
        backfill_contact_id = linked_contacts[0] if len(linked_contacts) == 1 and not linked_companies else None
        backfill_company_id = linked_companies[0] if len(linked_companies) == 1 and not linked_contacts else None
        pname = (r.get("PRIORITYNAME") or "").strip().lower()
        if "high" in pname:
            priority = "high"
        elif "low" in pname:
            priority = "low"
        else:
            priority = "normal"
        rows.append({
            "id": ids.get("activity", r["ACTIVITYID"]), "source_db": source_db,
            "source_act_id": to_uuid_str(r["ACTIVITYID"]),
            "contact_id": backfill_contact_id, "company_id": backfill_company_id,
            "activity_type": r["TYPENAME"], "subject": r["REGARDING"], "details": r["DETAILS"],
            "location": r["LOCATION"], "start_at": r["STARTTIME"], "end_at": r["ENDTIME"],
            "is_timeless": bool(r["ISTIMELESS"]), "is_cleared": r["ACCESSOR_ACTIVITY_CLEAREDID"] is not None,
            "duration_minutes": r["DURATION"], "organized_by_name": r["ORGNAME"],
            "priority": priority,
        })
    if update_existing and not refresh:
        _upsert_activities_update_links(conn, rows)
    else:
        bulk_upsert(conn, Activity.__table__, rows, "uq_activities_source", "activities", refresh=refresh)

    _migrate_activity_links(cur, conn, ids, source_db)
    _migrate_activity_invitees(cur, conn, ids, source_db, invitee_name_expr)
    _migrate_attachments(cur, conn, ids, source_db, refresh=refresh)


def _migrate_activity_links(cur, conn, ids, source_db):
    """Activity <-> contact/company/group, from TBL_CONTACT_ACTIVITY,
    TBL_COMPANY_ACTIVITY, TBL_GROUP_ACTIVITY - the full many-to-many
    picture (see activity_link.py's module docstring). Must run AFTER
    activities are inserted (needs their ids in the map)."""
    cur.execute("SELECT ACTIVITYID, CONTACTID, ISINVITED FROM TBL_CONTACT_ACTIVITY")
    rows = []
    for r in cur.fetchall():
        aid, cid = ids.get("activity", r["ACTIVITYID"]), ids.get("contact", r["CONTACTID"])
        if aid and cid:
            rows.append({"id": uuid.uuid4(), "activity_id": aid, "contact_id": cid, "is_invited": bool(r["ISINVITED"])})
    bulk_upsert(conn, ActivityContact.__table__, rows, "uq_activity_contacts", "activity_contacts")

    cur.execute("SELECT ACTIVITYID, COMPANYID FROM TBL_COMPANY_ACTIVITY")
    rows = []
    for r in cur.fetchall():
        aid, coid = ids.get("activity", r["ACTIVITYID"]), ids.get("company", r["COMPANYID"])
        if aid and coid:
            rows.append({"id": uuid.uuid4(), "activity_id": aid, "company_id": coid})
    bulk_upsert(conn, ActivityCompany.__table__, rows, "uq_activity_companies", "activity_companies")

    cur.execute("SELECT ACTIVITYID, GROUPID FROM TBL_GROUP_ACTIVITY")
    rows = []
    for r in cur.fetchall():
        aid, gid = ids.get("activity", r["ACTIVITYID"]), ids.get("group", r["GROUPID"])
        if aid and gid:
            rows.append({"id": uuid.uuid4(), "activity_id": aid, "group_id": gid})
    bulk_upsert(conn, ActivityGroup.__table__, rows, "uq_activity_groups", "activity_groups")


def _migrate_activity_invitees(cur, conn, ids, source_db, name_expr):
    """Who's invited to a call/meeting - Act!'s "Invitee" column, from
    TBL_ACCESSOR_ACTIVITY. That table's own columns aren't in
    docs/act-schema (filed under "internal", never dumped in detail), so
    ACTIVITYID/ACCESSORID here is inferred from the naming convention every
    other *_ACTIVITY junction in this schema follows exactly
    (TBL_CONTACT_ACTIVITY: CONTACTID+ACTIVITYID, TBL_COMPANY_ACTIVITY:
    COMPANYID+ACTIVITYID, TBL_GROUP_ACTIVITY: GROUPID+ACTIVITYID) - if this
    table genuinely uses different column names, this query fails loudly
    (a clear SQL error naming the missing column), not silently.
    """
    cur.execute(
        f"SELECT aa.ACTIVITYID, {name_expr} AS ACCESSORNAME "
        "FROM TBL_ACCESSOR_ACTIVITY aa "
        "JOIN TBL_ACCESSOR acc ON acc.ACCESSORID = aa.ACCESSORID"
    )
    rows, seen = [], set()
    for r in cur.fetchall():
        aid = ids.get("activity", r["ACTIVITYID"])
        name = (r["ACCESSORNAME"] or "").strip()
        if not aid or not name:
            continue
        key = (str(aid), name)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"id": uuid.uuid4(), "activity_id": aid, "accessor_name": name, "user_id": None})
    bulk_upsert(conn, ActivityInvitee.__table__, rows, "uq_activity_invitees", "activity_invitees")


def _migrate_attachments(cur, conn, ids, source_db, refresh=False):
    """File attachments on a Note/History/Activity - metadata only (a
    manifest of what was attached), not the files themselves; Act! stores
    those on a filesystem share this script has no access to. See
    activity_link.py's Attachment docstring."""
    cur.execute(
        "SELECT ATTACHMENTID, FILENAME, DISPLAYNAME, NOTEID, ACTIVITYID, HISTORYID, WORKFLOWDEFID "
        "FROM TBL_ATTACHMENT"
    )
    rows = []
    for r in cur.fetchall():
        if r["WORKFLOWDEFID"] is not None and not (r["NOTEID"] or r["ACTIVITYID"] or r["HISTORYID"]):
            continue  # workflow plumbing, not a real attachment on a record we migrate
        note_id = ids.get("note", r["NOTEID"])
        history_id = ids.get("history", r["HISTORYID"])
        activity_id = ids.get("activity", r["ACTIVITYID"])
        if not (note_id or history_id or activity_id):
            continue  # dangling reference to a record we didn't migrate
        rows.append({
            "id": uuid.uuid4(), "source_db": source_db, "source_act_id": to_uuid_str(r["ATTACHMENTID"]),
            "note_id": note_id, "history_id": history_id, "activity_id": activity_id,
            "file_name": r["FILENAME"], "display_name": r["DISPLAYNAME"],
        })
    bulk_upsert(conn, Attachment.__table__, rows, "uq_attachments_source", "attachments", refresh=refresh)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source-db", required=True, choices=SOURCE_DBS)
    p.add_argument("--mssql-host", default="localhost")
    p.add_argument("--mssql-port", default=1433, type=int)
    p.add_argument("--mssql-user", default="sa")
    p.add_argument("--mssql-password", default="", help="SQL Server password (leave blank for Windows Auth via ODBC)")
    p.add_argument("--use-odbc", action="store_true", help="Use ODBC with Windows Integrated Authentication")
    p.add_argument("--pg-url", required=True)
    p.add_argument(
        "--only", choices=["activities", "all"], default="all",
        help="Target only a specific subset: 'activities' only runs activities, associations, invitees, and attachments.",
    )
    p.add_argument(
        "--refresh", action="store_true",
        help="ON CONFLICT DO UPDATE instead of DO NOTHING - use when re-running "
             "against a newer .bak to pull in edits Act! made to already-migrated "
             "rows (not just new ones). See migration/README.md.",
    )
    run(p.parse_args())
