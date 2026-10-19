# The rest of the app: things that looked confusing or possibly buggy

Found while writing the assistant's help guides for every area (15 Oct), by reading the code. Not fixed yet - check each before acting. Sales Orders notes are in docs/sales-orders-review-notes.md.

## Security - fixed 18 Oct (tests/test_permissions.py)
- ~~Team accounts: no server-side admin check~~ - admins only (`app/core/guards.py`).
- ~~Anyone can change another person's preferences~~ - your own only (admins any).
- ~~Bulk update history / undo open to all~~ - your own (admins all); undo skips contacts you can't see.
- ~~Exporting a ticked selection didn't re-check access~~ - leaves out contacts you can't see.
- ~~Delete routes for contacts, companies, groups had no role check~~ - admins and data managers only.
- ~~Switched-off accounts stayed signed in; role/database changes waited for the next sign-in~~ - the backend checks the account on every call (role as it is now), and the frontend proxy refreshes the session every minute (signs out a switched-off account).
- ~~Hidden sections still opened from a link~~ - `components/section-gate.tsx`.
- ~~Data Health counts not limited to a data manager's databases~~.
- Sales: ~~Rebook with no permission check / on cancelled bookings~~, ~~anyone could add/close/reopen an edition~~ (salespeople can still edit its notes), ~~new booking from someone else's proposal~~, ~~editing a sent proposal on the server~~ (notes only), ~~Put back shown to people who can't edit prices~~.

## Data-changing bugs - fixed 18 Oct
Mail merge template update, issue date moves (year + deadlines follow), renamed deadline rules (rule keys, migration 0062), empty number settings, reopening cards that already wrote (now refused), snoozes (new "snoozed" outcome, migration 0063), duplicate pairs and dismissed follow-ups coming back, follow-up card links, inbound leads' database, returned-copy addresses (asks for the new one), departures (contacts.has_left), reopened cancelled bookings, hand-off resends and change emails, Send with the accounts check off, notetaker recording rule, call-note reminder dates, call cards closing/updating, activity repeats. Struck-through items below are covered by this.

## Plain on-screen text (C) and Review Queue rules (D) - fixed 19 Oct
C: Run now / run history / bulk errors in plain words, no job codes on screen, title names instead of database names, schedules in UK time words, Xero / Outlook / mail merge / notetaker messages plain, Settings cards without server setting names, staff checks on Automation settings, Brain usage and Email signals, Home uses card labels and real title counts (tests/test_plain_messages.py).
D: filters + date sort + new-tab links on every Review Queue kind (app/automations/review_facets.py), paging with a true count, bulk actions follow the Queue Insights group and run in rounds of 500 with a confirm dialog, soft bounces lead with "Keep - it was temporary" (tests/test_review_facets.py).

## Wording (E) and screens that didn't quite work (F) - fixed 19 Oct
E: Data Health (bounced counted, each figure against what it's about, Fix opens the filtered list), Feedback (notification wording, data managers, your own pins, tiles follow filters + Won't do, email preference honoured), Hub/Today/online forms/rate card/Put back/Xero/renewals/All items/proposal/companies/groups (sub-group members, paged)/meetings/editorial wording, cancel dialog buttons.
F: record arrows keep advanced search; Calendar paging + real overdue count + "Mine only" kept; contact card phone types, real website, no fake "Standard", custom field names, Magazine & Issues matching; change history names + phones/emails/addresses; dialogs show the real reason; reminder delete with Undo; Cancel on paused merges; Load Clare's Act! templates button; split reps in booking filters; booking-owned item fields read-only; rate card saves on click-away; proposals paging/errors/report; commission boxes; Pencilled + Draft in Xero filters; unbooked advert reps; edition cost permissions; FY editions link; hand-off editing on locked bookings; Found and card sources; editorial key dates, reminder catch-up, plan next year copies theme, "Issue 105"; Brain chat rename and re-mark-up; theme colours everywhere. Tests: test_screen_fixes.py, test_activities_list.py and others.

