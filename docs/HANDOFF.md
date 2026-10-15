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
| | SALES-009 proposal logging | **First pass done** — “I've sent it” notes the proposal on the client + sets a follow-up reminder |
| | AI Hub chat | Left — postponed to the very end |
| 3 Daily engine | SALES-012 triggers, SALES-013 morning queue, SALES-005 touchpoints, SALES-021 renewals | **Done** |
| | SALES-020 proposal builder | **Done incl. Outlook sending (§3.7), issue details from the editorial plan and rate-card offers (§3.10)** — tone-matching waits on BMI's sent examples |
| | SALES-022 template library + save-the-sale | Left (mail-merge templates are a start) |
| | SALES-023 meeting notes → pitch | Left |
| 4 Reporting | SALES-026 dashboard, SALES-028 weekly summary + alerts | **Done** (delivery by email/Teams waits on BMI) |
| | SALES-024 prospect pipeline, SALES-025 chase lists | Left (024 first, it unblocks 025) |
| | SALES-027 delivery tracking | Left — needs BMI's delivery stages/timings |

Built outside the spec (from BMI's Act! feedback): Sales Order Register (replaces their SOR spreadsheets), mail merge (Outlook / Word / labels / data), contact lookup + sort, groups from selection, Excel export, duplicate contact, reminders + notification bell, Xero payment status, event costs, edition notes.

Not started from the Act! feedback list: **#2** "Key info" box + "Ad agency" field (blocked: need one example contact from BMI), **#3** Editorial / Management roles (blocked: BMI deciding who), **#7** company address change → "also update these N contacts?" (unblocked).

**Act! user feedback #2 (Oct 2026) - "good search on every field, search results to Excel, bulk update, load contacts from Excel/PDF": ALL BUILT (B1-B4).**
- **One field list** - `backend/app/contacts/fields.py` is the single registry search, advanced filter, export, bulk update and the import matcher read. The Act! custom fields are discovered from the data and shown under their stored names ("User3") until BMI says what they mean. **To name them later:** put `{"user3": "ABTA number"}` in `CUSTOM_FIELD_LABELS` (fields.py) or `PUT /api/contacts/fields/custom` with the same JSON (admins/data managers) - every screen, export column and the import matcher pick the new name up (a column "ABTA No" then maps to it automatically). `CUSTOM_FIELD_BULK_EDITABLE` can restrict which custom fields bulk update may touch.
- **B1 search** - `services/contact_lookup.py` (the one definition shared by list, export, ids, record stepper, mail merge): the quick box matches every word in any order across names, job, department, category, company, email, phone (digits only works), address/postcode and custom-field values (notes are not in the quick box - too slow). **Advanced search** (`app/contacts/conditions.py`, `components/contacts/advanced-search.tsx`): any number of field/operator/value rules, match all or any, kept in the URL (`conds`, `match`) and carried to export, mail merge and the bulk tools. Includes notes, groups, any email/phone/address, custom fields, yes/no and date fields.
- **B2** - Excel export adds a column for every custom field that has a value; "Copy emails" (`POST /api/contacts/emails`) copies a `;`-separated list for Outlook Bcc, leaving out unsubscribed/bounced/no-email/duplicates and saying how many (warns above 500).
- **B3 bulk update** - `api/routes/contact_tools.py`: set / clear / find-and-replace on any text, yes/no or custom field, for a search or a ticked selection. Always previews ("N will change", before -> after samples), writes each change to the contact's field history, and has **Undo** (only restores contacts not changed again since). Limited to the databases the user can see.
- **B4 import** - `/contacts/import` (+ `/contacts/import/[id]`): upload xlsx/xls/csv/PDF (PDF tables via pdfplumber; no table -> the AI reads the text, flagged for checking). **Column matcher** `app/contacts/import_mapper.py` (add header phrases to `TARGETS`): normalises headings (case, punctuation, camelCase, abbreviations, typos), scores exact / "contains the words" / close spelling, also reads the values (emails, UK postcodes, phone numbers, Mr/Mrs, countries), understands numbered variants ("Email 2"), sends a second email/phone column to the next slot, and leaves genuinely ambiguous columns for the person, with candidates shown. Manual mapping per column, "new custom field", sheet/heading-line pickers, live preview. **Engine** `import_engine.py`: tidies names/emails/phones/postcodes, splits full names, finds people already in the CRM (email, else name + company), handles repeats inside the file, options (fill blanks [default] / skip / overwrite / add anyway; create companies; add to a group), review screen with filters (existing-contact links open in a new tab), commit in one transaction, **Undo** (removes what it added unless the contact has been worked on since; restores updated ones). Imported rows are stamped `source_act_id = import:<id>:<row>` and `custom_fields._import`. Tests: `tests/test_contact_import.py`, `tests/test_contact_tools.py`.
- **Still open with BMI:** which Act! custom field is the ABTA number / Type etc. (`docs/bmi-open-questions.md`).

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
- **Invoiced amount from Xero only when nobody recorded one** (`SalesOrder.invoice_from_xero`): links made by the matcher, or a typed number with the amount left blank, take Xero's amount (before VAT, in pounds) and date and follow it on every sync. An amount recorded by a person or the SOR sheets is never overwritten. (7-8 Oct the sync overwrote recorded amounts, which pushed exchange-rate gaps into Unexplained differences; migration `0039` put those figures back and logs it on each booking.)
- **Linking by hand:** booking panel > "Find in Xero" (invoices no booking has, same client / same amount first, search by number, customer or reference; `GET /api/sales/orders/{id}/xero-choices`, `POST .../xero-link`), and Invoicing > "In Xero, not in the register" > "Link to a booking" (the matcher's suggestions, then search by client; `GET /api/sales/xero/invoices/{id}/choices`, `POST .../link`). Both count as "confirmed" links (Undo available). Saving a typed number now says whether it linked ("linked to Xero invoice N · £x · awaiting payment") or isn't in Xero yet.
- Migration `0031`; dependency `rapidfuzz`. Not done: matching typo'd invoice numbers is included (never auto); matching across pre-2023 invoices is not (sync starts 2023-01-01).

### 3.6c Renewals belong to their salesperson (7 Oct 2026)
- Settings > Users: "Their initials in the order register" links a login to a `SalesRep` (one login per rep; suggested when the names match). Until a rep is linked, their renewals show as Unassigned.
- Who owns a renewal is worked out when the Today list is shown (rep who sold it last time -> their login, else the CRM company's owner), so linking a login moves the waiting renewals onto that person's list straight away.
- Today: a salesperson sees only their own items; admins and data managers see everyone's, grouped by person, with Unassigned last. Unassigned items are NOT shown to salespeople. Review Queue: a salesperson now sees only their own renewals too.

### 3.6d Access is enforced on the server (8 Oct 2026)
`app/core/visibility.py`: a person's grants (Settings > Users > Database access: a whole database, or one group and its sub-groups) are read fresh from `user_access` on every request. They limit contacts (the shared contact search, so lists, exports, lookup ids, copy emails, bulk update, mail merge), companies (whole-database companies, or the companies of contacts they can see through a group), groups, activities, the dashboard counts, the Review Queue and Today. Opening a contact, company or group outside someone's access returns "not found" (`guard_records` on those routers). Admins see everything. The Sales Order Register, rate card and editorial plan aren't limited by contact groups. Tests: `test_group_access.py`.

### 3.7 SALES-020 proposal builder — first pass built (6 Oct 2026)
**What exists:** Sales Orders → Proposals (list, `/sales/proposals/new`, `/sales/proposals/[id]`) and a "Build a proposal" button on every company page. Pick client + title (title picks the Word template OBH/STM/TBTM, changeable), add products from the rate card with quantities (or own lines with typed prices), the brain drafts five sections (Introduction, Your history with us, What we propose, Investment, Next steps), the rep edits/reorders/adds sections, previews, downloads the `.docx` in Matt's template, then "I've sent it" logs a "Proposal sent" note on the company (products + total before VAT) and sets a follow-up reminder (default 14 days). Nothing is ever sent automatically.
**Rules built in:** rate-card lines are always priced server-side from `sales_rates` (browser prices ignored); AI text is discarded per section if it contains any figure not in the client history / rate card / lines (`app/proposals/drafting.py`, same idea as the weekly summary guard) and standard wording is used; missing inputs become plain-English flags on the screen (no bookings, no rate card for that year, editorial plan not loaded) rather than invented content. Sales reps see only their own proposals; admins/data managers see all. Code: `backend/app/proposals/`, `api/routes/proposals.py`, `models/proposal.py` (migration 0033), `components/sales/proposal-*.tsx`, tests in `tests/test_proposals.py`.
**Outlook sending (done):** "Email it from Outlook" opens a draft email (contact's address, plain subject and note, all editable), sends from the rep's own connected Outlook with the Word file attached (under 3 MB), and only then logs it (note includes who it went to) + sets the reminder. A failed send logs nothing. Endpoints `GET /api/proposals/{id}/email-draft`, `POST /api/proposals/{id}/send`.
**Next passes:** BMI voice once 3-5 sent proposals arrive; reuse sent proposals as the pitch store (SALES-023). (Editorial plan + offers: done, see §3.10.)

Original plan (kept for reference):
Spec: rep picks client + title → app drafts a proposal in BMI's Word template using client history, current rates, editorial plan and BMI's voice → rep edits → download or send from Outlook → logged against the client with a follow-up.

Plan:
1. Templates: Matt's three `.docx` in the BMI Drive folder (`1N2FF1Gi9H18OQ9l_dDrLsNcngeNgcRDw`, names end "Template.docx"; file ids `1uM0aMTw1ObFUzWqQeJWE04FYo5rN1Mrq`, `1-FBNNycnAl84PpK6i7qlC34L-nkrVV9X`, `1XiSdgdzUjG81z06VBUlTFMe8GSmeDAZk`). Placeholders: "Campaign/Advertiser name 2026/27" in header and footer, a sub-heading, body copy, brand website + publisher footer. Fill with `python-docx` (already a dependency), preserving formatting.
2. Inputs: client's past bookings (order register), CRM notes/history, rate card prices.
3. AI drafts **only the body**; prices always come from the rate card; never invent figures (same guard as SALES-028).
4. Rep edits on screen → download `.docx` or send via their Outlook (reuse mail-merge sender) → logs history (that's SALES-009 for proposals) + sets a follow-up reminder.
5. Missing inputs (don't block the build): editorial plan/feature list → omit section and flag; rate card not loaded → leave price section empty; voice → neutral tone until sent examples arrive.

### 3.8 Rate card revamp (7 Oct 2026)
Sales Orders > Rate card is now one page per **brand** (OBH, TBTM, Selling Travel - `app/sales/brands.py`), laid out like the media packs: sections (print, sponsored, website, newsletter, events, awards, listings, other), click a price to change it, side panel for the full product (price type fixed / "from" / on request, unit, specs, other names it goes by, valid until), "Looks right" to clear a please-check flag, drag order, offers (volume "book N save X%", series "N entries for £Y", early bird, notes), next-year wizard (raise by %, round, per-item overrides), change history with put back, Excel download and print. Prices are before VAT.
- **Who edits:** admins + data managers everything; a publisher only their own brand (rep codes in `Brand.editors`, linked through `SalesRep.user_id`). Everyone can read.
- **Media-pack data:** `app/sales/rate_card_seed.py` holds the 2026 prices read from BMI's media packs; loaded only by the "Load from the media pack" button per brand (never by a migration). Items we inferred are flagged "please check".
- Code: `api/routes/rate_card.py`, `models/sales.py` (`SalesRate` new columns, `RateOffer`), migration `0035`, `components/rate-card/*`, tests `test_rate_card.py`.

### 3.9 Editorial plan (7 Oct 2026)
Sidebar > **Editorial plan** (`/editorial`): year planner (lanes per title, today line), deadlines list (soonest first), list view; brand chips + year switch. Each issue page (`/editorial/issues/[id]`) has key dates (editorial / advertising / copy deadlines, extra milestones, "use the usual rules"), features (paste a list, reorder, confirm/drop, mark sponsorable), details (theme, distribution, format), notes, bookings so far vs last year, and **Who should we pitch?** (§3.10). Brand settings (`/editorial/settings/[brand]`): deadline rules (N days before publication / Nth of the month before), regular sections, about text. "Plan next year" copies a brand's issues a year on (same weekday; numbered issues continue).
- Issues ARE order-register editions (`SalesEdition`, kinds issue/guide/event/awards), so an issue's plan and its bookings live together; order-register re-import keeps plan fields and features.
- **Published plan data:** `app/sales/editorial_seed.py` (OBH 105-108 + Awards 2027, TBTM issues/guide/digital specials/Dinner Clubs/Lunch Forums/Awards; Selling Travel still missing), loaded by the "Load the published plan" button. Dates worked out from rules or estimated are flagged "please check".
- Same edit rights as the rate card. Code: `api/routes/editorial.py`, `app/sales/editorial.py`, models `EditionFeature`, `EditorialSetting`, migration `0036`, `components/editorial/*`, tests `test_editorial.py`.

### 3.10 Rate card + editorial plan hook-ups (7 Oct 2026)
- **Proposals:** each proposal is for an issue (`proposals.edition_id`, migration `0037`). If none is chosen, the title's next issue still open for adverts is picked and flagged. The issue's date, advertising deadline, theme and features go into the wording (template and AI; the AI figure guard knows the issue facts) and the next steps ("copy and artwork are needed by ..."). The issue can be changed on the proposal (then Redraft). "Pitch this issue" on an issue page and "Draft a proposal" in Who should we pitch? open `/sales/proposals/new?edition=...(&company=...)`.
- **Offers:** `app/sales/offers.py` applies the brand's rate-card offers to rate-card lines on every save - each becomes a read-only negative line ("Offer: ...") shown in green and in the Word file as "-£60.00". Lines remember their `rate_id`. Expired offers are skipped; a rate past its "valid until" is flagged.
- **Renewal emails:** the draft names this year's counterpart of the issue the advertiser booked (or the next open one), with its date, deadline and up to three features; the review card has an "Issue to offer" row that opens the issue in a new tab (`ReviewDetail.href`).
- **Who should we pitch?** (`GET /api/editorial/issues/{id}/pitch`): last year's equivalent issue's advertisers not yet rebooked, the previous issue's advertisers, and past advertisers (3 years) whose company name/industry/category matches a planned feature's words. Company names open in a new tab.
- **Advertising deadline reminders** (`app/automations/editorial_deadlines.py`, job `editorial_deadline_alerts`, 07:15 daily, OFF by default - setting "Advertising deadline reminders", days "14,7,1"): an in-app notification to the brand's publishers and anyone who sold that title in the last year, with bookings so far and how many of last year's advertisers haven't rebooked; once per issue per reminder day.
- Tests: `test_editorial_hookups.py`.
- **Deploy:** `alembic upgrade head` (migrations `0035`-`0037`) and `pip install -r requirements.txt` (adds `pdfplumber` for the contact import).

---

- **Wording follows Matt (12 Oct):** on screen, a "booking" is the whole multi-item thing (code: `SalesDeal`, `/sales/deals`) and each line in an issue is an "item" (code: `SalesOrder`, `/sales/orders/[id]`, list at `/sales/bookings` titled "All items"). Code names are unchanged. "Order confirmation", "Order no." on the printed confirmation and the "Sales Orders" section keep their names. Renewals' button is now "New booking", opening the booking form for the company (prefilled from their last booking, set to the chosen edition); unlinked advertisers still get the single-item sheet. Easy to switch back if BMI prefer other words.

- **Call notes / Notetaker (13 Oct):** a separate, reusable service lives in `notetaker/` on the `notetaker` branch (FastAPI + self-hosted Attendee bot + Gemini notes; README there covers the API, webhooks and Dokploy set-up). BMI Brain's side: `/calls` page and `/calls/[id]`, `app/api/routes/calls.py`, model `CallRecording` (migration 0048), review kind `call_notes` ("Save to history" writes a "Meeting Held" history entry plus a reminder per action item). The service posts results to the public frontend route `/api/notetaker/webhook`, which forwards to `/api/calls/webhook`; the backend checks the HMAC signature. Backend settings: `NOTETAKER_URL`, `NOTETAKER_API_KEY`, `NOTETAKER_WEBHOOK_SECRET` (the button is hidden until set). Not done yet: calendar sync / automatic joining (needs `Calendars.Read`), Zoom.

- **Shared calendar + automatic notetaker (14 Oct):** `/calls/meetings`. People connect Google and/or Outlook calendars (read-only; Outlook is its OWN grant `offline_access User.Read Calendars.Read` on the same Azure app and callback - never add calendar scopes to the mail sign-in, it would break existing mail tokens). Logic in `app/services/calendar_sync.py`: meetings from several calendars merge on (normalised Meet/Teams/Zoom room, start minute), else calendar UID + start; a moved meeting becomes a new row and the old one is cancelled (one-off Record/Skip carried over). `should_record` gives plain reasons; per-person preference `calendar_recording` (auto / remind / off), company settings in Automations → "Call notes". Job `calendar_sync` every 3 min books bots ~20 min ahead (join 1 min early), calls them off on skip/cancel/move, joins late-added meetings up to 30 min in. Tables: migration 0049. Google needs `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (redirect `{APP_BASE_URL}/api/google/callback`).
- **Notetaker line, check and fresh start (15 Oct):** each meeting now says what actually happened, not just what the rules want: `calendar_sync.outcome(m, call, decision)` gives `{tone, text}` (past tense once a meeting is over - recorded, not let in, failed with the reason, booked but never joined, never sent, or the rule that stopped it). `last_error` is kept after the meeting ends. Admins get a "Notetaker check" side sheet on `/calls/meetings` (`GET /api/calendar/health`: notetaker reachable with its key via `/v1/capacity`, webhook secret set, `calendar_sync` job on and running in the last 15 min, each calendar's last read, and meetings missed in the last 7 days with why) and a "Clear meeting history" button (`POST /api/calendar/start-over`, `calendar_sync.start_over`): removes every meeting and attendance, calls off booked bots, deletes calls that never recorded, keeps recorded calls (unlinked) and all connections, then reads the calendars again.

- **Accounts approval (14 Oct, Matt: only Samantha changes or approves bookings):** users have an **Accounts** permission (`users.can_approve_bookings`, Users → edit person; migration 0050). Rules in `app/sales/accounts.py`: once anyone has it, only accounts people see/act on the `order_check` card and the new `booking_change` card (review kinds with `approver="accounts"`, filtered in review_queue `_visible_kinds`), and a checked booking is locked for everyone else (setting "Only accounts can change checked bookings"). Salespeople use **Request a change** (the edit form in request mode, or "Ask accounts to cancel it"); `app/automations/booking_changes.py` shows before → after and knock-ons (issues it leaves/joins, already-invoiced items needing a credit note), and Approve applies it exactly as asked and keeps the booking checked. Until nobody has the permission, behaviour is as before (managers check, no lock). Bookings settings has **Production** and **Accounts** emails, always CC'd on every confirmation sent.
- **From Matt's "Sales and accounts" doc (14 Oct), migration 0051:**
  - **Items still to be allocated (packages).** A placement can be `{"tba": true}` with no issue: it's priced and in the booking total, prints as "date to be confirmed", but makes no order-register item until an issue is chosen (`app/sales/deals.py` `is_unallocated`, `set_allocation`; the booking keeps `unallocated_count`, `unallocated_gbp`, `allocate_by`). The form has "+ To be allocated" and a "Decide the issues by" date per line; the booking page shows a banner; the Bookings list has a "Still to allocate" filter and the unallocated total. Review kind `allocation_due` (`app/automations/allocations.py`, daily job, off by default) reminds the salesperson as the decide-by date or the title's next booking deadline gets close; it closes itself once allocated. On a locked booking, allocating goes through Request a change like any other change.
  - **Accounts hear about every new booking** (setting on by default): a bell note for each accounts person, and the confirmation (Word file) emailed to the Accounts addresses in Bookings settings from the automation mailbox (`app/sales/accounts.py` `email_new_booking`, run after the response; needs the automation mailbox set up).
  - **Online booking forms** (Jotform, Stova): Bookings → Online forms (managers). Each form gets a secret public address (`/api/booking-forms/{token}`, forwarded by the frontend to `/api/sales/booking-forms/receive/{token}`). Jotform posts its webhook form (answers in `rawRequest`); anything else can post JSON. Each entry is a review card `online_booking` (`app/automations/booking_forms.py`) with the answers, the company/name/email/how-many picked out and the client matched to the CRM; "Create booking" makes a pencilled booking (issue from the form, or to be allocated) that goes to the accounts check. Stova: needs to know whether it can send webhooks or only exports.
  - **Issue gone to press check** (`sor_issue_check`, `app/automations/sor_checks.py`, daily job, off by default, accounts only): a few days after an issue's copy deadline, one card listing items with no booking behind them, items that don't match their booking, pencilled items, unsent confirmations, packages for that title still to allocate, plus filler ads and items still to invoice.
  - **Filler ads**: `sales_orders.filler`, a tick box on the item, and a "Filler ads" filter on All items / issue pages. What Matt wants tracked about them is still to confirm (the doc's note stops at "Keep a track on").
  - Not done: delivery stages (needs the call with Matt and Samantha); prospect pipeline import (needs their spreadsheets).
- **Proposals, parts 1 and 2 of the plan agreed 14 Oct (from Kirsty's six example proposals), migration 0052:**
  - **Proposal requests** (review kind `proposal_request`, `app/automations/proposal_requests.py`, job every 10 min, off by default). Reads the inboxes in Automations → Settings → Proposal Requests → "Inboxes to read" (start with Kirsty's) using the same app-only Mail.Read as the other scans. Free checks first (not the owner's own mail, not automatic/bounce/OOO/newsletter, internal mail only when it's a passed-on enquiry, at least one price/rate/media pack/proposal word), then the AI classifies and picks out magazine, wants, budget, timing, agency, client, sector. The card goes only to the inbox owner (`owner_user_id`; managers see all) with a reply drafted from the rate card (a few products per thing asked about) and the editorial plan; the AI may only write the opening sentence and it's dropped if it adds a figure. Send replies in the thread from the person's own Outlook (`outlook.reply_to`, falls back to a new email); new clients are added to the CRM when someone acts on the card; "Make a full proposal" creates a proposal (sent as an email, with Coming issues and Examples blocks) and opens it (`payload.open_href`).
  - **Proposal editor**: every text section is the rich editor (now with tables, add row/column and pictures, shrunk to 1200px in the browser and kept as data: images). Ready-made blocks (`app/proposals/blocks.py`): package, prices, audience numbers, coming issues, events, examples - filled from live data whenever previewed or sent. "How it goes to the client": as an email (the proposal is the email body; pictures become inline attachments; Word file optional) or as a Word document (the brand template; HTML written into it by `app/proposals/html_docx.py`). Older plain-text sections still print exactly as before. Preview shows the exact output plus warnings for things Outlook handles badly.
  - **Examples library** (`/sales/proposals/examples`, `proposal_examples`, `app/proposals/examples.py`): one per brand, shared by everyone, tagged by format and sector; TBTM starts with Kirsty's 45 links, security-scanner wrapping removed (`clean_url`). Links checked weekly and on demand; broken ones are flagged and never suggested.
- **Proposals, parts 3 and 4 (built 14 Oct), migration 0053:**
  - **How you write** (`/sales/proposals/style`, `writing_profiles`, one per person, `app/proposals/style.py`, routes `api/routes/proposal_style.py`). The salesperson adds 3-12 past proposals or replies (upload Word/PDF/text, paste, or "Find them in my Sent emails" which searches their Sent Items with app-only Mail.Read: `graph_client.list_sent_messages`), adds a note (typed or spoken), then "Work out my style" asks the AI for a profile: greeting, sign-off, tone, length, email or Word, always/never, direct-client discount % and rounding, and per situation (agency brief, PR pitch, general, referral, follow-up, existing client, full proposal) what goes in, in what order, and the opening/closing wording. They check it and press "Use this profile". AI off: the standard profile is offered to edit by hand. Openings/closings containing figures are blanked (same figure rule as everywhere).
  - **Where it's used:** proposal request replies (`proposal_requests.compose` follows the owner's profile: order of items, greeting, opening/closing, sign-off, direct-client price = rate card less their % rounded); new proposals (`_apply_style` sets email/Word and adds the blocks their full-proposal situation includes); AI-drafted sections get a "write in this person's style" note. No personal profile = everything behaves exactly as before.
  - **Learning:** every sent reply and finished/sent proposal records what was removed and the sign-off used (`record_edit`, last 30). An item removed 3 times in the last 6 is left out from then on; the same new sign-off 3 times becomes theirs. Shown on the style page under "What the Brain has learned" with a switch to undo each one.
  - **Report** (`/sales/proposals/report`, `GET /api/proposal-report?days=&user_id=`): per person, requests received, replied, not real requests, still waiting, proposals made, bookings that followed (deals from the proposal, or for that company after the request) and their value, usual time to reply; plus by type and by magazine. Sales see only themselves; managers see everyone.
  - Tests `tests/test_proposal_style.py`.
- **Proposal editor is one page (15 Oct, Ahmed's feedback):** `components/sales/proposal-document.tsx` replaces the box-per-section editor. One page, one toolbar (`RichToolbar`, shared with the email editor), a Heading button; each heading (h2, `data-sid`/`data-kind`) starts a section and the page is split back into sections on every change, so the Word file, email, AI revise and style learning still see sections. Ready-made parts are shaded boxes in the page (not typeable); click one to choose what it shows, move or remove it (side sheet). "Add a ready-made part" puts one where the cursor is. The Investment heading shows the package table under it (display only).
- **Booking defaults (migration 0054):** Bookings → Confirmation details → "Filled in on every new booking": production contact (empty = "Production - " + first production address), copy and artwork, special instructions. Returned by `GET /api/sales/deals/prefill`; the publication heading follows the titles on a new booking until someone types their own. Placeholder text is lighter and fields are normal weight everywhere (`ui/input`, `ui/textarea`, `globals.css`).


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

### 4.3 Commission (BMI's structure from Matt, built 8 Oct 2026)
- **Plans** (`commission_rules`, Sales Orders > Commissions > Commission plans): one rule per salesperson per product group: titles covered, rate on their own revenue, extra rate on new business (with an optional "from this publication date" change, e.g. David's 5% to 2% from June 2027), bonus per new customer, per new contract-publishing guide, when a title's yearly revenue passes a threshold, and a share of event profit. "Load BMI's commission structure" fills them from `app/sales/commission_seed.py` (Matt's note; title choices are written in each rule's notes). A booking on a title outside someone's plan uses their old default rate (2%) and is flagged.
- **How it's applied** (`commission_settings`, one row, editable on the plans page): month a booking counts in (`earned_on`: publication by default, or booked), new-business look-back (24 months), first-deal window (0 = only same-day bookings count with the first), event profit basis (whole event or own sales). These are the open questions for Matt; changing an answer is a setting.
- **Personal revenue** = the salesperson's credited share, after any agency cut (in proportion). Cancelled/contra/moved earn nothing.
- **New business** (`app/sales/new_business.py`): no booked spend (any title) or paid Xero invoice by the same customer (CRM company / tidied name / names they've been invoiced under) in the look-back before the booking date. Same-day bookings are part of the first deal. A similar name with recent spend makes it "Needs a decision" (paid no top-up; the month can't be approved until a manager decides). Managers can override any booking, with a reason (kept in its history).
- **Statements** (`app/sales/commission.py`, `api/routes/commission.py`): per salesperson per month, line by line with reasons; bonuses; event profit share (in the month the event's costs are signed off; a loss pays £0). Approving (admins, after the month ends) freezes it (`commission_statements`); later changes to an approved month appear as an adjustment on the next statement, once. Excel download and print. Salespeople see only their own.
- **Event costs**: on the event's edition page, the organiser (rep with an event-profit rule for that title), admins or data managers enter costs and mark them final; an admin signs them off, which locks them (Reopen to change). Editing final costs puts them back to draft.
- **New contract-publishing guide**: tick on the guide's edition page with who sold it; the bonus is paid in the month it publishes.
- Migration `0038`. Tests `tests/test_commission.py` (each clause of Matt's note as a worked example).
- **Matt's answers (9 Oct 2026), built:** first deal = everything on the first invoice (`first_deal_rule="invoice"`: a later booking is new only if it shares the first booking's invoice number); commission earned on publication / event held; new business is a **tick box the salesperson sets** on the booking (managers check monthly; the 24-month check is only a suggestion until someone ticks); Kirsty's 10% is on the whole event, a loss pays £0 profit share but her own 2% still applies. Migration `0040`.
- **From the past statements (Kirsty Aug/Sept, Sally Aug, Steve Sept 2026):** statements end with total, less 35% PAYE/NIC (`retention_rate`), net due, less advances (`commission_months`, entered by admins), cheque amount; a "New business this month" list names each client; an "Issues and events" table shows the issue's total invoicing next to the person's own sales; £75 per Selling Travel Connect attendance (`attendance_bonus_gbp`, count per event in `commission_attendance`, entered on the statement); Sally's Canada Hub at 5.5% (a rule limited to issue names containing "Hub": `edition_includes`/`edition_excludes`, which wins over the title's general rule). "ND sales" on Kirsty's sheet = Neil Dargie's share, already handled by split credits.
- **Still to confirm with Matt:** what the £75 attendance counts; 35% for everyone; Canada Hub = issues named "Hub".

### 4.3b Orders and order confirmations (built 9 Oct 2026)
- **What it is** (`app/models/deal.py`, `app/sales/deals.py`, `api/routes/deals.py`, screens under `/sales/deals`): one client order with several items, BMI's "order confirmation" / "schedule of works". Built from Clare's six example confirmations (SunExpress, Travel Wisconsin, AMEX GBT, Jamaica, Virgin, St Helena).
- **Each item is an ordinary booking** (`SalesOrder.deal_id`) in its own issue / month / event, with optional `item_date` (an email on 13 May) and `copy_due`. So issue figures, Xero matching and commission keep working, and commission is earned item by item (`commission.Ctx.earned_on` uses `item_date` first) - Matt's rule.
- **Pricing:** price per insertion (rate card or agreed) with % off per line; or one **package price** shared across the items by rate card value (default), evenly, or typed per line; then % off the whole order; then agency commission (stored per item in `agency_commission_gbp`, so it comes off commissionable revenue as before). Free **added-value** lines are £0 bookings that print "normally £X". Pennies go on the biggest item so items always sum to the total.
- **Status:** pencilled (held, booking status `pencilled`, not counted anywhere since everything filters `booked`) / confirmed / cancelled (cancel keeps items that already ran or were invoiced, by default). Sending the confirmation from Outlook confirms a pencilled order. Deleting only for pencilled with nothing invoiced.
- **Items can't be edited on their own** for client / issue / price / salesperson (409, "change it on the order"); invoice fields still can.
- **Shared orders:** `split` [{rep_id, pct}] credits every item that way. Salesperson is required on the form (or "House account").
- **Documents:** print page `/sales/deals/[id]/print` (print or save as PDF) and Word download, same data (`deals.document`). BMI's address, terms, artwork specs, footer and the next order number are in Orders > Confirmation details (`deal_settings`, admins). Order numbers continue from 2437.
- **Rebook for next year:** copies the order as pencilled, each item moved to next year's matching issue (same kind, same weekday a year on) at next year's rate card price; says what couldn't be matched.
- **Re-importing the order register** (`sor_import.import_sor(replace=True)`) now **keeps bookings made in the app**: they wait on a placeholder issue and move to the re-imported one; one the spreadsheet also has is flagged "counted twice?" in `import_warning`.
- Entry points: Orders in the sidebar, New order on All bookings / a company / an edition, "They said yes: make the order" on a sent proposal. Migration `0041`. Tests `tests/test_orders.py`.
- **Not tested against the real Outlook** (send uses the same code as proposals).

### 4.3c Proposals with options, and email templates (built 10 Oct 2026)
- **Proposals** (`app/proposals/pricing.py`): each line can be for any title (`title_id`) and run in several issues (`issues`, which set the quantity; `issue_labels` shown in the Word file). % off a line (`discount_pct`) and % off the whole proposal (`Proposal.discount_pct`). Lines with an `option` ("Option A: Issue 108") are choices; lines without one are in every option. Each option has its own total (`totals()`); `total_gbp` is the first option's. Rate-card offers are worked out per option and title. `Proposal.kind` (single issue / several issues / a year's programme / digital / sponsorship / mixed) shapes the standard wording, and the AI is told it. Making the order from a sent proposal asks which option; offers present -> the order uses a package price equal to the option's total, otherwise item prices with the same discounts. Migration `0042`.
- **Email templates** (`/mail-merge/templates`, `MailTemplate` brand / title / kind / needs_check / use_count; migration `0043`): brand facts (print run, email database, readership, website, media pack, video, latest issue) live once per brand on the editorial plan's brand settings (`EditorialSetting.facts`) and fill `{{print_run}}` etc.; issue fields (`{{issue}}`, `{{issue_date}}`, `{{ad_deadline}}`, `{{copy_deadline}}`, `{{theme}}`, `{{feature}}`, `{{features}}`) come from the chosen issue (`mail_merge.shared_context` / `fill_shared`). A mail merge that uses them and has nothing to fill them is refused with a plain reason.
- **Clare's 7 ACT templates** (`app/services/act_templates.py`): "Load Clare's ACT templates" adds them once, as "needs a check", with the repeated figures turned into merge fields and Selling Travel's figures filled in where blank. Each says what looks out of date (2024 links, Covid, old event dates and prices). Saving a template marks it checked.
- **Email from a template** (one person): on the templates page, Who should we pitch? (company's contacts, the issue and the matching feature filled in) and contact pages. Sent from the user's Outlook and recorded on the contact's history, or copied. Not tested against the real Outlook.

### 4.3d Financial year, weekly per-person summary, admin-only settings (built 10 Oct 2026, from the 8 Oct meeting)
- **Financial year** (BMI's runs July-June): the sales overview and dashboard have a "Financial year / Calendar year" switch (`?basis=financial|calendar`). Default and start month are settings (`sales_use_financial_year`, on; `sales_financial_year_start_month`, 7) under Management Reporting. A financial year is named by the year it starts in (2026 = "2026/27", 1 Jul 2026 - 30 Jun 2027). Calendar years still go by an edition's year; financial years go by the edition's **date** (undated editions count from 1 January of their year), see `analytics.period_bounds` / `sales._in_period`. Booking pace runs Jul-Jun; bookings taken before the year began land in the first month. In financial mode the overview's links go to All bookings filtered by edition date. The dashboard's first tile is "booked this year so far vs the same date last year". The weekly brief follows the default.
- **Weekly summary by salesperson** (`management_reports._people`): new "By salesperson" section (table on screen, bullets in email/Teams): bookings taken in the last 7 days (their credited share), commission earned this week and so far this month, from the same engine as the statements (earned when an issue publishes). Alphabetical, not ranked; the AI headline never sees people. Uncredited bookings are called out.
- **Admin-only settings**: changing automation settings, resetting a scan position, wiping review data, and connecting/disconnecting Xero are admin only (`require_admin`). Data managers still see the Hub, run jobs and sync Xero; the settings page shows them read-only.
- **Sections people see** (`/settings/sections`, admin only; `app/ui_sections.py`, `GET/PUT /api/ui/sections`, stored in `automation_settings` as `ui_hidden_sections`): admins untick sections per role (Sales, Data Manager) to take them out of the menu. Admins always see everything. It only tidies the menu; access is still set by role + database grants.

### 4.3e Rate card sizes and own sections; costs on any edition (built 12 Oct 2026, from the 8 Oct meeting)
- **Sizes and pages** (`SalesRate.width/height/size_unit/bleed_mm/pages`, migration `0044`): width x height in mm (print, with bleed) or px (online), and a page count (sponsored content). Shown as one line ("210 x 297 mm, 3 mm bleed · 2 pages", `rate_card.size_label`) on the rate card, the Excel, and in the product pickers on orders and proposals. Copied to next year. An order item from a product with pages counts those pages on the booking (`deals.sync_items`).
- **A brand's own sections** (`RateSection`, keys start `x-`; `POST /rate-card/brands/{key}/sections`, `PATCH/DELETE /rate-card/sections/{id}`): e.g. "Cover wraps & belly bands", after the standard ones, in every year; each says which sales title it's booked under. Only an empty section can be removed.
- **Costs on any edition** (issues too, not just events): each cost line can have a part (`section`: "Judging day", "Ceremony"), what it was for (`category`, list in `sales.COST_CATEGORIES`), a budget (`budget_gbp`) and the booking it was for (`order_id`, same edition only, e.g. a cover wrap's printing). The panel shows totals per part, budget vs actual (over budget in amber), where the money went, and each linked booking's own profit. Events and awards open with the panel showing; an issue shows a one-line "Add the first cost" until it has costs. Commission profit share still uses every `kind == "cost"` line.
- **Costs & profit report** (`/sales/costs`, staff only; `GET /sales/costs-report`, `/costs-report/export.xlsx`): every edition with costs in the year (calendar or financial), sold / budget / costs / profit / margin, filters (title, type, profit or loss, over budget, signed off), "where the money went" for the year, and a count of editions with bookings but no costs (can be shown in the list).

### 4.3f Renewals follow the financial year (12 Oct 2026)
- Renewals (page, anniversary scan, renewal pass, the overview's "not back yet") use the same year as the overview (`sales_use_financial_year`); the page has the same Financial / Calendar switch. Last year's advertisers still go by the issue they booked into.
- **"Back" also counts any booking taken with the title during this year**, whatever issue it went into (`renewals.rebooked_rows`) - someone who paid us this year never gets a renewal email. Booking dates in the future don't count.
- **Odd booking dates are flagged** (`renewals.date_problem`): in the future (a "2035" typo) or more than 60 days after the issue came out. Shown on the row with a link to the booking (new tab) and a "Booking date: looks wrong" filter. The "last booking" shown is picked by issue date, so a typo can't decide it.

### 4.3g Follow-ups from the 8 Oct meeting (built 12 Oct 2026)
- **Invoiced beside booked**: overview and dashboard show "Booked for 2026/27" (every booking for the year's editions) and "Invoiced in 2026/27" (invoices *dated* in the year, whatever issue; `sales.invoiced_between`, invoice date = Xero's or the typed one), each against the same point last year. The weekly brief has the invoiced sentence too.
- **"None of these" is re-checked**: on every hourly matching run an invoice answered "None of these" is matched again against bookings it wasn't shown with (reason "New booking since None of these"). **"Not a booking"** (review card button, and on the "In Xero, not in the register" list) is for cost shares, refunds, recharges: never matched again, off that list, shown under "Marked as not a booking" with **Put back**. State: `automation_state` `xero_not_a_booking`.
- **Accounts check on orders** (`app/automations/order_checks.py`, review kind `order_check`, settings `orders_accounts_check` and `orders_check_before_sending`, both on; migration `0045`): every new order, and a checked order whose client / CRM company / contact / addresses / PO / agency / items / total change, goes to the Review Queue with every record linked. "Looks right" marks it checked; "Needs a fix" (note required) notifies the salesperson, and saving again sends it back with the note. While on, the confirmation can't be sent or marked as sent until checked. Orders made before 0045 count as checked.
- **Per-person sections**: on Sections people see, a person can get their own column (it replaces their role's choice; X goes back to the role's).
- **OBH Forum Asia retired** (migration `0046`, `TitleDef.active`): hidden from pickers, old bookings kept; OBH event prices now book under OBH Awards.
- **Rate card**: click a product's name to edit it. Prices are changed by admins and data managers only unless `rate_card_publishers_can_edit` is switched on.
- **Compare editions** (`/sales/compare`, `GET /sales/editions/compare`): any two editions - totals, a pace chart lined up on each one's publication date, who was in one and not the other. "Compare" on every edition page (defaults to last year's equivalent) and on Editions.

### 4.3h SALES-022 save the sale (built 12 Oct 2026)
- The email scan (`email_summary.py`) now also extracts **"decline"** signals (a client saying no to a booking) with a reason - budget / timing / results / competitor / other (model's answer if valid, else keyword rules, `decline_reason`). Migration `0047` (signal type + `email_signals.reason`).
- `app/automations/save_the_sale.py` (job `save_the_sale_scan`, every 30 min, setting `automations_save_the_sale_enabled`, off by default; cap `save_the_sale_max_per_run`): one review item ("Save the sale") per decline with a draft reply from the reason's template. **The offer is chosen by rules, not AI**: budget = the next cheaper products in the same title on the rate card (below what they last paid) and the next issue; timing = the next open issue (with its ad deadline); results = the cheapest online/newsletter product in the brand; competitor/other = no offer, acknowledge and ask. AI polish only when configured and thrown away if it adds a figure.
- Card: why they said no, what they said, contact / company / last booking / offer links (new tab), the original email excerpt, filters (salesperson, title, reason), date sort. Buttons: Send from my Outlook, Log to CRM only, Let it go (notes "Declined: reason" on the contact). Regenerate switches to the next option (or the one named in the instruction).
- **Templates**: five "Save the sale" templates (kind `save_sale`) appear in the email template library, marked "needs a check", for BMI to rewrite in their own words; the library also has the spec's purposes New prospect, Existing advertiser and Join the project.

### 4.3j Invoicing flow agreed on the 15 Oct call (Matt, Clare, Samantha), migration 0056
- **Who approves what (changed):** the salesperson sends the confirmation to the client themselves (setting "Confirmation waits for the check" is now **off** by default). Pressing **Confirm** (client said yes), or sending the confirmation from Outlook, puts the booking in accounts' **Booking check** card; pencilled bookings aren't checked (`order_checks.request_check` withdraws the card when back to pencilled). Online form entries now create **confirmed** bookings (the client booked it themselves).
- **Lock** (`accounts.locked`): once accounts have checked it **or any item is invoiced** (invoice number / Xero link). Accounts can **Unlock for the salesperson** (`POST /deals/{id}/unlock`, note optional, salesperson notified); when the salesperson saves it locks again and goes back to the check. "Lock it again" (`/relock`).
- **Holiday cover:** setting **Accounts are away** (`accounts_away`): administrators (Matt, Clare) can pass checks, approve changes, unlock and set invoice dates, see accounts' cards and get their notifications (`accounts.notify_people`, `can_approve`).
- **Notifications** for accounts' work (`accounts.tell_accounts`) are emailed too for anyone whose "Email me notifications" preference is on (the default).
- **When to invoice** (`SalesDeal.invoice_plan`, `app/sales/invoicing.py`): **as soon as allowed** (default: now if it runs this quarter, else the first day of the quarter it runs in - BMI invoices in the same quarter, for VAT; quarters follow the July-June financial year), when it runs, after it has run (+`invoice_after_run_days`, 3), on a date agreed with the client (`invoice_on`, required), the quarter after, the financial year after. Plus **invoice instructions** for accounts (never printed) and **invoice currency** (GBP/EUR/USD; prices stay in pounds). A set date a quarter before the item runs shows a gentle warning. Old "up front"/"as agreed" became "as soon as allowed".
- **Accounts' own date** per item (`SalesOrder.invoice_due_on`, `POST /deals/{id}/invoice-date`, "Remind me to invoice on" in the booking's Invoice column, accounts only): wins over the rule; the salesperson is told. Everything else follows the issue date, so a moved issue moves its reminder.
- **Ready to invoice** cards (`app/automations/invoice_due.py`, kind `invoice_due`, accounts only, daily job 07:05 + refreshed on every save; setting `automations_invoice_reminders_enabled`, on): one per booking listing what's due, with instructions, invoice-to, PO, agency, currency and links. Actions: Invoiced (number from Xero), Remind me on… (date field - review cards now support `field_type="date"`), Not yet - next week, No invoice needed. Closes itself when nothing is due. The old "Uninvoiced bookings" scan now skips items from Brain bookings. **Bookings list → To invoice** filter: due now / due by the end of this month (month-end check).
- **Confirmation:** the client's **copy and artwork contact** (name, email) prints in Special Instructions ("Copy and artwork from: …"); **terms per publication** (Confirmation details → "Terms for each publication", `DealSettings.terms_by_title`; the booking's title, else the first item's, else the general terms).
- **Advert with no booking** (issue page button, `POST /deals/unbooked-ad`): record it as a **filler** (a £0 filler item on the issue, page noted) or **someone forgot the booking** (the salesperson gets a notification + email linking to a new booking for that issue and client; it can be dated back).
- Not done yet: Xero draft invoices (needs Samantha's examples + Xero write permission), hand-offs to editorial/production, ownership + "first to take it", the pipeline. Several dates for one sponsored article = separate lines on the booking, each with its own date.
- Tests `tests/test_invoicing_flow.py`; older tests updated to the new flow.

### 4.3k Draft invoices in Xero (built 15 Oct 2026, from the call), migration 0057
- **One click** "Create the invoice in Xero" on a booking (items due now; "Invoice it now" on any other item) and on the Ready to invoice card (`components/deals/xero-invoice-button.tsx`). Accounts only (or admins while accounts are away). Makes a **DRAFT** sales invoice (`app/services/xero_invoices.py`); nothing is approved or sent - Samantha checks and sends it from Xero. Success: a dialog with the number and every detail as Xero has it, plus "Open it in Xero". Otherwise a dialog lists the problems in plain words with the fields to fix them, then "Make the draft invoice" again. Nothing is made in Xero until everything's sorted.
- **Contact**: the booking's own link, then the company's remembered link (not for agency bookings), then the contact on the client's last matched Xero invoice, then a Xero search by invoice-to first line (skipping "Accounts Payable"), agency, client and company name (+ email). Names are tried in that order; the first with exactly one certain match wins. Otherwise: "We couldn't find the right Xero contact..." or "We found more than one..." with the candidates and a search box. The choice is saved on the booking (`sales_deals.xero_contact_id/name`) and the company (`companies.xero_contact_id/name`, not for agency bookings).
- **Lines**: one per item: "What - Title · Issue" (+ date if it has its own), qty 1, our price, agency % as Xero's DiscountRate, account / item / tracking from **Bookings → Xero codes** (per publication, or "every publication"; `DealSettings.xero_codes`); codes picked in the dialog are remembered for that publication. Tax is left to Xero (contact + account). Date today (Xero's date; she changes it if she sends it another day), Reference = PO number or "Magazine Month", currency = the booking's invoice currency (non-GBP asks for the amounts). Idempotency-Key header stops double clicks making two.
- **After**: the invoice is stored like a synced one, the items are linked (`link_bookings(..., "created")`, our £ figures kept), the booking locks (invoiced), the Ready to invoice card closes. Xero drafts show as "Draft in Xero" (new `xero_state` "draft").
- **Xero permission**: scopes now `accounting.invoices accounting.contacts.read accounting.settings.read` (was invoices.read). **Reconnect Xero** after deploying; in n8n token mode the n8n Xero app needs the same scopes. Without it, the dialog says an administrator needs to reconnect Xero.
- Routes `api/routes/xero_invoicing.py` (`/api/xero-invoicing/deals/{id}` GET preview / POST create, `/contacts`, `/reference`, `/codes`). Tests `tests/test_xero_draft_invoices.py` (stubbed Xero). Not yet checked against Samantha's real invoices.

### 4.3l Hand-offs to editorial and production (built 15 Oct 2026, from the call), migration 0058
- **Who** (`app/sales/handoffs.py`, `suggest_team`): sponsored editorial / sponsored content / social media (sponsor, advertorial, feature, spotlight, interview, Q&A, profile, article, content, news story...) -> **editorial**; everything else (adverts, banners, HTML/solus, covers) -> **production**; sponsored for **Caribbean / Visit USA** -> production (fillable forms); sponsored with a banner/HTML -> **both**. Each line has "After it's sold" on the booking form (`line-handoff.tsx`): Hand off to (Suggested / Editorial / Production / Both / Nobody), the email(s) (placeholder = routing table suggestion; blank + a warning when nothing is set), the **format** (TBC allowed) and **Also appears** activities (online, newsletter, social, banner, HTML email, print, event; date + note). Stored on the line (`handoff`, `activities`).
- **Routing table** (Bookings -> Hand-offs, admins; `DealSettings.handoff_routes`): per magazine + "every magazine", editorial and production addresses, **blank by default**. Production falls back to the "Production - always copied" addresses in Confirmation details.
- **When**: when accounts pass the booking check (or on confirm if the check is off); editorial lines whose format is empty/TBC wait until it's filled in. One email per team per booking from the automation mailbox: client, items with issue / run / copy-due dates and activities, the client's copy contact, salesperson, booking link, and a **ready-written email to the client** asking for copy (editorial) or artwork (production). Each line goes once (`sales_deals.handoff_log`); later saves send only new / newly-ready lines; **Send again** on the booking.
- **Locked bookings**: the format, team, addresses and activities can still be changed (`PUT /deals/{id}/lines/{key}/handoff`, "Save and tell editorial" on the booking) - they don't affect the invoice.
- Booking page "Hand-offs to editorial and production": per item, team, addresses and state (sent / didn't go + why / no address yet / waiting for the format / goes after the accounts check). Needs the automation mailbox. Tests `tests/test_handoffs.py`.

### 4.3i Feedback from testers (built 15 Oct 2026)
- **Feedback button** on every page (bottom right, `components/feedback/feedback-widget.tsx`, mounted in `(app)/layout.tsx`; hidden on print pages and while a pop-up blocks the page). Four kinds (broken / confusing / idea / looks wrong), typed or spoken (same transcribe endpoint as proposals). **Point at it**: a picker outlines whatever is under the mouse and names it ("Button: Save, under Confirmation"); a click records it plus a close-up screenshot. **Snap an area**: the page is drawn as a picture (`modern-screenshot`, falls back to the browser's own screen capture), they drag a box. **Whole screen**. Every screenshot opens in a mark-up dialog (arrow, box, draw, Hide to black out private things). While typing, open feedback on the same page or with the same words is shown with **Me too**, so people vote instead of repeating.
- **Recorded automatically** (`lib/feedback-capture.ts`): page path and heading, each pointed-at element's label, nearest heading, a CSS selector, and **where it is in the code**: `feedback-source-loader.cjs` (a Turbopack loader in `next.config.ts`) stamps every element written in `src/` with `data-src="file.tsx:line"` (components from other packages are left alone); browser, screen, zoom, theme; and the last 25 problems on the page (on-screen errors via `friendlyError` with the real reason, console errors, page errors, failed requests).
- **Board** `/feedback` (sidebar "Feedback"): counts, status tabs, kind/page/sort/mine filters, search (words, page, person, #12), cards with the first screenshot, a side sheet with everything (screenshots, code locations, browser and errors for the sender and managers, votes, comments, status). "Show me on the page" opens the page with numbered dots on the things people pointed at (`feedback-pins.tsx`, `?feedback_pin=`); the button shows how many are open on the current page. Admins and data managers set the status (New / Looking at it / Fixed / Won't do + a note); the sender and everyone who said Me too get a notification. Admins are notified of each new one (in the app).
- **Download feedback**: a zip of what the board is showing: `feedback.md` (readable, screenshots linked), `feedback.json` (everything) and `images/`. Built a batch at a time.
- **GitHub issues (optional)**: set `GITHUB_FEEDBACK_REPO` (owner/name) and `GITHUB_FEEDBACK_TOKEN` (fine-grained token, that repo only, Contents + Issues read/write). Each new piece of feedback becomes an issue labelled `feedback` + kind, with screenshots saved on branch `feedback-screenshots` (`GITHUB_FEEDBACK_BRANCH`) so they show inside the issue; edits, comments and status pass on, Fixed / Won't do closes it. Failures are kept on the feedback with a Try again button for admins (`app/feedback/github.py`).
- Backend `api/routes/feedback.py`, `models/feedback.py` (migration `0055`, tables `feedback`, `feedback_images`), tests `tests/test_feedback.py`.

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
- **Review queue cards (standing rule from Ahmed): every record a card mentions - booking, company, contact, invoice - gets a link that opens it in a NEW tab (`target="_blank" rel="noreferrer"`, with an sr-only "(opens in a new tab)"), so the reviewer can check it without losing their place. Do this for every review kind you build or change.** Bookings open at `/sales/orders/[id]`. Each kind also declares its filters (`ReviewKind.facets`; each item stores readable values in `payload["facets"]`, the screen shows them with counts computed with the other filters applied) and, if it has a date, `date_sort_label` + `payload["sort_date"]` for "latest first / oldest first" (that kind then opens newest-first). Bulk actions only touch the items the current filters show.
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
`APP_BASE_URL`, `MAIL_TOKEN_KEY` (Fernet), `GRAPH_TENANT_ID/CLIENT_ID/CLIENT_SECRET` (mailbox scanners; Outlook sign-in falls back to these), optional `OUTLOOK_*`, `AUTOMATION_MAILBOX`, optional `GITHUB_FEEDBACK_REPO` + `GITHUB_FEEDBACK_TOKEN` (feedback as GitHub issues), `XERO_CLIENT_ID/SECRET` (+ optional Xero vars above), LLM key.

---

## 7. Waiting on BMI (keep `docs/bmi-open-questions.md` in sync)
1. **IT – Outlook sending:** on the existing app registration add redirect `https://<domain>/api/outlook/callback`, delegated `Mail.Send`, `User.Read`, `offline_access`, grant admin consent.
2. **Automation mailbox (done differently, 14 Oct):** no application permission needed. automation@bmipublishing.co.uk has its own BMI Brain login (`scripts/seed_team.py`); sign in as it, Settings → Email → Connect Outlook, and set Automations → Settings → "Automation mailbox". `app/services/notify.py` `send_automation_email` finds the Outlook connection whose address matches and sends with the normal delegated Mail.Send. If the connection ever expires, Settings → Email says so; reconnect it the same way.
3. **Teams incoming webhook** (summaries/alerts).
4. **Xero app** registered at developer.xero.com (client id/secret).
5. **Rate card:** media packs received and loaded for all three brands (§3.8); BMI to confirm the items marked "please check" and whether prices are before VAT.
6. **Editorial plan:** OBH + TBTM loaded (§3.9); still need Selling Travel's issue dates and features list.
7. **Digital edition links** (past issues or the link pattern; one issue link + one page link).
8. **3–5 sent proposals** (voice for SALES-020).
9. **Commission rule** (2% vs 5%).
10. Reps' pipeline spreadsheets (SALES-024); delivery stages/timings/owners (SALES-027).
11. One contact with the "useful box" and "Ad agency" filled in; editorial logins (names + read/edit).
12. Gemini API key + billing (offer Clare a 10-min call); branding files; mailbox list + Wufoo outcome; Teams/Zoom transcripts (SALES-008); "proposal sent" pattern (SALES-009); successor research method (CS-003).

**WhatsApp ask already sent (3 Oct):** rate card, editorial plan, digital edition links, 3–5 sent proposals.

## 8. Suggested next steps
1. Proposal builder: BMI voice from sent examples (blocked on BMI). Editorial plan + offers are wired in (§3.10).
2. Act! feedback #7 (company address → update contacts with opt-out).
3. SALES-024 pipeline → SALES-025 chase lists.
4. Xero figures on the SALES-026 dashboard once Xero is connected live.
5. Load link patterns when BMI sends them; Selling Travel editorial plan when it arrives; have each publisher press "Looks right" on their rate card and plan.
6. SALES-022, SALES-023, then (with Ahmed's go-ahead and a proper plan) the AI chat.
   **Proposal AI (library, personal style, drafting agent) is planned and PARKED in `docs/proposal-ai-plan.md`** - build it with the AI chat and SALES-023, not before.
7. Before go-live: fresh Act! migration, `refresh_sor` on live, reps test mail merge.
