# BMI CRM — Backlog (not committed, local tracking only)

Running list of things identified but deliberately parked, so we don't lose
track of them across sessions. Add to this as we go; check items off or
delete them once actually done (and note it in the relevant commit instead).

---

## Performance / scalability pass — parked (2026-09-18)

Discussed but deliberately deferred to focus on automations. Concrete,
already-diagnosed findings to act on later, not vague "make it faster":

- [ ] **`cache: "no-store"` is hardcoded on every single backend fetch**
      (`frontend/src/lib/backend.ts`) — zero use of Next.js's Data Cache
      or time-based revalidation anywhere. This is almost certainly the
      actual cause of "feels slow navigating cold" more than anything
      DB-side. Fix: scope `no-store` to genuinely-always-live endpoints
      only; give read-heavy/rarely-changing ones (publications, groups,
      dashboard stats, contact/company detail) a `next: { revalidate: N }`
      and lean on the `revalidatePath` calls already in `lib/actions.ts`
      for precise invalidation on write — that plumbing already exists,
      it's just not paired with any cache to invalidate.
- [ ] **Missing composite indexes** on the actual filter+sort patterns in
      use: `contacts(source_db, last_name, first_name)` (used by
      `list_contacts`'s `ORDER BY` at ~118k rows, currently unindexed) and
      `companies(source_db, name)`.
- [ ] **Search can't use a normal index** — `ILIKE '%term%'` (leading
      wildcard) is structurally un-indexable by a plain btree. Fix:
      `pg_trgm` extension + a GIN trigram index on the searched columns.
      Small, standard, boring — the correct fix at this scale, not a
      separate search service.
- [ ] `dashboard.py`'s `get_dashboard_stats` runs ~6 sequential DB round
      trips per load — fine today, candidate for batching or (once the
      table sizes actually justify it) a scheduled-refresh materialized
      view, reusing the existing APScheduler infra from the automations
      work rather than adding new infrastructure.
- [ ] Standing habit going forward: every new FK gets an index (already
      mostly done reflexively), every new sort/filter column gets one
      matched to the real query shape, not just individually.
- [ ] Longer-term, only once row counts justify it: keyset/cursor
      pagination instead of offset-based for anything approaching
      infinite-scroll or bulk export; connection pool sizing check once
      concurrent usage is real.

## Next Up: Act!-Style "Add Activity" Modal & Full Creation Flow

Target: Replace the basic scheduling tab in `log-interaction-dialog.tsx` with a dedicated, high-fidelity **"Add activity" modal** matching Act!'s desktop/web experience as shown in the Act! specification screenshot.

### 1. UI / Layout Specification (`components/add-activity-dialog.tsx`)
Modal Header: "Add activity" title with top-right action buttons (`Save` [primary brand blue], `Cancel` [outline]).

- **Section 1: 🕒 SCHEDULING**
  - **Activity type**: Dropdown (`Meeting`, `Call`, `To-do`, `Appointment`, `Personal activity`, `Vacation`).
  - **Title / Regarding**: Combobox / input with preset recent subjects or free text.
  - **Make activity private**: Checkbox (`is_private: boolean`).
  - **Duration**: Dropdown (`10 Mins`, `15 Mins`, `30 Mins`, `45 Mins`, `1 Hour`, `2 Hours`, `Half Day`, `All Day`). Automatically synchronizes `end_at = start_at + duration`.
  - **Start date/time**: Date picker (`DD/MM/YYYY`) + Time picker (`HH:MM`).
  - **End date/time**: Date picker + Time picker (auto-adjusted when start time or duration changes).
  - **Scheduling toggles**:
    - `[ ] All day activity`: Toggles full-day duration.
    - `[ ] Timeless`: Toggles `is_timeless`, disabling specific hour/minute selection.
  - **Recurrence**: Dropdown (`Never`, `Daily`, `Weekly`, `Monthly`, `Yearly`).
  - **Priority**: Dropdown (`High`, `Normal`, `Low`).