## Editorial plan
- Moving an issue's publication date into another year doesn't update its year, so it drops off both years' planners.
- Saving brand settings deletes brand figures other than the seven on the form (proposals can show extras like LinkedIn followers).
- Issue page "Last year's equivalent" doesn't require the same kind of issue; "Haven't rebooked" and reminders do.
- Changing an issue's publication date doesn't recalculate deadlines (need Use the usual rules).
- Use the usual rules recognises custom deadlines by name; renaming leaves a duplicate key date.
- An undated event/awards shows nothing in Key dates.
- Deadline reminders only on exact days (14/7/1), no catch-up; in-app only; salespeople only if their sales record is linked to their login.
- Plan <next year> doesn't copy theme or notes and the dialog doesn't say so.
- Previous/next buttons on an issue show "105" instead of "Issue 105".
- Non-editors on brand settings get no Back to the plan button.
- Plan footer says "Everyone can view it" but the sidebar entry depends on access.
- The published plan can only be loaded for 2026; load button disappears once anything is set; Selling Travel has none.
## Settings, dashboard, feedback, data health, Ask AI
- Disabling an account doesn't sign the person out (session up to 30 days); role changes apply on next sign-in.
- A new database grant doesn't show in the switcher until the person signs in again.
- Sections page says hiding doesn't change what anyone may see - Ask AI now refuses hidden sections; hidden pages still open from a direct link.
- Data Health counts aren't limited to a data manager's databases.
- Data Health "Fix" opens the full list, not the records with the problem.
- Data Health backlog % measured against all contacts, so mostly "Watch".
- "Unsubscribed / hard-bounced" counts only unsubscribed.
- Dashboard Overnight Activity shows even when the Review Queue is hidden for that person.
- Dashboard shows review kinds as raw code names and "see /settings to change".
- Dashboard "Across all 3 publication titles" is fixed text.
- No-access message says "Settings → Team" but the card is "Team & access".
- Add database dialog says "Postgres" and "Internal key" (jargon).
- Xero card shows server setting names (XERO_CLIENT_ID); Outlook card mentions "Mail.Send".
- Outlook Disconnect has no error handling.
- Feedback: saving a status note without changing status says "They'll get a notification" but none is sent.
- Feedback delete / GitHub retry errors say "Only administrators" but data managers can.
- Feedback dots show Me too on your own feedback, then fails.
- Feedback count tiles ignore filters; no Won't do tile.
- Ask AI: rename conversation exists on the server but not on screen.
- Ask AI screenshots can't be marked up again; Point at it close-up skips mark-up.
- Ctrl+J opens the panel on /brain on top of the full-page chat.
- "Email me notifications" has no effect on feedback notifications.
## Automations Hub and Review Queue
- Bulk actions ignore the selected Queue Insights group, so "dismiss all soft bounces" acts on every bounce of that kind.
- Reopen assumes a rejected card changed nothing, but some rejected buttons write (Remind me on, Needs a fix email, No invoice needed) - reopening can repeat that.
- "Keep as separate contacts" isn't remembered; dismissed duplicate pairs come back on later sweeps.
- Dismissing an Overdue Follow-up leaves the activity open, so it's queued again next hour.
- Follow-up cards: "View activity record" links to /companies/<activity id> (broken link).
- Inbound Lead Capture creates the contact in the "manual" database, not the mailbox's database.
- Returned copy "Update address" writes the label's (failed) address onto the record; unmatched labels have no contact picker.
- Departure "Confirm successor" warns it updates the contact across titles but only adds notes.
- Departure error says "Pick someone else" but the button is "Assign different contact".
- Soft bounces still offer "Confirm & unsubscribe" as the main button.
- Review Queue subtitle "N items waiting in this filter" shows the total across all kinds.
- Review Queue shows only the first 100 cards, no paging.
- Approved/Rejected rows: record links open in the same tab (breaks new-tab rule); hardcoded emerald/rose colours.
- No filters / date sort on: bounces, out-of-office, departures, duplicates, business cards, returned copy, inbound leads, follow-ups, commercial signals, touchpoints, renewals (CLAUDE.md rule).
- Internal names on screen: Run now toast "<job id> ran", backend errors with job id + exception text, run error column "ExceptionType: message", bulk errors with item IDs.
- More internal names: job descriptions "SALES-010-lite", "CS-001"; shared-inbox picker shows "prospects / onboard / sellingtravel"; AI usage raw purpose names; "Resolved via batch confirm (SALES-002)".
- Run now toast says it ran even when skipped (already running).
- Hub schedules show raw cron codes; times are UTC with no UK note.
- Calls notes, booking checks/changes and online bookings show "Manual upload" / "Created from photo uploads" in the workstream table.
- "Found" always 0 for jobs that don't make cards (e.g. email summary scan).
- Settings, AI usage and Email signals pages have no staff check on the frontend (salesperson gets an error page).
- Email signals page is a throwaway still live, says "SALES-012/013", raw types.
- Settings say "Daily" for weekday-only jobs (Ready to invoice, Items to allocate, Issue gone to press, Behind-last-cycle).
- Teams webhook setting promises "daily review summaries" that don't exist.
- "Sales Order Register" appears as two settings groups.
- Hub says nothing is updated until approved, but some things happen on their own (email-summary note, exact client links, clear Xero links).
- Bulk note prompts use a browser prompt with no confirm and no cap on very large selections.
- "Reset to default (true)" shows raw value; emptied number box can save an invalid value; text settings unchecked.
- Today subtitle doesn't mention personal touchpoints.
- Today's visibility filter may be called without the person's identity (unconfirmed).
## Contacts, companies, groups, calendar, mail merge, call notes
- Mail merge "Update template" sends only name/subject/body/shared; backend overwrites every field, so brand, title, purpose and team note are lost and it's marked checked.
- Record arrows on a contact page ignore advanced-search rules.
- Calendar & Tasks loads only the newest 100 activities, no pages; Overdue count only looks inside those.
- "Mine only" switches back on for salespeople when another filter is clicked.
- "Repeats" is saved but no repeat copies are created.
- Raw error text on screen: mail merge failed-send shows Outlook's error; notetaker send/stop and test-send errors pass the service's message through.
- Save to history on a call page doesn't close its Review Queue card.
- A contact linked after the call-notes card was made doesn't get linked on the card.
- Reminders from saved call notes are all due the next day, whatever the call said.
- Companies page tells group-limited users the list shows the whole database (it doesn't).
- Group page lists only direct members (cap 500); Export and Mail merge include sub-groups - numbers differ.
- Contact card labels any second phone "Mobile" and saving relabels it.
- Contact card Web Site shows a "Company Profile" link, not the website.
- ID/Status shows "Standard" when there's no category.
- User Fields tabs show stored names (user3) not custom names; contact tab can show _import keys.
- Magazine & Issues picks custom fields by matching "ad" in the name (catches "address").
- Change history: company changes show raw ids; phone/email/address edits from Edit Record don't appear.
- Add existing contact doesn't refresh the company's contact list.
- Company Contacts empty state names buttons wrongly ("Link Existing Contact"/"New Contact").
- Mark as departed only moves notes; person not marked departed; activities stay with them.
- "Load Clare's ACT templates" has no button anywhere.
- Add/edit contact, company, group dialogs show a fixed message instead of the server's plain reason.
- Delete reminder: no confirmation, no undo.
- Cancel hidden on paused mail merges (server allows it).
- Notetaker check wording "check its console" is technical.
- Meetings heading says "Everyone's meetings" but sales staff see only their own.
- One BMI attendee's automatic setting records the meeting for everyone in it.
- Hardcoded colours on the activity timeline and several CRM pages.
