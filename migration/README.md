# Act! → Postgres migration

One-time pipeline that moves all three Act! databases (OnBoard, Prospects,
SellingTravel) into the new CRM's Postgres schema. Not part of the running
app - this is an operator tool you run yourself, once per database, then
you're done with it (until BMI hands you an updated Act! backup, if ever).

Full background on the source data: `docs/act-schema/{onboard,prospects,sellingtravel}-schema.md`.
Schema design decisions: `CONTEXT.md`, and the docstrings in `backend/app/models/*.py`.

## What this does NOT do

- It does **not** touch the real, live Act! system. Input is a `.bak` file
  restored into a **throwaway** SQL Server instance you stand up yourself,
  purely so this script has something to run SQL against. Nothing here
  writes to Act!.
- It does **not** guess at anything. Every row keeps `source_db` +
  `source_act_id` forever, so any question about "where did this come
  from" is always answerable, and the script is safe to re-run (every
  insert is `ON CONFLICT (source_db, source_act_id) DO NOTHING`).

## One-time setup

### Windows PowerShell

Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/)
with the WSL 2 backend enabled. Then open a new PowerShell window and run:

```powershell
cd F:\bmi-sandbox\migration
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
docker version
```

If `docker` is not recognized, Docker Desktop is not installed, is not
running, or its CLI directory is not on `PATH`. Start Docker Desktop and open
a new PowerShell window before retrying. If Docker Desktop reports that WSL 2
is unavailable, run `wsl --update`, reboot Windows if requested, and enable
WSL 2 integration in Docker Desktop settings.

### Linux/macOS

```bash
cd migration
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

You also need a way to restore a `.bak` into a temporary SQL Server. Docker
is the easiest:

```bash
docker pull mcr.microsoft.com/mssql/server:2022-latest
```

## Per-database run (repeat 3x: onboard, prospects, sellingtravel)

**1. Restore the `.bak` into a throwaway SQL Server container.**

```bash
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=<pick-a-password>" \
  -p 1433:1433 --name act-sql \
  -v /path/to/folder/containing/the/bak:/var/opt/mssql/backup \
  -d mcr.microsoft.com/mssql/server:2022-latest

# wait ~15s for it to come up, then, matching the RESTORE statement used
# during schema exploration - database name must be exactly one of
# OnBoard / Prospects / SellingTravel (see MSSQL_DB_NAMES in etl.py):
docker exec act-sql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '<password>' -C -Q \
  "RESTORE FILELISTONLY FROM DISK = '/var/opt/mssql/backup/<the .bak filename>'"
# ^ note the logical file names it prints (ACT_DATA / ACT_LOG), then:

docker exec act-sql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '<password>' -C -Q \
  "RESTORE DATABASE OnBoard FROM DISK = '/var/opt/mssql/backup/<the .bak filename>' \
   WITH MOVE 'ACT_DATA' TO '/var/opt/mssql/data/onboard.mdf', \
        MOVE 'ACT_LOG' TO '/var/opt/mssql/data/onboard_log.ldf', STATS = 10"
```

(swap `OnBoard`/`onboard` for `Prospects`/`prospects` or
`SellingTravel`/`sellingtravel` on the other two runs)

**2. Run the ETL against the target Postgres.**

```bash
python etl.py --source-db onboard \
  --mssql-host localhost --mssql-port 1433 --mssql-user sa --mssql-password '<password>' \
  --pg-url 'postgresql+psycopg://postgres:postgres@localhost:5433/bmi'