- **Section 2: 👥 CONTACTS**
  - **Organizer**: Dropdown with info icon (defaults to current user / `BMI Administrator`).
  - **Invite**: Tag-based multi-autocomplete input ("Start typing") for internal team members + **"User availability"** button.
  - **Associate with**:
    - Entity selector dropdown (`Contacts`, `Companies`, `Groups`, `Opportunities`).
    - Multi-select autocomplete tag input ("Start typing") with debounce against `/api/contacts/search`, `/api/companies/search`, etc.
  - **Create separate activity for each contact**: Checkbox (`split_per_contact: boolean`). When checked, creates independent activity records for each selected contact instead of one shared activity.

- **Section 3: 📍 ADDITIONAL DETAILS**
  - **Location**: Free-text input for physical venue, room, or dial-in link.
  - **Resources**: Dropdown for conference rooms or equipment.
  - **Description**: Rich-text / formatted editor toolbar (Font family, font size, text color, bold, italic, underline, strikethrough, alignment, bulleted/numbered lists).
  - **Attachment**: Drag-and-drop file upload zone ("Drag and Drop file here") with "Select file" button.

### 2. Backend Schemas & Route Enhancements
- **Schema (`backend/app/api/schemas.py`)**:
  - Update `ActivityCreate` to accept:
    - `activity_type: str`, `subject: str`, `details: Optional[str]`, `location: Optional[str]`
    - `start_at: Optional[datetime]`, `end_at: Optional[datetime]`, `duration_minutes: Optional[int]`
    - `is_timeless: bool = False`, `is_private: bool = False`, `priority: str = "normal"`, `recurrence: Optional[str] = "Never"`
    - `organized_by_name: Optional[str]`
    - `contact_ids: list[UUID] = []`, `company_ids: list[UUID] = []`, `group_ids: list[UUID] = []`, `invitee_names: list[str] = []`
    - `split_per_contact: bool = False`
- **Route (`backend/app/api/routes/activities.py`)**:
  - Update `POST /api/activities`:
    - Handle transactionally: if `split_per_contact` is true and multiple `contact_ids` are passed, loop and insert an `Activity` per contact.
    - Otherwise, insert one `Activity` and bulk insert into `activity_contacts`, `activity_companies`, `activity_groups`, and `activity_invitees`.
  - Add attachment metadata endpoint `POST /api/activities/{id}/attachments`.

### 3. Frontend Actions & Integration
- Update `createActivity` in `frontend/src/lib/actions.ts` with full payload typing.
- Replace the "Log or schedule" action button in `frontend/src/app/(app)/activities/page.tsx` and navbar with `AddActivityDialog`.

---

## Act! Calendar & Tasks Revamp & Database Migration — COMPLETED (2026-09-17 / 2026-09-18)

Successfully implemented Step 1 (Frontend), Step 2 (Backend), and Step 3 (Targeted Database ETL):

1. **Step 1: Frontend Act!-Style Calendar & Task List Table View**:
   - Built full-width, 12-column high-density data grid in `components/interactive-activity-table.tsx`:
     Done checkbox, Type icon, Date (with Overdue badge), Time/Timeless, Priority badge, Subject/Details, Contact link, Company link, Duration, Location, Attachments clip, Scheduled For.
   - Added Status filter pills (Open, Overdue [with counter], Done, All), Type filter, Priority filter, and quick text search.
   - Built enhanced detail modal in `components/activity-detail-dialog.tsx`.
   - Updated `lib/types.ts` and `lib/actions.ts`.

2. **Step 2: Backend Models & API Alignment**:
   - Added `priority` column (`"high"`, `"normal"`, `"low"`) to `Activity` model and Alembic migration `0011`.
   - Exposed `priority`, `duration_minutes`, `organized_by_name` on `ActivityOut`.
   - Added query filters for `priority`, `activity_type`, and search `q` on `GET /api/activities`.

