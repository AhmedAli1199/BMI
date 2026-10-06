# BMI Brain — Handoff (from 30 Sep 2026 onwards)

This is the working handbook for continuing the BMI Brain build in a new
Claude session/account. Read it fully before touching code. It covers:

1. How we work (rules for commits, branches, standups, copy)
2. Project state: what's done, what's in progress, what's left
3. Everything decided since 30 Sep (renewals, rate card, Stage 4, cost lines, notes, Xero, proposal builder plan)
4. Business rules and data logic we settled (order register / SOR, commission, invoicing, renewals)
5. The UI/UX rulebook — theme, patterns, "de-slop" rules, copy rules — **follow it for anything new**
6. Dev environment, testing and deploy runbooks
7. Open questions / what BMI still owes us

Other docs you must also know about:
- `CONTEXT.md` — what the project is.
- `docs/build-spec.txt` — the client spec (automation IDs CS-00x / SALES-0xx, acceptance tests).
- `docs/bmi-open-questions.md` — the live list of questions for BMI (open + answered). Keep it updated.
- `BACKLOG.md` — older backlog + the original "de-AI-slop" notes.
- `.claude/skills/` — vendored UI skills (shadcn rules, web-design-guidelines, webapp-testing). Use `shadcn/rules/styling.md` as an audit checklist.
- `frontend/AGENTS.md` — Next.js 16 is NOT the Next.js in your training data; read `node_modules/next/dist/docs/` before writing Next code.

---

## 1. How we work (non-negotiable)