```

Read its output. It prints, per entity type, how many rows it extracted
from SQL Server vs. how many it actually inserted (the difference is rows
already present from a prior run - expected on a re-run, unexpected on a
first run). For `history_entries` it also prints how many rows it dropped
as Act! system noise and how many as unlinked - see
`backend/app/models/history.py`'s `HISTORY_TYPES_KEPT` for exactly which
history types are kept.

**3. Tear the SQL Server container down** (it did its job, no reason to
keep 1.5-15GB of restored `.bak` sitting around):

```bash
docker rm -f act-sql
```

**4. Repeat steps 1-3 for the other two databases.**

## Validating before you trust it

**Do this against a throwaway/local Postgres first** (e.g. the
`docker compose up db` from the repo root, or a scratch database on your
own machine) - never point `--pg-url` at the real Dokploy database until
you've done this once and are satisfied:

1. Run all three databases through the pipeline.
2. Compare row counts against `docs/act-schema/*.md`'s row-count tables -
   `companies`/`contacts`/`groups` should match the source `TBL_COMPANY`/
   `TBL_CONTACT`/`TBL_GROUP` counts closely (a handful missing is fine and
   expected - e.g. a company with a blank name, or an address/phone/email
   pointing at neither a contact nor a company).
3. Spot-check a handful of real contacts: pull one up in the source Act!
   client (or the restored SQL Server directly) and compare against the
   Postgres row - name, company link, group memberships, a note or two,
   custom fields under `custom_fields` (check the labels match
   `migration/custom_fields.py`, not raw `CUST_*` names).
4. Check `history_entries` and `notes` counts are meaningfully smaller
   than the source `TBL_HISTORY`/`TBL_NOTE` counts (that's the noise
   filter and the contact/company-only scoping working as intended, not a
   bug) - the ETL's own printed "dropped N as noise" line is the ground
   truth for how much was filtered and why.
5. Only once all of that looks right, re-run with `--pg-url` pointing at
   the real Dokploy Postgres.

## Running it against the real Dokploy database

You (the user) need to do the actual "point this at production" step
yourself - I don't have credentials or network access to your Dokploy
instance from this sandbox. Concretely:

1. Get the Postgres connection string Dokploy is using for the `backend`
   service (Dokploy's env vars UI, or your `docker-compose`/Dokploy app
   config - the same `DATABASE_URL` the backend already connects with).
2. Run `alembic upgrade head` from `backend/` against that database first
   (creates the tables this ETL writes into - see "Applying the schema"
   below).
3. Run the 3x per-database steps above with `--pg-url` set to that
   connection string.
4. Re-run the row-count/spot-check validation from the section above,
   this time against the real data.

This only needs to happen once. After that, the CRM's own Postgres is the
system of record - Act! is retired, per CONTEXT.md.

## Refreshing during the transition week (before Act! is actually retired)

There will normally be a gap between "data migrated" and "everyone has
actually stopped touching Act!" - e.g. staff keep using Act! as usual for
a few more days while the CRM is reviewed. Anything entered or edited in
Act! during that gap is invisible to the CRM until you re-run this ETL
against a newer `.bak`.

**There is no live/automatic connection to Act! today** - getting a newer
`.bak` is a manual step (someone with access to the real Act! system
exports one), same as the original migration. There's no way around a
person doing that export; what this tooling controls is what happens
once you have it.

Two things to decide before doing this more than once:

1. **Pick one system of record for the gap.** The safest option is: staff
   keep using Act! as normal during the transition, and the CRM stays
   read-only-in-practice (browse/review, don't rely on anyone's edits
   there yet). That way a refresh can never lose anything. If someone
   *does* edit a migrated record directly in the CRM during this window,
   know that a refresh will silently overwrite that edit with whatever
   Act! says (see point 2) - so either avoid that, or track such edits
   separately until Act! is actually retired. A brand-new record created
   straight in the CRM (`source_db="manual"`) is never touched by a
   refresh either way - it has no Act! counterpart to conflict with.

2. **Re-run with `--refresh` to actually pick up edits, not just new rows.**
   Without it, `bulk_upsert` uses `ON CONFLICT DO NOTHING` - re-running
   only adds contacts/companies/notes/etc. created in Act! since the last
   run; an edit to an *existing* migrated row (a changed phone number, a
   note added to an old contact, and so on) is silently ignored. Pass
   `--refresh` and it becomes `ON CONFLICT DO UPDATE`, so those edits land
   too:

   ```bash
   python etl.py --source-db onboard --refresh \
       --mssql-host localhost --mssql-port 1433 --mssql-password '...' \
       --pg-url postgresql+psycopg://...
   ```

   Repeat per database, same as the original migration. Safe to run as
   many times as you like - it's still keyed on `(source_db,
   source_act_id)`, so it only ever touches rows that came from Act!.

Once everyone has actually stopped using Act! day-to-day, stop doing
refreshes - from that point the CRM's own edits are the only ones that
matter, and an old `.bak` would just be a stale copy of the past.

## Applying the schema (do this before the first ETL run, anywhere)

```bash
cd backend
alembic upgrade head
```

This creates `companies`, `contacts`, `groups`, `group_memberships`,
`addresses`, `phones`, `emails`, `notes`, `history_entries`, `activities`,
`opportunities`, `review_queue` (migration `0002_crm_core_tables.py`,
tested applying and rolling back cleanly against a real Postgres 16).

## Known simplifications (deliberate, see model docstrings for why)

- Contacts appearing in more than one of the three Act! databases become
  **separate contact rows**, one per source database - not merged into a
  unified person. (Explicit decision, 2026-09-11.)
- Addresses/Phones/Emails attach to a Contact or a Company only - the rare
  Group/Opportunity-level ones in Act! are not migrated.
- Notes/History attach to exactly one entity (Contact or Company), even
  though Act!'s schema technically allows many-to-many - matches how the
  data is actually used in practice (verified, see schema docs).
- `Activity` rows are migrated flat, unlinked to a specific contact -
  Act!'s schema has no reliable Activity→Contact link table to migrate
  from (only a user-assignment/"cleared" table, which isn't the same
  thing). If BMI needs that link, it isn't recoverable from Act! and would
  need to be re-established in the new CRM directly.
- `Opportunity` is linked to a contact/company only where Act!'s junction
  tables had an unambiguous single link - fine given the total volume is 7
  rows across all three databases.