3. **Step 3: Database ETL & Act! Backup Backfill (Live on Remote Postgres `169.58.1.97:55432`)**:
   - Restored Act! backups into native Windows SQL Server 2022 via ODBC (`migration/restore_bak.py`):
     - `OnBoard` (57 activities)
     - `SellingTravel` (3 activities, restored in 3.3s)
     - `Prospects` (14.6 GB BAK, 2,071 activities, restored in 70.4s)
   - Extracted true Act! priorities from `TBL_ACCESSOR_ACTIVITY` + `TBL_ACTIVITYPRIORITY`.
   - Backfilled all 2,131 activities with their primary contact/company links, organizers, durations, and priorities.
   - **Postgres Staging Final Live Counts**:
     - Activities: **2,131** (100% enriched)
     - Activity Contact Links: **2,412**
     - Activity Company Links: **931**
     - Activity Group Links: **2**
     - Activity Invitees: **2,157**
     - Attachments Manifests: **217**
     - Priorities Breakdown: **High: 91 | Low: 1,557 | Normal: 483**
- [x] **Record ownership as a real FK** — `Contact.owner_user_id` and
      `Company.owner_user_id` resolved from Act!'s `MANAGEUSERID` via
      `migration/backfill_owner.py` (completed 2026-09-20). Migration `0014`
      applied to staging. All 73,126 contacts and 7,618 companies with active
      salespeople now carry real foreign keys to `users.id`. Unassigned pools
      (e.g., 44k Prospects under "BMI Administrator") have raw names preserved
      in `custom_fields['_original_record_manager']`.
- [x] `TBL_ACCESSOR`/`TBL_ACCESSOR_ACTIVITY` confirmed and mapped against live
      databases. All name expressions and status values verified.

Explicitly deferred (real data, lower priority or needs its own careful
pass — not silently dropped, just not in this round):
- [ ] **Prospects-only Sage financial data**: `CUST_ContactTable1_100939`
      (1,509 contacts, 2 real fields), `CUST_SL_CONTACT_INVOICE`/
      `CUST_SL_CONTACT_SOP` + company equivalents (Sage Sales
      Ledger/Order-Processing invoice & order history synced into Act!,
      linked via junction tables). Genuine financial data — deserves a
      careful pass like SOR, not bundled in here.
