#!/usr/bin/env python3
"""One-time backfill: who wrote each Act! note and history entry (TBL_NOTE / TBL_HISTORY CREATEUSERID -> the
TBL_ACCESSOR name), into notes.act_author / history_entries.act_author. "Who looks after each client"
(backend/app/sales/ownership.py) needs it: an existing client stays with whoever was last in touch in Act!.

Run once per source database, after etl.py (and migration 0066), same flags as backfill_owner.py:

    python backfill_note_authors.py --source-db onboard \\
        --pg-url postgresql+psycopg://postgres:postgres@localhost:5433/bmi

UPDATE only (matched by source_db + source_act_id), never inserts - safe to re-run. The raw Act! name is kept as it
is; ownership.py matches it to a salesperson by name, so a past rep or a shared login ("BMI Administrator") simply
doesn't count for anyone.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from psycopg2.extras import execute_values
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl import discover_accessor_name_expr, mssql_connect, to_uuid_str  # noqa: E402
from app.models.base import SOURCE_DBS  # noqa: E402

TABLES = (("TBL_NOTE", "NOTEID", "notes"), ("TBL_HISTORY", "HISTORYID", "history_entries"))


def run(args) -> None:
    print(f"=== Note and history authors: {args.source_db} ===")
    ms = mssql_connect(args)
    cur = ms.cursor()
    name_expr = discover_accessor_name_expr(cur, alias="a")
    found = {}
    for act_table, id_col, _pg in TABLES:
        cur.execute(f"SELECT t.{id_col} AS ID, {name_expr} AS AUTHOR FROM {act_table} t "
                    "LEFT JOIN TBL_ACCESSOR a ON a.ACCESSORID = t.CREATEUSERID")
        found[act_table] = [(args.source_db, to_uuid_str(r["ID"]), (r["AUTHOR"] or "").strip()[:120])
                            for r in cur.fetchall() if (r["AUTHOR"] or "").strip()]
    ms.close()

    pg = create_engine(args.pg_url.replace("postgresql+psycopg://", "postgresql+psycopg2://"))
    with pg.begin() as conn:
        raw = conn.connection.dbapi_connection.cursor()
        for act_table, _id, pg_table in TABLES:
            rows = found[act_table]
            sql = (f"UPDATE {pg_table} AS t SET act_author = v.author FROM (VALUES %s) AS v(source_db, source_act_id, author) "
                   "WHERE t.source_db = v.source_db AND t.source_act_id = v.source_act_id")
            for i in range(0, len(rows), 1000):
                execute_values(raw, sql, rows[i:i + 1000], page_size=1000)
            names = {}
            for _db, _id2, a in rows:
                names[a] = names.get(a, 0) + 1
            top = ", ".join(f"{n} ({c})" for n, c in sorted(names.items(), key=lambda x: -x[1])[:12])
            print(f"  {pg_table}: {len(rows)} rows with an author in Act! - most: {top}")
        raw.close()
    print(f"=== {args.source_db}: done. Then press Run now on 'Who looks after each client' (Automations), "
          "or wait for the nightly run. ===")


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
