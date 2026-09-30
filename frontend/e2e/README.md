# End-to-end tests (Playwright)

These run against a real, already-running dev stack (Postgres + the
FastAPI backend + this Next.js frontend on `localhost:3000`) - they are
not a mocked/component-level suite. Start the stack first:

```bash
# Backend (from backend/, with the venv active)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/bmi \
  API_KEY=dev-only-change-me uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (from frontend/)
npm run dev -- -p 3000
```

Seed the account the specs log in as (defaults below; override with
`E2E_ADMIN_EMAIL`/`E2E_ADMIN_PASSWORD` env vars if you seed a different
one):

```bash
cd backend
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/bmi \
  ADMIN_EMAIL=e2e-admin@bmipublishing.co.uk ADMIN_PASSWORD='E2eTestPass123!' \
  ADMIN_NAME="E2E Admin" python -m scripts.seed_admin
```

Then run the suite:

```bash
npm run test:e2e
# or, interactively:
npm run test:e2e:ui
```

If Playwright's bundled Chromium isn't downloadable in your environment,
point at a pre-installed one:

```bash
PLAYWRIGHT_CHROMIUM_PATH=/path/to/chromium npm run test:e2e
```

## What's covered

- `login.spec.ts` - wrong password stays on /login with an error; correct
  credentials land on the dashboard.
- `contacts.spec.ts` - create a contact, find it in the list, open its
  detail page, edit a field, confirm it survives a reload.
- `companies.spec.ts` - create a company, and the EntityPicker company-
  linking flow on a contact (the fix from the Sept 2026 UI pass).
- `review-queue.spec.ts` - the queue lists pending kinds; resolving an
  item removes it from the list without a manual reload. Skips itself
  gracefully once the seeded demo data it depends on is exhausted -
  create more via the Automations Hub's "run job now" or the seed
  scripts if you need repeat runs.
- `today.spec.ts` - regression coverage for the Sept 23 demo /today
  crash (`backend/app/automations/morning_queue.py`'s missing `Company`
  import) at the full page level, mirroring
  `backend/tests/test_morning_queue.py`'s API-level coverage of the same
  bug.

## A gap found while writing these (fixed)

Resolving a review item that fails validation on the backend (e.g. a
`signal_trigger`/`personal_touchpoint_due` item whose linked
`EmailSignal` row no longer exists) surfaced the raw
`Backend request failed: 400 /api/review-queue/... - {"detail":"..."}`
string in the error toast - developer-facing, not what a reviewer should
see. Turned out NOT to crash the page (the component's own try/catch was
already working; an earlier read of Next's server-action transport
returning its own 500 status for a thrown action was mistaken for a
broken page). Fixed in `lib/backend.ts`'s `backendFetch`: every non-2xx
response now surfaces the backend's own `detail` message (FastAPI's
standard error shape) cleanly, and logs the full status/path/body to the
server console instead - fixes this for every toast across the app, not
just the review queue.