- [ ] `TBL_SECONDARY` (Act!'s "secondary contact" links, ~71 rows) — small,
      low priority.
- [ ] `TBL_SYSCOLUMN`/`TBL_PICKLIST`/`TBL_PICKLIST_SYSCOLUMN` — the real
      decode layer for custom-field labels and dropdown definitions
      (multi-select vs free text, "limited to list"), vs. the current
      hardcoded `CUSTOM_FIELD_MAPS` in `migration/custom_fields.py`. Would
      make custom fields self-maintaining instead of needing a code change
      whenever Act! gains a new one — real value, but a bigger rework.
- [ ] `TBL_GROUPQUERY`/`TBL_COMPANYQUERY` + `CONTACTQUERYTEXT`/
      `OPPQUERYTEXT` — some Act! groups are **dynamic** (rule-based
      membership, not a static list); migrating only `TBL_GROUP_CONTACT`
      freezes today's members and loses the rule that maintains them.
- [ ] `TBL_COUNTRY`/`TBL_PHONEMASK` — country/phone-format reference data,
      would let us normalize the ~125k free-text `country` values and
      phone numbers to something structured (E.164 etc).
- [ ] `TBL_HISTORYTYPE_GROUP`/`TBL_HISTORYTYPE_SUPERGROUP` — Act!'s own
      2-level taxonomy above its 65 history types; worth pulling to
      sanity-check the hardcoded `HISTORY_TYPES_KEPT` list in
      `backend/app/models/history.py` and to power timeline filtering.
- [ ] `TBL_ACTIVITYSERIES`/`TBL_ACTIVITYSERIESITEM` — reusable "activity
      sequence" templates (old follow-up cadences), only in SellingTravel
      (3 series, 18 steps), never actually applied to a real record.

## SOR (Sales Order Register) ingestion

- [ ] Design + build the `sales_order` model/table, one-time Excel import,
      and CRUD UI to replace the "shared overwrite-prone Excel". Explicitly
      deferred — user said this needs its own careful pass, not bundled
      with the Step 1/2 automations work. Unblocks SALES-020/021/026/027
      once done (see automations plan below).

## Automations (scoped, approved to start with Step 1 + Step 2)

Full catalog + realistic ETAs given in-chat (2026-09-17). Build order agreed:
1. Follow-up Engine + Morning Queue (merges SALES-005/012/013)
2. Template Library (SALES-022)
3. Business Card Capture (merges SALES-001/002)
4. Returned Copy Processing (CS-005)
5. Duplicate/Moved-Person Merge (CS-004)

Blocked on IT confirming mailbox access: CS-001, CS-002, SALES-009/010/011,
SALES-025, the auto-detect half of SALES-024.

**Dependency to unblock the AI-drafting steps (#1, #2, #3 above):** app needs
an LLM API key added to the backend env (Anthropic, so vision + text drafting
both come from one provider) — not yet wired in. Currently the only two live
automations (bounce/departure) are pure rule-based, no LLM calls at all.

## Branding / "de-AI-slop" pass

Started + main sweep done 2026-09-17: pulled BMI's real palette (navy
`#132c6b` / bright blue `#0099e5`, black masthead nav) from the three
magazine sites + BMI Publishing logo, replaced the tinted-square icon-chip
pattern with an outlined icon (`.brand-icon`) + solid masthead-rule strip
(`.masthead-rule`) everywhere it appeared. Done: global theme
(`globals.css`), dashboard, `publication-style.tsx`, `automation-style.tsx`,
automations pages, `review-item-card.tsx`, contact/company dossiers + cards,
contacts table, activity timeline + detail dialog, team roster, settings,
automations review empty state. Centralized the 5x-duplicated publication
badge-color switch statement into `sourceBadgeStyle()` in `lib/sources.ts`.
Status badges (Done/Scheduled) now use the app's `--ok`/`--warn` theme
tokens instead of hardcoded emerald/amber, so they respect the
evening/night themes too (previously didn't).

Remaining:
- [ ] Haven't touched button styling (`components/ui/button.tsx`) or form
      inputs yet — still default shadcn look, not yet given the same
      masthead-derived treatment.
- [ ] Sidebar/topbar chrome now uses the new black+blue palette but hasn't
      been visually verified in a live browser screenshot yet (only
      confirmed via dev-server curl + typecheck/lint, no visual QA pass on
      any page).
- [ ] Haven't picked a custom icon set (Phosphor/Tabler/custom) — still on
      `lucide-react` throughout; the outlined-icon treatment reduces the
      "generic" read but doesn't replace the icon library itself.
- [ ] Left `publication-form-dialog.tsx` and `user-form-dialog.tsx`'s
      selected-state toggle chips (icon picker, role picker) on
      `bg-primary/10` deliberately — that's a legitimate filled "selected"
      state, not a decorative icon sticker, so didn't touch it. Worth a
      second look if it still reads generic once seen live.

## Smaller loose ends (not yet actioned)

- [ ] Calendar & Task List "Open" tab shows the full unbounded Act!
      backlog (no date-window default) — worth deciding whether to add a
      default filter (e.g. overdue + next N days) so ancient stale items
      don't dominate, and/or a bulk-triage pass on clearly-dead pre-migration
      to-dos.
- [ ] Dedicated cross-record History List page (separate from per-contact
      History tab) — gap-analysis priority #4, not started.
- [ ] Import/export UI — gap-analysis priority #5, not started.
- [ ] Opportunities UI — gap-analysis priority #6 (low priority, only 7
      real historical rows), not started.
- [ ] Reports/dashboard expansion — needs a scoping conversation with BMI
      first, not started.
- [ ] Marketing/mail merge — needs confirmation BMI even wants it, not
      started.
- [ ] Phase 2 deferred sub-features: attachments, multi-contact association
      on one History/Activity row, meeting invitees/free-busy check.
- [ ] Push to the actual org repo `eynvision/bmi-sales-brain` (only
      `origin`/AhmedAli1199/BMI used so far).
- [ ] IT's clarification on Graph app-vs-delegated mailbox permission type.
- [ ] `feat/act-ui-redesign` branch not yet merged to `main`, not yet
      deployed to Render/Dokploy — none of this session's work (including
      earlier RBAC/redesign) is live for BMI's team yet.
- [ ] Branch mismatch: this session's designated branch per the environment
      is `claude/wizardly-cannon-dlcu8m`, but that branch holds a completely
      unrelated older history (RBAC work). All actual work is on and pushed
      to `feat/act-ui-redesign`. Needs sorting out which branch is really
      the target going forward.