- **Branch:** all work goes to `ui-polish-revamp` (push with `git push -u origin ui-polish-revamp`). Not `main`, not the session's auto-named branch, unless Ahmed says otherwise. Don't open PRs unless asked.
- **Commit messages:** descriptive, plain English. End with the attribution trailer your session gives you. **Never put a model name/ID in commits, code or comments.**
- **Before every commit/push:** backend `pytest` (full suite), frontend `npx tsc --noEmit -p .`, eslint on changed files, relevant Playwright e2e, and a live look in the browser for UI changes. Chain commands with `&&` (we once committed after failing tests because `;` didn't stop).
- **Standups:** plain language, written for Ahmed's team lead / BMI, who don't know our internal labels. No "Track A/B", no "Phase 3", no file names. Format: **Done today** (what a user can now do), **Next**, **Waiting on BMI**. Concise. When asked for "tomorrow", make it concrete and numbered.
- **Messages to BMI:** short, friendly, no jargon. WhatsApp messages = 3–5 lines max.
- **Ask vs act:** Ahmed likes a plan first for big things ("tell me the plan, then build"). For fixes and clear asks, just build it. When he says "go all in", build everything in one go but keep UX polished.
- **Honesty:** if something isn't built, tested against real systems, or is an inference (e.g. the 2% commission rate), say so explicitly. When the data contradicts an earlier claim, correct it openly (we did this for "commission on invoiced amount" — wrong, reverted).
- **AI chat ("Ask the Brain") is deliberately postponed** until everything else is built — it needs careful planning. Don't start it without Ahmed's go-ahead.

---

## 2. Project state (as of 3 Oct 2026)

Spec stages and status (IDs from `docs/build-spec.txt`):

| Stage | Automation | Status |
|---|---|---|
| 1 Clean foundation | CS-001 bounces, CS-002 out-of-office, CS-003 departures (via auto-replies; no LinkedIn research), CS-004 duplicates, CS-005 returned copy, SALES-001/002 business cards | **Done (7/7)** |
| 2 Living memory | SALES-010 email summaries, SALES-011 inbound capture | **Done** |
| | SALES-008 call notes | Left — needs Teams/Zoom transcripts |
| | SALES-009 proposal logging | Left — build together with SALES-020 |
| | AI Hub chat | Left — postponed to the very end |
| 3 Daily engine | SALES-012 triggers, SALES-013 morning queue, SALES-005 touchpoints, SALES-021 renewals | **Done** |
| | SALES-020 proposal builder | **Next / in progress (plan in §3.7)** |
| | SALES-022 template library + save-the-sale | Left (mail-merge templates are a start) |
| | SALES-023 meeting notes → pitch | Left |
| 4 Reporting | SALES-026 dashboard, SALES-028 weekly summary + alerts | **Done** (delivery by email/Teams waits on BMI) |
| | SALES-024 prospect pipeline, SALES-025 chase lists | Left (024 first, it unblocks 025) |
| | SALES-027 delivery tracking | Left — needs BMI's delivery stages/timings |

Built outside the spec (from BMI's Act! feedback): Sales Order Register (replaces their SOR spreadsheets), mail merge (Outlook / Word / labels / data), contact lookup + sort, groups from selection, Excel export, duplicate contact, reminders + notification bell, Xero payment status, event costs, edition notes.

Not started from the Act! feedback list: **#2** "Key info" box + "Ad agency" field (blocked: need one example contact from BMI), **#3** Editorial / Management roles (blocked: BMI deciding who), **#7** company address change → "also update these N contacts?" (unblocked).

Also deferred by Ahmed: "BMI Brain" wordmark at the top (skip), fresh Act! migration before go-live (later), rate card data load (later — waiting on BMI).

Recent commits (newest first): `1dcbe3c` Xero · `aa12325` event costs + notes · `1183120` SALES-021 renewals · `78f49d0` SALES-028 · `afcc235` SALES-026 · `296fefc` shared mailboxes. Migrations up to `0030_xero`. 144 backend tests passing.

---

## 3. Decisions since 30 Sep

### 3.1 Work done on the other account (30 Sep)
- Shared mailboxes BMI confirmed are configured: bounce/OOO scanning covers the three shared mailing inboxes; inbound capture covers `enquiries@` (`backend/.env.example`, `docs/bmi-open-questions.md`).
- **SALES-026 dashboard** (`/sales/dashboard`, `app/sales/analytics.py`, `weekly-chart.tsx`): how each issue/event is selling vs **the same point last cycle** (matched by equivalent edition, not calendar date), weekly booking flow, team activity, "unattributed bookings" flag. **Explicitly not a league table / ranking / target tool** (spec's cultural rule).
- **SALES-028** (`app/automations/management_reports.py`, `/sales/summaries`, `app/models/management.py`): daily rule-based "behind last cycle" alert (ignores thin data, no repeats) + Monday one-page brief. Every figure comes from the order register; AI wording containing a number not in the source data is thrown away. Both off by default. Delivery is in-app only until BMI gives automation@ mailbox + Teams webhook.

### 3.2 Renewal outreach (SALES-021) — what it does and the gaps we fixed
Every weekday it reads the order register; for each title it finds advertisers who booked last year and haven't rebooked this year. Starting `sor_renewal_lead_days` (60) before the anniversary of last year's booking, it queues **one review item per advertiser per title per year**, with a drafted renewal email. It never sends on its own.

Card fields: headline (who, title, last year's spend), Advertiser (name as in SOR), Last booking (size, edition, date), Spent with this title last year, Their salesperson, Draft (AI-drafted / Templated fallback), **Draft email** (renamed from "Original message").

Fixes shipped in `1183120`:
| Gap | Now |
|---|---|
| No price | **Sales Orders › Rate card** page (`SalesRate`, per title + year + product). Draft quotes this year's price for the same product; if none, card says "Not on the 2026 rate card" and the draft mentions no price. **AI must never invent prices, dates or figures.** |
| No link to last year's ad | Each title has link patterns (`SalesTitle.digital_issue_url` / `digital_page_url`, set on Rate card page, placeholders like `{edition}`, `{page}`); each edition can override with `SalesEdition.digital_url`. Draft links to the exact page if the page number is known, else the issue. |
| Only anniversary-triggered | **Start renewals** button on an edition: drafts for everyone in last year's equivalent edition who hasn't rebooked. Shares a dedupe key with the anniversary scan → nobody approached twice, safe to re-run. |
| Anyone could action any item | Routed to **the rep who sold it last time** (their "My list" on Today + "N renewal emails ready" notification). Falls back to the company owner if the rep has no linked login. |
| Approve only logged a note | **Send from my Outlook** (edit dialog, pre-filled changeable recipient, sends from rep's mailbox, logs "Renewal sent"). **Log to CRM only** kept. |
| No re-check | Before log/send it re-checks the register; if they've rebooked since, it stops and says so. |
| — | **Regenerate** picks up prices/links added later. |

Still not done: hand-off of un-approached advertisers to a wider campaign (no campaign tool yet; mail merge could cover it); sending needs BMI IT's Outlook setup.

**Rate card entry:** manual today (≈5–10 rows per title, once a year). Offered: Claude loads it from BMI's media pack, or build an "Upload rate card" AI-extract-then-confirm button. Ahmed said: later.
**Digital links:** one pattern per title, not per issue (~17 entries). Two example links from BMI are enough to write them.
**Rep ↔ login linking:** automatic, by matching the salesperson's email (`app/sales/reference.py` REPS) to a login with the same email. Ahmed confirmed live logins are set up.

### 3.3 BMI email thread (8–25 Sep) — agreed items
- Load back-dated SORs for the AI chat → done (2023–2026 imported).
- **Optional event cost lines** in the register (Saad agreed 8 Sep) → done (§3.4).
- **General notes per publication/event/project** (Matt, 8 Sep) → done (§3.5).
- Xero: Matt shared the `integration@bmipublishing.co.uk` login → integration built (§3.6).
- They like "BMI Brain" as the name and the report-style look we sent.
- Proposals: **keep it simple — three Word templates**, one per core product (Onboard Hospitality, STM/Selling Travel, TBTM). Sent examples promised.
- Prospects549 stays **one database**.
- No Act! database is linked to enquiry mailboxes today; old Wufoo subscription forms under review.
- Editorial access: BMI deciding.
- Reps will test everything (incl. mail merge) before Act! switch-off; we'll do a fresh migration before go-live.
- Gemini API key + billing: Clare didn't understand; Saad sent a non-technical guide ($15–20 starter budget). Still unconfirmed.

### 3.4 Event cost lines (`aa12325`)
- **Why they were skipped before:** the importer only read booking rows and deliberately ignored the free-form cost block under them (no fixed layout, risk of fake bookings). Plus a bug: any heading containing "contracted" matched the contra rule → 117 fake £0 bookings. CONTRA regex is now `\bCONTRA\b`.
- **Where cost blocks exist:** only the events workbooks — STM Connect Events, Selling Travel Events, TBTM Events (2023–26). TBTM has a full P&L layout.
- **Rules** (`sor_import.cost_lines`): only labelled rows; amounts read only from the £ column (so running totals in other columns aren't counted); labels starting `£…` and anything matching total / event profit / % of profit / plus|inc|ex VAT become **summary** ("sheet total", greyed, never summed); income/revenue/sponsorship → **income**; day/venue headings (anchored date regex) → **sections** with subtotals; other text → note.
- **Profit = booked value − cost lines.** Sheet totals are reference only. Income lines are shown but not added to profit (usually the same money as bookings).
- Model `SalesEditionCost` (kind cost/income/summary/note, label, amount_gbp, amount_inc_vat_gbp, section, sort_order, `source_row` NULL = added in app). UI `components/sales/edition-costs-panel.tsx` on the edition page, rendered in sheet order, add/edit/remove.
- **Re-import (`--replace`) preserves** notes, digital_url, targets and app-added cost lines (keyed on title + year + edition name).
- Current import: 4,616 bookings, 445 editions, 521 cost lines.

### 3.5 Edition notes
Free-text notes per edition (`SalesEdition.notes`, `components/sales/edition-notes.tsx`), saved via `updateEdition`, kept through re-import.

### 3.6 Xero integration (`1dcbe3c`) — read-only
- OAuth2 "Web app" auth-code flow. Admin clicks **Connect Xero** in Settings › Integrations, signs in (integration@ login), picks BMI's organisation. We store only an encrypted refresh token (Fernet via `MAIL_TOKEN_KEY`). Xero rotates refresh tokens on every use and expires them after 60 days unused — the hourly sync keeps it alive.
- Job `xero_invoice_sync` (cron `20 * * * *`, setting "Xero" group) pulls sales invoices (`Type=="ACCREC"`, since `XERO_SYNC_FROM`, default 2023-01-01) changed since last sync (`If-Modified-Since`, 5-min overlap) into `xero_invoices`. **Nothing is ever written to Xero.**
- Matching to bookings: by invoice number, ignoring spaces and case (`number_key`).
- Payment state per booking: `voided` (VOIDED/DELETED) → `paid` (amount_due ≤ 0) → `overdue` (due date passed) → `part_paid` (amount_paid > 0) → `unpaid`; plus `not_in_xero` (has invoice number, no match — usually a typo). Same logic in SQL (`order_query.xero_state`) and Python (`_xero_ref`) — keep them in sync.
- UI: payment state under the invoice in the bookings table; "Payment (Xero)" filter with counts; Settings card (status, Sync now, Disconnect, Reconnect on error).
- Files: `app/models/xero.py`, `app/services/xero.py`, `app/api/routes/integrations.py`, migration `0030`, `frontend/src/app/api/xero/{connect,callback}/route.ts`, `components/xero-connection-card.tsx`, `lib/xero-actions.ts`.
- **Webhook mode (live since 5 Oct 2026):** if BMI's Xero sign-in isn't possible, an n8n workflow that already holds the Xero refresh token can hand out access tokens instead. Set `XERO_TOKEN_WEBHOOK_URL` (production https address; answers GET with `{"access_token", "expires_in"}`) and `XERO_TENANT_ID` (optional `XERO_TOKEN_WEBHOOK_HEADER` / `XERO_TOKEN_WEBHOOK_SECRET` for n8n Header Auth, `XERO_TENANT_NAME`). The app then asks n8n for a token only when its cached one expires (every ask rotates n8n's refresh token), and Settings shows "signed in through BMI's n8n workflow" with no Connect/Disconnect. **The n8n workflow must be the only thing refreshing the token.** Tested for real against BMI's Xero via the webhook: 600 invoices dated 2026 synced over two pages, incremental re-sync returned 0. Still to do: put the vars in Dokploy, add auth to the webhook, sync from 2023, check bookings match invoice numbers.
- **Env vars:** `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `APP_BASE_URL`, `MAIL_TOKEN_KEY`; optional `XERO_REDIRECT_URI` (default `{APP_BASE_URL}/api/xero/callback`), `XERO_SYNC_FROM`, `XERO_SCOPES` (default is now the granular `offline_access accounting.invoices.read accounting.contacts.read`; Xero apps created in 2026 can't use the broad `accounting.transactions` scope).
- **Setup:** developer.xero.com logged in as integration@ → create Web app → redirect URI = `https://<domain>/api/xero/callback` → set env → Connect in Settings. **Not yet tested against real Xero.**
- Not done yet: an Invoicing view "unpaid/overdue in Xero" (the filter covers it), Xero figures on the SALES-026 dashboard (paid vs booked).

### 3.6b Xero invoice matching (6 Oct 2026) - bookings link to their invoice by themselves
Finance raises the invoice in Xero; the app finds the booking it belongs to, so nobody types invoice numbers any more.
- **How a match is judged** (`app/sales/invoice_match.py`): client name (plus the name that client has been invoiced under before, learned from linked pairs), amount (invoice before VAT = booking value, or 2-4 of the same client's bookings add up to it; foreign currency converted at Xero's rate), issue named in the invoice reference/lines ("OBH 105"), and timing. Tested on BMI's own history with the numbers hidden: when it acted on its own it was right ~99 times in 100 (worst case ~95%); the first answer was right for ~86% of invoices.
- **What happens** (`app/automations/xero_matching.py`, job `xero_invoice_match_scan`, hourly at :40, OFF by default - setting "Xero invoice matching"; Run now works regardless):
  1. a booking whose typed number matches Xero gets a real link (`SalesOrder.xero_invoice_id`, source "typed"). Numbers are compared the way people write them (`app/sales/invoice_numbers.py`, migration `0032`): case, spaces, dashes, dots, slashes, `#`, a spelled-out "no." and leading zeros are ignored (`INV-0309` = `inv 0309` = `Inv0309` = `INV 309`); a different number never matches. Digits alone (`309`) match only if exactly one invoice ends in those digits. The Python and SQL versions of the rule are tested to agree - change them together;
  2. a CLEAR match (name >= 85 and a lead of 15 over the runner-up, and the booking has no typed number) is applied on its own (source "auto"): invoice number, invoiced value and date are filled in, the change goes to the booking history ("Linked automatically to Xero invoice N"), and nothing goes in the review queue (it would clutter it) - the booking's edit panel shows the link with Undo, and an undone invoice is remembered (`xero_match_declined`) so it isn't offered again;
  3. anything less clear becomes a review item (kind `sor_invoice_match`, audience sales) with the invoice and candidate booking(s) side by side and a reason it needs a person; "Yes, link this invoice" links the chosen candidate (source "confirmed"); "None of these" is remembered;
  4. invoices that fit no booking are listed on Invoicing > "In Xero, not in the register".
  Setting "Fill in clear matches automatically" (`xero_match_auto_link`) turns step 2 off so everything waits for a person. An invoice already decided (any review item, or an undone automatic link) is never offered again.
- **UI:** `components/sales/invoice-match-panel.tsx` (shown inside `ReviewItemCard` and the resolved list), booking sheet shows "Linked to Xero invoice N" with Open in Xero + Undo, bookings table / filters unchanged (payment state now prefers the real link).
- **Needs a one-off "Re-read all invoices"** (Settings > Xero card, or `POST /api/integrations/xero/sync?full=true`) so already-synced invoices get their line text.
- Migration `0031`; dependency `rapidfuzz`. Not done: matching typo'd invoice numbers is included (never auto); matching across pre-2023 invoices is not (sync starts 2023-01-01).

### 3.7 SALES-020 proposal builder — the plan (next task)
Spec: rep picks client + title → app drafts a proposal in BMI's Word template using client history, current rates, editorial plan and BMI's voice → rep edits → download or send from Outlook → logged against the client with a follow-up.

Plan:
1. Templates: Matt's three `.docx` in the BMI Drive folder (`1N2FF1Gi9H18OQ9l_dDrLsNcngeNgcRDw`, names end "Template.docx"; file ids `1uM0aMTw1ObFUzWqQeJWE04FYo5rN1Mrq`, `1-FBNNycnAl84PpK6i7qlC34L-nkrVV9X`, `1XiSdgdzUjG81z06VBUlTFMe8GSmeDAZk`). Placeholders: "Campaign/Advertiser name 2026/27" in header and footer, a sub-heading, body copy, brand website + publisher footer. Fill with `python-docx` (already a dependency), preserving formatting.
2. Inputs: client's past bookings (order register), CRM notes/history, rate card prices.
3. AI drafts **only the body**; prices always come from the rate card; never invent figures (same guard as SALES-028).
4. Rep edits on screen → download `.docx` or send via their Outlook (reuse mail-merge sender) → logs history (that's SALES-009 for proposals) + sets a follow-up reminder.
5. Missing inputs (don't block the build): editorial plan/feature list → omit section and flag; rate card not loaded → leave price section empty; voice → neutral tone until sent examples arrive.

---

## 4. Business rules and data logic (order register / SOR)

### 4.1 Data model (mirrors their sheets)
| Sheets | App |
|---|---|
| Workbook ("OBH 2026.xlsx") | **Title** + year |
| Tab ("105", "Jan 2026", "Feb Asia") | **Edition** (issue / month / event) |
| Row | **Booking** (`SalesOrder`) |
| Rep initials | **Salesperson** (`SalesRep`), auto-linked to login by email |
| Per-rep commission columns | **Credit** rows (`SalesOrderCredit`) — supports split bookings |
| Client text | client name + optional link to CRM company |

Everything else (totals, commission, renewals, invoicing lists) is calculated from bookings — nobody types totals. Statuses: **booked** (counted), **cancelled** ("CANX"/"cancelled" text), **contra** (free swap, `\bCONTRA\b`), **moved** (points to the new edition). Each non-booked status stores the sheet text that caused it (`status_reason`), shown in the UI.

Reps: SW Sue Williams, CM Craig McQuinn, KH Kirsty Hicks, SP Sally Parker, ST/S.Thompson/"Steve" **Steven** Thompson (not Susan), DW David Wilcox, ND/"Neil" Neil Dargie. L.Merrigan, D.Clare, A.Rogers, S.De Berniere, C.Blackwell = past reps without logins. "TBC" → no rep.

### 4.2 Import rules (`app/sales/sor_import.py`)
- Header row found by labels, not position (handles standard, events, awards, TBTM extra Total column, Visit USA columns).
- Skip template sheets ("TEMPLATE DO NOT COPY OVER") and duplicate "-Copy(1)" files.
- Visit USA Travel Planner pairs ("…2026.xls" working copy vs "…2026 edition.xls" final): import bookings once with the **edition file's values** and keep the working copy's notes.
- **Hidden Excel columns are ignored** for rep credits.
- If credits exceed the booking value, keep only reps named in the Salesper. column.
- **Shifted commission columns:** if a rep's credit matches neither the booking value nor the invoiced amount, credit the named rep(s) with the booking value (split equally) and keep a warning note. If credit equals the invoiced amount (part-invoiced), keep the sheet figure.
- Ticket numbers on £0 rows → `order_ref` (no ".0"), not invoice numbers.
- Text in the invoice-value cell → "Reason for difference"; amount left blank.
- Fractions stored as decimals → shown as "2/3".
- Extra sheet columns (Seats, Table no., Paid?, Reg info rec, Entries, Travel Planner…) kept in `extra`, shown under "Other details from the sheet".
- Unreadable rows imported as-is and **flagged "needs a check"** — never guessed.
- Totals check: per edition, imported sum vs the sheet's "Cumulative value". 443/445 match; the 2 DIFFs are sheet formula errors (TBTM Dinner Dec 2023; State of Washington 2025) — app is right.
- The importer reads text only — it **can't see cell colours** (a row marked cancelled only by red fill isn't caught).

### 4.3 Commission
- Default **2% of booked credit** — inferred from the sheets ("Commission payable" ÷ rep total = 2% on 343 sheets, 5% on 8). Editable per salesperson/booking. **The 2% vs 5% rule is an open question for BMI.**
- Checked and rejected: "commission is paid on invoiced amount" (data shows booked value in 60 cases vs invoiced in 10).
- Cancelled/contra/moved earn nothing. Salespeople see only their own commission; admins see all.

### 4.4 Invoicing logic
- **Invoiced %** is by value, not row count; the tile also shows "N of M paid bookings invoiced" (£0 tickets excluded).
- Differences compared **per client within an edition** (handles split invoices), rows with an invoice number but no amount = unknown (not a difference), **< £2 ignored** (rounding).
- **Unexplained difference** = differs and no reason written. **Difference explained** = a reason is written (shown on the row). Ahmed chose this simple split ("option 1") — **no "still to invoice later" total** (it wrongly counted agency-commission rows as owed). Don't reintroduce reason-grouping unless finance asks.
- "Overdue" = edition published / event run, still no invoice number.
- "Not linked to CRM" counts **bookings**; the Review Queue client-match counts **client names** that closely resemble a CRM company, max 200 per run. Approving one links all that client's bookings.

### 4.5 Automations on the register (all off by default, suggest-only)
`sor_client_match` (client ↔ CRM company), `sor_invoice_missing` (a week after publication), `renewal_due` (SALES-021). Workstream "Revenue & Orders".

### 4.6 Refreshing from the SOR sheets
`python -m scripts.refresh_sor` (in the backend container, `cd /app`): migrates, downloads SOR.zip from Drive, unzips, **stops if anyone edited bookings in the app** (safety check), clears pending client-match items, re-imports + re-matches in one transaction. Flags: `--dry-run`, `--force` (loses app edits), `--source <zip or folder>`, `--drive-id`, `--skip-migrations`. Container has no `curl` — the script uses Python. Once reps work in the app, stop refreshing (sheets retired).

---

## 5. UI/UX rulebook — follow for everything you build

### 5.1 Theme and tokens
- Three named themes via `[data-theme]` on `<html>`: **morning / evening / night** (`app/globals.css`, `components/theme-provider.tsx`). Not light/dark. Every token changes per theme, including sidebar/topbar.
- **Only semantic tokens. Never hardcoded hex/rgb or Tailwind palette colours** (`text-emerald-600`, `bg-[#132c6b]`, etc.). Use `primary`, `muted`, `muted-foreground`, `border`, `card`, `accent`, `destructive`, `chart-1..5`.
- Status colours: `--ok`, `--warn`, `--bad` (+ `-tint`). **They are not Tailwind-registered** — use `style={{ color: "var(--ok)" }}` or `text-[var(--ok)]` / `bg-[color-mix(in_oklab,var(--warn)_12%,transparent)]`. Green = good/done, amber = needs attention/more work, red = problem/overdue. Apply consistently everywhere.
- **Never colour alone** for status — always a label or icon too.
- Brand palette: navy `#132c6b`, bright blue `#0099e5`, black masthead nav — already in the tokens.
- Typography: Geist sans everywhere (serif was removed). `.editorial-title` (600, tight tracking) for page titles, `.editorial-heading` for section headings. Body 14px+; numbers `tabular-nums`, right-aligned in tables.
- Cards: `.editorial-card` or `rounded-xl border border-border/80 bg-card shadow-2xs`.

### 5.2 Anti-"AI slop" rules (the de-slop list)
- **No tinted-square icon chips** (`bg-blue-500/10 rounded-lg p-2` around an icon). Use `.brand-icon` (outlined, transparent) or a plain icon, and `.masthead-rule` (3px colour strip) for differentiation.
- No gradients, glows, drop-shadow stacks, decorative emoji, 3D charts, or "sparkle" banners. Tufte: maximise data-ink, remove anything that isn't data.
- No fake/invented numbers or placeholder metrics. Empty states say something useful ("No hard bounces in 7 days"), not a table of zeros. No nav items pointing at pages that don't exist.
- No duplicated content: one true home per thing (we removed the Command Center and duplicate automation cards because the same item lived in 2–3 places).
- Don't repeat the page title/counts inside the page body; don't stack redundant headers.
- Prefer tables with expandable rows over grids of cards on full-width pages (cards leave white space and are hard to compare).
- **3–4 headline numbers max per page**, most important top-left (F-pattern). All-time totals as small grey text, never the hero number. Show change vs previous period with colour that means good/bad for *that* metric (more new items = amber, more resolved = green).
- Charts: hand-drawn SVG (no chart library), theme tokens only, one chart per page, `<title>` tooltips, an `sr-only` text summary, `aria-hidden` on the SVG. See `components/automations/charts.tsx`, `sales/pace-chart.tsx`, `sales/weekly-chart.tsx`.

### 5.3 Layout and interaction patterns (reuse these, don't invent new ones)
- **Progressive disclosure:** keep pages scannable; detail goes behind a click (expandable table rows that lazy-load via a server action, collapsible sections closed by default, side panels/sheets for editing). Example: `components/automations/automations-table.tsx`, Queue Insights strip.
- **Info hints:** every non-obvious figure or heading gets a small (i) — `components/sales/info-hint.tsx` (`<InfoHint>…</InfoHint>`) explaining how it's calculated, in plain words. Use sparingly but consistently.
- **Tables / lists:** the declarative **data-view toolkit** — `lib/data-view/schema.ts` (`FilterDef`: search, multi, single, tristate, range, dates), `components/data-view/{data-view,client-data-view,filter-sidebar,toolbar}.tsx`. Filter sidebar on the left (drawer on mobile), removable chips, counts beside each option (facets computed with every other filter applied), click-to-sort headers (`SortableTh`), paging 50/100/250, Export of exactly what's shown. **All state in the URL** (bookmarkable, Back works). Server-filtered for big tables (`app/sales/order_query.py` is the one source of truth for list + totals + facets + export), client-filtered for small ones. Example defs: `lib/sales-filters.ts`.
- **Editing:** side sheet (`components/sales/order-sheet.tsx`) or inline row editor (`edition-costs-panel.tsx`); show change history ("Show change history", `field-change-history.tsx`); destructive actions limited by role, otherwise "cancel" rather than delete.
- **Page header:** breadcrumb + title + one-line description + primary action on the right (`components/automations/hub-ui.tsx` `HubHeader`, `RangeSwitch`, `KpiTile`, `Delta`).
- **Sidebar:** collapsible sections with sub-items and count badges (amber when pending > 0, neutral at 0); section opens automatically when you're inside it (`components/app-sidebar.tsx`).
- **Buttons:** always the `Button` component; when it renders a link use `render={<Link …/>}` / `render={<a …/>}` **with `nativeButton={false}`**. Icon-only buttons need `aria-label`. Use `gap-*`, not `space-x-*`; `cn()` for conditional classes.
- **Formatting helpers:** `fmtGBP` (compact for tiles: "£1.74m", "£215k"), `fmtDate` (en-GB, "3 Oct 2026") in `components/sales/sales-ui.tsx`; `fmtCount`, `fmtPercent`, `fmtDuration` ("4h", "2d"), `fmtAgo` in `lib/automation-format.ts`. Whole-number percentages. "—" for missing values.
- **Toasts** (`sonner`) for results; show clean backend error messages (never raw dumps). Loading skeletons in the shape of the real layout.
- **Accessibility (WCAG 2.2 AA):** 4.5:1 text contrast, 3:1 for UI parts/focus rings, visible focus on every control, everything keyboard-operable, real `<table>` markup with `scope`, `aria-expanded`/`aria-controls` on expanders, labels on inputs.
- **Responsive:** works at phone width; filter sidebar becomes a drawer; avoid sideways scroll on laptop widths.
- **Server/client:** server components fetch via `backendFetch` (`lib/backend.ts`); client components call server actions in `"use server"` files (`lib/*-actions.ts`), which proxy with the API key. `params`/`searchParams` are Promises in Next 16. Downloads go through Next route handlers that proxy the backend (pattern: `src/app/api/sales/editions/[id]/export/route.ts`).
- Gate staff-only UI with `canUseAutomations(session)` / `canManageUsers` (`lib/access.ts`); enforce the same on the backend.

### 5.4 Copy rules (the jargon problem — Ahmed is strict about this)
Earlier copy was "too developer-facing". Grounded in Google / Microsoft / Mailchimp style guides, GOV.UK, plainlanguage.gov, Stripe docs, NN/g:
1. Write like a knowledgeable colleague at their desk. Clear beats clever.
2. Active voice, present tense, "you". One idea per sentence. Short.
3. Target reading level grade 6–8. Concrete words and real examples ("waits 3 days", not "after the configured delay").
4. **Never show internal names** (setting keys, kinds, table names, job ids, "SOR", "payload"). Say "order register", "the scanner that reads replies", etc.
5. Define a term in one plain sentence the first time it appears on a page; no unexplained acronyms.
6. Buttons say exactly what happens ("Yes - link all their bookings", "Send from my Outlook", "Log to CRM only"). For AI actions, say what gets written where.
7. Sentence case. Lists/tables for anything with more than one fact.
8. Same rules for chat replies to Ahmed and for messages to BMI.
9. Help content structure (Diátaxis): What it is (one sentence) → How it works (numbered steps) → Settings table (plain name | what it controls | example) → What each button does.

### 5.5 Before shipping UI
`npx tsc --noEmit -p .` → eslint on changed files → Playwright check in the browser (all three themes for visual work) → screenshots to Ahmed for bigger UI changes → e2e for user flows (`frontend/e2e/`, temp specs `e2e/_tmp-*.spec.ts`, delete after).

---

## 6. Dev environment and runbooks

- **Stack:** FastAPI + SQLAlchemy 2 + Alembic + Postgres (`bmi`, tests on `bmi_test` with SAVEPOINT per test); Next.js 16 App Router + Base UI/shadcn + Tailwind 4. Deployed on **Dokploy**; Claude has no access to live servers/DB — give Ahmed exact commands to run in the backend container (`cd /app`).
- **Local:** `service postgresql start` (check `pg_isready -h localhost -q`); `PGPASSWORD=postgres psql -h localhost -U postgres`. Backend: from `backend/`, `(setsid nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 < /dev/null &)` — no `--reload`, restart after backend changes. Frontend: from `frontend/`, `(setsid nohup npm run dev > /tmp/next.log 2>&1 < /dev/null &)`. `pkill` returns exit 144 — then start again. `rm -rf frontend/.next` if stale route types break tsc.
- **Migrations:** apply to both `bmi` and `bmi_test`. Live: `alembic upgrade head` (refresh_sor also migrates).
- **Patterns:** scheduled jobs via `register_job(ScheduledJob(id,label,description,cron,func,enabled_flag))`, enabled flag on `Settings` + `AutomationSettingDef` in `settings_registry.py`; every run recorded in `automation_job_runs`. Review items via the registry (`ReviewKind`/`ReviewAction`, handler `(db, item, action_id, input_data)`); workstreams defined once in `app/automations/workstreams.py`. Identity via `app/core/identity.py`; roles admin / data_manager / sales (`CAN_USE_AUTOMATIONS` = admin + data_manager). Field edits audited (`record_field_changes`). Tokens encrypted with `app.services.outlook.encrypt/decrypt`; OAuth state via `outlook.make_state/read_state`. Make external calls stubbable (e.g. `xero.fetch_invoices`) and test with monkeypatch.
- **Playwright:** Chromium at `/opt/pw-browsers/chromium`; login via `e2e/helpers`. Clean up leftover E2E test data if specs flake (the groups test doesn't clean up after itself — known follow-up).

### Live env vars (summary)
`APP_BASE_URL`, `MAIL_TOKEN_KEY` (Fernet), `GRAPH_TENANT_ID/CLIENT_ID/CLIENT_SECRET` (mailbox scanners; Outlook sign-in falls back to these), optional `OUTLOOK_*`, `AUTOMATION_MAILBOX`, `XERO_CLIENT_ID/SECRET` (+ optional Xero vars above), LLM key.

---

## 7. Waiting on BMI (keep `docs/bmi-open-questions.md` in sync)
1. **IT – Outlook sending:** on the existing app registration add redirect `https://<domain>/api/outlook/callback`, delegated `Mail.Send`, `User.Read`, `offline_access`, grant admin consent.
2. **IT – automation@ shared mailbox** + app-only Mail.Send restricted by an Application Access Policy to that mailbox.
3. **Teams incoming webhook** (summaries/alerts).
4. **Xero app** registered at developer.xero.com (client id/secret).
5. **Rate card per title** (sizes/packages, VAT, discounts).
6. **Editorial plan / features list** per title (issue dates, deadlines, themes).
7. **Digital edition links** (past issues or the link pattern; one issue link + one page link).
8. **3–5 sent proposals** (voice for SALES-020).
9. **Commission rule** (2% vs 5%).
10. Reps' pipeline spreadsheets (SALES-024); delivery stages/timings/owners (SALES-027).
11. One contact with the "useful box" and "Ad agency" filled in; editorial logins (names + read/edit).
12. Gemini API key + billing (offer Clare a 10-min call); branding files; mailbox list + Wufoo outcome; Teams/Zoom transcripts (SALES-008); "proposal sent" pattern (SALES-009); successor research method (CS-003).

**WhatsApp ask already sent (3 Oct):** rate card, editorial plan, digital edition links, 3–5 sent proposals.

## 8. Suggested next steps
1. Build SALES-020 proposal builder (+ SALES-009 logging of sent proposals).
2. Act! feedback #7 (company address → update contacts with opt-out).
3. SALES-024 pipeline → SALES-025 chase lists.
4. Xero figures on the SALES-026 dashboard once Xero is connected live.
5. Load rate card + link patterns when BMI sends them.
6. SALES-022, SALES-023, then (with Ahmed's go-ahead and a proper plan) the AI chat.
7. Before go-live: fresh Act! migration, `refresh_sor` on live, reps test mail merge.
