import argparse
import os
import sys
import time
import pyodbc

# Standard logical names in Act! BAK files: ACT_DATA and ACT_LOG
MSSQL_DATA_DIR = r"C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\DATA"

def restore_bak(bak_filename: str, db_name: str):
    abs_bak_path = os.path.abspath(bak_filename)
    if not os.path.exists(abs_bak_path):
        print(f"Error: File not found: {abs_bak_path}")
        sys.exit(1)

    mdf_dest = os.path.join(MSSQL_DATA_DIR, f"{db_name.lower()}.mdf")
    ldf_dest = os.path.join(MSSQL_DATA_DIR, f"{db_name.lower()}_log.ldf")

    print(f"Connecting to local SQL Server...")
    conn = pyodbc.connect(
        "Driver={ODBC Driver 17 for SQL Server};Server=.;Database=master;Trusted_Connection=yes;",
        autocommit=True,
    )
    cur = conn.cursor()

    print(f"Inspecting filelist in {abs_bak_path}...")
    cur.execute(f"RESTORE FILELISTONLY FROM DISK = N'{abs_bak_path}';")
    files = cur.fetchall()
    data_logical = next((r[0] for r in files if r[2] == "D"), "ACT_DATA")
    log_logical = next((r[0] for r in files if r[2] == "L"), "ACT_LOG")
    print(f"  Data logical name: {data_logical} -> {mdf_dest}")
    print(f"  Log logical name:  {log_logical} -> {ldf_dest}")

    sql = f"""
    RESTORE DATABASE [{db_name}]
    FROM DISK = N'{abs_bak_path}'
    WITH MOVE N'{data_logical}' TO N'{mdf_dest}',
         MOVE N'{log_logical}' TO N'{ldf_dest}',
         REPLACE, STATS = 10;
    """
    print(f"Restoring database [{db_name}]...")
    start = time.time()
    cur.execute(sql)
    while cur.nextset():
        pass
    elapsed = time.time() - start
    print(f"Successfully restored [{db_name}] in {elapsed:.1f}s!")

    cur.execute(f"USE [{db_name}];")
    cur.execute("SELECT COUNT(*) FROM TBL_ACTIVITY;")
    act_count = cur.fetchone()[0]
    print(f"  TBL_ACTIVITY count: {act_count}")

    cur.execute("SELECT COUNT(*) FROM TBL_CONTACT_ACTIVITY;")
    contact_act_count = cur.fetchone()[0]
    print(f"  TBL_CONTACT_ACTIVITY count: {contact_act_count}")
    conn.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Restore an Act! BAK file into local SQL Server")
    p.add_argument("bak_file", help="Path or filename of the .BAK file")
    p.add_argument("db_name", choices=["OnBoard", "Prospects", "SellingTravel"], help="Target database name")
    args = p.parse_args()
    restore_bak(args.bak_file, args.db_name)
