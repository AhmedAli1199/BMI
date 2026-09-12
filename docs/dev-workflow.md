# Dev / staging / production — how this actually works

Three tiers, one Postgres server for staging+production (not two), no
real BMI data outside of staging/production ever.

## 1. Local dev (Claude's day-to-day, and yours)

`docker compose up --build` from the repo root, exactly as today. Postgres
here is thrown away and rebuilt constantly - never anything you need to
protect.

Instead of real data, seed it with fake data shaped like the real schema:

```bash
cd backend
python -m scripts.seed_dev_data           # adds 50 companies / 200 contacts
python -m scripts.seed_dev_data --wipe    # clears fake data, reseeds
```

Everything it creates is tagged `source_db="devseed"`, so it's never
confused with real migrated rows and never touches real contacts.

**This is sufficient for the large majority of work**: every backend
endpoint, every SQLAlchemy query, every migration, every frontend screen
can be built and verified against this without ever touching staging or
production. Claude should default to this and never ask for real
database access - it doesn't need it.

## 2. Staging (Dokploy, real-volume data, no risk to production)

Same Postgres *server* Dokploy already runs for production - a second
*database* on it, not a second server or container. This is the standard,
resource-light way to do this; a full duplicate server buys you nothing
extra here given the data volume involved (see "does this cost double
disk space?" below).

**One-time setup**, run against your Dokploy Postgres:

```sql
CREATE DATABASE bmi_staging;
```

Point a staging deployment of the backend at it (`DATABASE_URL` pointing
to `bmi_staging` instead of `bmi` - either a second Dokploy app pointed at
the same repo/branch, or just a local/your-machine backend instance
pointed at the staging connection string for a quick check, whichever is
less setup for how often you'll actually use it).

**Keeping it populated with realistic data** - two options, pick one:

- **Re-run the ETL against staging** (`migration/etl.py --pg-url
  <staging-url>`) using the same restored `.bak` files - gives you a full,
  independent copy, no dependency on production at all. Best if you still
  have the `.bak`s handy.
- **Copy from production periodically**: `pg_dump` production, restore
  into `bmi_staging`. Simpler if the `.bak`s are gone, but means staging
  data is only as fresh as your last refresh - fine for this use case
  (checking a migration or a query works before it hits prod), not fine
  if you start treating staging as a place people actually enter test data
  that needs to persist.

**When to use it**: before any change that touches the data shape - a new
Alembic migration, a change to how an automation queries/writes data - run
it against staging first with real volume, confirm timing/correctness,
then apply to production. Routine backend/frontend work that doesn't
touch the schema doesn't need staging at all; local dev data is enough.

## 3. Production (Dokploy, `bmi` database)

Real data, real credentials. Nobody develops against this directly -
Claude never has these credentials, full stop, matching CONTEXT.md. You
apply migrations here yourself (`alembic upgrade head` against the
production `DATABASE_URL`, same command as everywhere else) once a change
has been through local dev and, for schema changes, staging.

## Does this cost double the disk space?

No, not meaningfully. The `.bak` files you handled during migration were
Act!'s own bloated internal format (sync engine tables, indexes, years of
audit history) - multiple GB each. What actually landed in Postgres is a
small fraction of that: the real business data across all three
databases (contacts, companies, groups, filtered notes/history,
activities, opportunities) comfortably fits in well under 1GB total. A
second copy of that on the same Postgres server for staging is a rounding
error on any real hosting plan - not worth re-architecting around.

If staging data volume ever *does* become a real concern (it won't at
this scale), the fallback is a staging database seeded with a random
sample (e.g. 10% of contacts and everything linked to them) instead of a
full copy - not needed now, mentioned here only so it's not a surprise
later.

## CI safety net

`.github/workflows/backend-ci.yml` runs on every backend PR: applies every
Alembic migration up/down/up against a disposable Postgres in GitHub
Actions, then runs the dev seed script (and its `--wipe`) through it. This
catches a broken migration or a seed-script bug (foreign-key ordering,
etc.) before it's even mergeable, let alone before it reaches staging.
