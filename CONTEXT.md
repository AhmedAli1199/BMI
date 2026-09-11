# Context: BMI Sales & Data Brain — Sandbox Build Session

## Who you're working for and why this document exists
You are picking up an in-progress client project for Cybix (a small dev studio) building a replacement CRM + automation platform for a client called BMI Publishing. This document is your full context — read it before writing any code. You're working in a **sandbox repository**, not the production one — this is intentional (explained under "Your role" below).

---

## The business situation, briefly

BMI Publishing runs three magazine/media titles (Onboard Hospitality, a Prospects list, and Selling Travel) and has used **Act! CRM** for years — three separate Act! databases, one per title area. Cybix was originally hired to build a set of AI-powered sales automations *around* Act! (bounce handling, contact hygiene, AI-drafted follow-ups, a reporting dashboard, etc. — full original spec is at `docs/build-spec.txt` in the repo, but note this build **does not use n8n**, it's custom FastAPI + Next.js).

**Scope has since expanded**: BMI now wants to migrate off Act! entirely onto a custom-built CRM (the thing you're helping build), which will also serve as the platform the automations run on top of. Act! is being fully retired from this point forward, not kept as a live system of record.

---

## Where things actually stand right now (do not assume anything beyond this)

- **Act! data access:** BMI's Act! is self-hosted (not Act! Cloud SaaS as first assumed — confirmed via their IT). We obtained RDP access to their server, logged into the Act! desktop client as an Administrator, and used Act!'s built-in **File → Backup → Database** feature to produce full `.zip` backups of all three databases. These have been transferred locally and (as of this session) are being restored into a local/temporary SQL Server instance for schema exploration. **The target Postgres schema has not yet been finalized** — this is one of the first things to work on.
- **Known data volumes** (confirmed via the Act! Web API before the backup approach, real numbers not spec assumptions): ~118,000 Contacts, ~14,600 Companies, 830 Groups with ~281,000 memberships, ~165,000 Notes, ~1.61 million History records, **0 Activities, ~7 Opportunities** (these two modules are essentially unused by BMI in Act! — treat them as a green-field design opportunity, not a migration target).
- **Known schema quirks from the Act! Web API** (confirmed from real API responses): Contacts have many generic legacy custom fields named `user1` through `user15` (and similar) whose real meaning is not yet decoded — do not assume what they mean; flag them for the user to confirm rather than guessing. A few custom fields do have real names already (e.g. `bmi_notes`).
- **Xero:** A working OAuth2 "Web app" connection exists (standard authorization-code flow, refresh token stored), built via an n8n workflow that also handles token refresh on a schedule. Scopes: `accounting.invoices.read`, `accounting.contacts.read`, `openid profile email offline_access`. This is **not yet wired into the FastAPI backend** — currently lives in n8n only.
- **Mailboxes (Microsoft Graph):** In progress with BMI's IT. Plan is application permissions + client credentials flow (no per-user login), scoped to specific mailboxes via an Exchange Application Access Policy. Credentials not yet received as of this session.
- **Gemini API key:** Requested from BMI, status unconfirmed as of this document.
- **Frontend/backend scaffold:** Per the prod repo's README, the stack is already scaffolded — FastAPI (SQLAlchemy + Alembic) backend, Next.js (TypeScript, Tailwind, shadcn/ui) frontend, Postgres, Docker Compose for local dev, deployed via Dokploy. **Match this exact structure and these exact conventions in this sandbox repo** — the whole point of the sandbox is that it can be merged back cleanly.

---

## Your role in this session

You are working in `AhmedAli1199/BMI` (a sandbox copy of the real prod repo, added as the `origin` remote; the real prod repo is available as `upstream` for reference only). **Do not attempt to push to `upstream`.** Commit freely to `origin`/your own branches here — this repo is meant to be experimented in safely. When the user is satisfied with a piece of work, they will handle merging it back to prod themselves.

**Follow the existing repo's conventions exactly**, even though you can't run its Dokploy deployment from here:
- `backend/` — FastAPI, SQLAlchemy models, Alembic migrations
- `frontend/` — Next.js App Router, TypeScript, Tailwind, shadcn/ui components
- Local dev via `docker compose up --build`, matching the README's existing instructions
- Never commit `.env` files or any credential — `.gitignore` should already exclude these; verify before your first commit if anything looks off

---

## What's actually being built (the product, not just automations)

Two things, sharing one backend and one Postgres database:
1. **A basic but real CRM** — Contacts, Companies, Groups, and basic linking between them (a contact belongs to a company, contacts have group memberships), replacing Act!'s day-to-day UI for BMI's sales team.
2. **The automations layer on top** — originally scoped against Act! (see `docs/build-spec.txt`), now re-targeted to read/write your own Postgres tables instead of calling out to Act!. This includes a generic **review queue** pattern (a `review_queue` table + Next.js approval UI) that most automations funnel through — humans approve/edit before anything is finalized, per the original spec's guardrail principle ("system drafts, human sends/approves").

---

## Schema design principles already agreed (apply these, don't design from scratch)

- **Do not replicate Act!'s raw internal schema.** It's undocumented, GUID-heavy, and full of meaningless legacy field names. Use the restored SQL Server data purely as a *source*, cross-referenced against known-clean Web API JSON shapes (ask the user for these if you need to confirm a field's real meaning — they have real example payloads from earlier testing).
- **Custom fields go into a flexible `jsonb` column**, not individually-named typed columns, until we know which ones actually matter to BMI day-to-day.
- **Keep `source_act_id` and `source_db` on every migrated row** — permanent provenance, not a temporary migration artifact. This is the audit trail for "where did this record originally come from."
- **Activities and Opportunities should be designed fresh** for how BMI actually wants to track tasks/pipeline — there's no real legacy data to preserve here (0 and ~7 rows respectively), so don't let Act!'s empty/unused module shape hold you back.
- **Open decision, not yet resolved — ask the user before building around an assumption:** should a person who's a contact under more than one of BMI's three titles become **one unified contact record**, or stay as **separate per-title records**? This affects the core `contacts` table's shape significantly. Do not silently pick one — flag it.

---

## Immediate next steps for this session (in rough order)

1. Once the user provides real restored-database table/column/row-count output (they're running exploratory SQL queries against the restored backup), help design the actual target Postgres schema — proposing SQLAlchemy models + an Alembic migration, informed by that real data.
2. Build core backend CRUD endpoints for Contacts, Companies, Groups (+ membership linking).
3. Build the core frontend CRM screens: paginated Contacts list (must be server-side paginated — ~118k rows), Contact detail view (linked Company, Group memberships, Notes/History timeline).
4. Build the generic `review_queue` table + a Next.js review/approval screen — this is reused by every later automation, worth getting the pattern right once.
5. Write the actual ETL/migration script(s) that move data from the restored raw SQL Server database into the new Postgres schema — run against a throwaway database first, validate row counts and spot-check real records before trusting it, only then point at the real target database.

---

## Things to explicitly avoid in this session

- Don't write any code that authenticates to or writes into the *real* Act! system — that phase is over, Act! is being retired, not synced with.
- Don't hardcode any credential (Xero, Gemini, Graph, Postgres) — use environment variables per the existing `.env.example` pattern in the repo.
- Don't assume the cross-title contact-merge decision (see above) — ask the user if it hasn't been explicitly settled yet.
- Don't push to the `upstream` remote under any circumstances.
