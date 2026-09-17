# BMI CRM — Backlog (not committed, local tracking only)

Running list of things identified but deliberately parked, so we don't lose
track of them across sessions. Add to this as we go; check items off or
delete them once actually done (and note it in the relevant commit instead).

---

## "Nothing missed" gap-fill pass — CODE WRITTEN 2026-09-17, not yet run

Full plan + code written (models, Alembic migration `0011`, ETL updates) to
close the gap between what Act!'s `.bak` actually has and what we migrated.
**Not yet applied/run against a real .bak or Postgres — no live DB in this
environment, verified via syntax check, full module import, and Alembic
offline SQL generation only.** Run `alembic upgrade head` then re-run
`migration/etl.py` per source database against the real `.bak` to backfill.

Implemented:
- Activity ↔ contact/company/group associations + invitees (fixes the
  `contact_id`/`company_id = NULL` on all 2,131 activities — turned out
  `TBL_CONTACT_ACTIVITY`/`TBL_COMPANY_ACTIVITY` DO have real data, 2,333
  links in Prospects alone; the original "no reliable link" claim in
  `migration/etl.py`/README was wrong, corrected in both places).
- Attachments (file metadata from `TBL_ATTACHMENT` — not the actual files,
  those live on Act!'s old file share).
- `Activity.duration_minutes` (Act!'s real `DURATION` column) +
  `organized_by_name` (denormalized display name via `TBL_ACCESSOR` — NOT
  a `users` FK, see below).
- Notes/History widened to also cover Group and Opportunity entities
  (`TBL_GROUP_NOTE`/`TBL_GROUP_HISTORY`/`TBL_OPPORTUNITY_HISTORY` — ~1,200
  rows previously dropped on the floor).
- `Company.ticker_symbol`/`sic_code` — bug fix, these were selected by the
  ETL from day one but never actually written into the row dict.
- `Contact`: `company_name_freetext`, `last_results`, `is_email_opted_out`,
  `has_bounced`, `engagement_score`, `last_email_date` — the AEM/bounce
  fields directly feed the CS-001 bounce-handling automation, which
  currently has zero historical bounce signal to start from.
- `Phone.extension` (Act!'s `SUFFIX` — was being dropped on ~167k rows).
- `Opportunity.custom_fields` (USER1-8, never discovered before) +
  `stage_name` now actually populated (joins `TBL_STAGE`).
- `contact_company_links` (`TBL_COMPANY_CONTACT`) — a contact can belong to
  several companies in Act!; `Contact.company_id` only ever holds one.
  7,959 extra links in Prospects alone.
- **Fixed a real bug in the migration script itself**: `IdMap` minted a
  fresh random UUID for every row on every run, which is only correct for
  genuinely new rows — re-running against already-migrated data (exactly
  what this gap-fill pass needs to do) would've generated new junction
  rows pointing at the WRONG ids for anything migrated before. Added
  `IdMap.preload()`, seeding the map from what's already in Postgres for
  that `source_db` before any `get_or_create()` call. This is the answer
  to "how do we handle linking to already-existing records" — it's easy
  *with* this fix, and silently wrong without it (would fail loud on a FK
  violation, not corrupt data, but still wrong and now fixed properly).

Still parked for cutover (needs the Act!-accessor → our-user identity
mapping, a human decision, OR needs a live-DB column check first):
- [ ] **Record ownership as a real FK** — `Activity.created_by_user_id`
      (`ORGANIZEUSERID`), and the equivalent `CREATEUSERID`/`EDITUSERID`/
      `MANAGEUSERID` fields on Contact/Company/Group/History/Note, all
      point at Act!'s `TBL_ACCESSOR`, which has no established mapping to
      our own `users` table. `organized_by_name`/invitee names denormalize
      just the display name now (via live column discovery, since
      `TBL_ACCESSOR`'s own columns aren't in the schema docs) so they
      render correctly without waiting on this — a real `user_id` FK can
      be backfilled once the mapping exists, independent of that.
- [ ] `TBL_ACCESSOR`/`TBL_ACCESSOR_ACTIVITY`'s exact column names aren't
      confirmed against a live schema (not in docs/act-schema — filed
      under "Act! internal", never dumped). The ETL discovers the
      display-name column live and infers `TBL_ACCESSOR_ACTIVITY`'s
      columns from the extremely consistent naming convention every other
      `*_ACTIVITY` junction follows — should work, but worth a `SELECT TOP
      5 * FROM TBL_ACCESSOR_ACTIVITY` check against the real `.bak` before
      trusting it blind on a real run.

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
