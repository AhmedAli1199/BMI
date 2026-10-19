---
title: Automations Hub
screens: ["/automations", "/automations/[workstream]", "/automations/engine", "/automations/signals", "/automations/llm-usage"]
summary: The control room for the Brain's background automations - what they found, how fast the team deals with it, which scanners are on, when they last ran, and what the Brain costs.
sources: ["frontend/src/app/(app)/automations/page.tsx", "frontend/src/app/(app)/automations/[workstream]/page.tsx", "frontend/src/app/(app)/automations/engine/page.tsx", "frontend/src/app/(app)/automations/signals/page.tsx", "frontend/src/app/(app)/automations/llm-usage/page.tsx", "frontend/src/components/automations/automations-table.tsx", "frontend/src/components/automations/hub-ui.tsx", "frontend/src/components/automations/charts.tsx", "frontend/src/components/run-job-button.tsx", "frontend/src/components/photo-upload-dialog.tsx", "frontend/src/components/app-sidebar.tsx", "frontend/src/lib/automation-style.tsx", "backend/app/api/routes/automations.py", "backend/app/api/routes/automation_stats.py", "backend/app/automations/workstreams.py", "backend/app/automations/scheduler.py", "backend/app/automations/business_card.py", "backend/app/automations/returned_copy.py"]
---

## What this screen is for
The Automations Hub is where administrators and data managers keep an eye on the Brain's background helpers. Each helper (a "scanner") reads mailboxes, the CRM or the order register on a timetable and puts suggestions in the Review Queue. Most of what it suggests waits until a person approves it; a few safe things happen on their own - the email summary note on a record, linking an order-register client to a company with exactly the same name, and (if switched on) filling in clear Xero invoice links. The header says this too, and each setting on Scanners & Settings says what it does by itself. The Hub shows how much is waiting, how quickly the team deals with it, whether each scanner is switched on and working, and what the requests to the Brain cost.

Open it from the menu: **Automations** (under The Brain) > **Overview**, one page per group of automations, and **Scanners & Settings**. Salespeople don't see the Hub. Their **Today** list and **Review Queue** are separate sidebar items.

## What you see
**Overview (Automations Hub)**
- The header, with a button on the right that takes you to the Review Queue.
- A **Workstreams** table covering the last 7 days. A workstream is a group of related automations:
  - **Sales & Follow-ups**: proposal requests, overdue follow-ups, commercial signals, personal touchpoints and call notes.
  - **Lead & Contact Capture**: new people who emailed an enquiry mailbox.
  - **Business Cards & Photos**: business cards and returned-copy labels people photograph.
  - **CRM Data Hygiene**: duplicates, bounces, out-of-office replies and people who have left.
  - **Revenue & Orders**: booking checks, invoicing, renewals, invoice matching and the other order register cards.
  Columns: **Pending** (amber when anything is waiting), **New**, **Resolved** and **New per day** (a small line chart). Click a row to open that workstream.
- A strip at the bottom of the table: **Scanners & Settings**, "N of M scanners switched on".
- Two lists: **New for review** (the 5 newest waiting cards) and **Recently resolved** (the 5 latest decisions, with who made them). Each has **View all →**.

**A workstream page** (for example Automations Hub > CRM Data Hygiene)
- A breadcrumb back to **Automations Hub**, the title and a one-line description.
- **Business Cards & Photos only**: an **Upload photos** panel at the top.
- Four figures: **Pending now** (with how long the oldest has waited), **New suggestions**, **Resolved by your team** and **Acted on**. Acted on is the share of decisions that were an approval rather than a dismissal, plus the median time from suggestion to decision. The small arrows compare with the previous period. A rise in new suggestions shows amber (more work). A rise in resolved shows green.
- **New vs resolved**: a chart of new and resolved cards per day, with the backlog line.
- **Automations**: one row per kind of card. Columns: **Automation**, **Scanner** (On / Off / Last run failed, and when it last ran), **Pending**, **New**, **Resolved**, **Acted on**, **Time to resolve** and **Last 7 days**.

**Scanners & Settings** (/automations/engine)
- A line saying how many scanners are switched on, and how many failed on their last run (in red).
- A table with one row per scheduled job. It shows **Scanner** (name, On/Off and a description, with the error in red if the last run failed), **Schedule**, **Last run** (Succeeded / Failed / Running, how long ago, and "manual" if someone pressed Run now), **Found** (cards it added), **Took** and **Last 10 runs**. The last column shows 10 small bars, oldest to newest: green worked, red failed, amber still running. Hover over a bar for its date and result.

**Brain usage & cost** (/automations/llm-usage)
- Four figures: **Total cost** (US dollars), **Times used**, **Success rate** (amber below 90%) and **Text read and written (tokens)** (tokens are the units the Brain's provider charges by).
- **Usage over time**: calls, failures, tokens and cost per day or per hour, newest first.
- **By automation**: the same figures for each purpose and provider.

**Email signals** (/automations/signals)
- A plain table of the latest 200 facts the email scan has picked out of sales emails: **Contact**, **Type**, **Due date**, **Summary**, **Confidence**, **Status** and **Created**. It shows what the Brain has picked out of client emails so far, and how sure it was of each. **Type** is one of Budget timing, Renewal date, Promised call-back, Personal moment or Said no. **Status** is Waiting, Acted on or Dismissed. The page isn't in the menu; open it by its address when you want to check the scan is reading emails sensibly.

## Buttons and controls
### Review <number> pending / Open Review Queue
On the Overview, it opens the Review Queue with every automation shown. On a workstream page, it opens the Review Queue filtered to that workstream's automation with the most cards waiting. When nothing is waiting, it reads **Open Review Queue**.

### Workstream rows
Click anywhere on a row of the **Workstreams** table to open that workstream's page.

### Scanners & Settings of … scanners switched on
The strip under the Workstreams table. It opens the Scanners & Settings page.

### View all →
On **New for review**, it opens the Review Queue (Pending). On **Recently resolved**, it opens the **Approved** tab. Clicking any single line opens the Review Queue filtered to that kind of card.

### 7 days / 30 days / All time
On a workstream page, this switch changes every figure and the table. The chart always shows the last 7 or 30 days. With **All time** it shows the last stretch only, and the figures above are all-time.

### Opening a row in the Automations table
Click a row, or the arrow at its end, to open its details:
- **What your team decided**: how often each button was pressed in the period.
- **Waiting now, by type**: a breakdown of the waiting cards, for duplicates (by confidence), bounces (hard or soft) and out-of-office replies (replacement named or not). Click a line to open just those cards.
- **Scanner health**: schedule, whether it's switched on, the last run and anything it found, any error, and **All scanners →**.
- **Reviewers & Brain cost**: the three people who decided the most, and the Brain's cost. Some scanners share their Brain cost between several kinds of card, for example the bounce and out-of-office scan. Those say "Shared with … (same scanner)". "Doesn't use the Brain - it follows fixed rules" means the Brain isn't used.
- **Latest items**: the 5 newest cards, with **Open in Review Queue**.
Clicking the amber **Pending** number also opens those cards in the Review Queue.

### Upload business card(s) / Upload returned copy label(s)
On **Business Cards & Photos** only. Both open a small window:
- **Publication**: which database the people belong to (OnBoard Hospitality, Prospects or Selling Travel).
- **Show / event (optional)** (business cards only): for example "WTM London 2026". It goes on the new contact's note.
- **Photo**: take a picture or pick one. One photo can hold several cards or labels.
- **Upload** reads the photo with the Brain and adds one Review Queue card per card or label. **Cancel** closes the window.
After a business card upload, the message offers **Confirm all now**. That approves every card from that photo in one go. New people are created with the suggested groups, changed details are applied, and unchanged people get an "already in the CRM" note. Anyone signed in can upload, including salespeople.

### Brain usage & cost
On Scanners & Settings, it opens the Brain usage & cost page.

### Automation settings
On Scanners & Settings, it opens Automations > Settings (see the "Automation settings" guide).

### Run now
On each scanner's row. It runs the job straight away, even if it's switched off. It doesn't switch the job on. Administrators and data managers can use it. It may take a few seconds, and the page then refreshes with the new run. If the job is already running, nothing extra happens.

### Reset & rescan
Administrators only, on the four scanners that remember where they got to in each mailbox or contact list: **Bounce & OOO mailbox scan**, **Duplicate contact scan**, **Email exchange summary scan** and **Inbound contact capture scan**. It makes the scanner forget its place, then runs it, so it reads everything again back to its "first look back" setting. Cards it already made are kept, and it won't repeat a card that is still waiting.

### 7 days / 30 days / 90 days and By hour / By day
On Brain usage & cost. They choose the period (30 days to start with) and whether the usage table is grouped by day or by hour.

### Automations Hub and Scanners & Settings (breadcrumb)
On Automation settings and Brain usage & cost, the breadcrumb above the title takes you back to **Automations Hub** or **Scanners & Settings**. On the Email signals page, **Automations Hub** in the breadcrumb goes back to the Overview.

## How it works
- Every scanner has an on/off setting in Automations > Settings. Most are off until switched on. Reminders, notification emails, mail merge sending, the Xero sync, the shared calendar, the Brain search index, Ready to invoice reminders and the weekly example-link check start on. Switching one changes its next scheduled run, with no restart.
- Schedules are shown in UK time, so in British Summer Time they read an hour later than in winter (a job set for 07:00 GMT shows as 08:00 in summer).
- Each run is recorded with its result. **Found** counts the Review Queue cards the job added during that run. Jobs that don't make cards always show 0, even when they did their work. These include reminders, notification emails, mail merge, the Xero sync, the shared calendar, the search index, the email summary scan, the advertising deadline reminders and the management reports.
- A card waits in the Review Queue until someone presses one of its buttons. **Acted on** counts approvals against dismissals. **Time to resolve** is the middle value from card to decision.
- Brain costs are estimates: tokens used × the price set in Automations > Settings > Brain usage & cost at the time. Check the provider's own bill for exact amounts.
- Some cards are made by people or events rather than a scanner: photo uploads, booking checks, booking changes, online booking forms and call notes. Their Scanner column says "Manual upload".

## Common questions
**Q: How do I see what's waiting for my team?**
A: Open **Automations Hub** > **Overview** and look at the **Pending** column. Click a workstream for detail, or press **Review <number> pending** to start working through them.

**Q: Is a scanner switched on?**
A: Open **Scanners & Settings**. A green dot and "On" mean it runs on its schedule. To switch it on or off, press **Automation settings** and tick or untick its setting. Only administrators can change it.

**Q: I've just switched on a scanner. Can I test it without waiting?**
A: Yes. On **Scanners & Settings**, press **Run now** on its row. Then check the Review Queue for what it found.

**Q: A scanner shows "Failed". What do I do?**
A: Read the red text under its name. Common causes are a mailbox the Brain can't read, the Brain not being switched on, or Xero needing to be reconnected. Fix that, then press **Run now**. If it keeps failing, tell your administrator.

**Q: How do I add business cards from an event?**
A: Go to **Automations Hub** > **Business Cards & Photos**.
1. Press **Upload business card(s)**.
2. Pick the **Publication** and type the **Show / event (optional)**.
3. Choose the **Photo** and press **Upload**.
4. Check the cards in the Review Queue, or press **Confirm all now** in the message to accept them all.

**Q: How much is the Brain costing us?**
A: Press **Brain usage & cost** on Scanners & Settings, or **View Brain usage & cost →** on the settings page. Choose **7 days**, **30 days** or **90 days**.

**Q: Why does an automation say "Doesn't use the Brain - it follows fixed rules"?**
A: That automation works from fixed rules and figures, such as the order register or Xero, so it costs nothing to run.

**Q: Can I make a scanner re-read old emails?**
A: An administrator can press **Reset & rescan** on that scanner. It reads back as far as its "first look back" setting.

## If something doesn't work
- **"Administrators & Data Managers only"**: the Hub is for those two roles. Salespeople can still use **Today** and **Review Queue**. Press **Go to your Today queue**.
- **No Reset & rescan button**: only administrators see it, and only on the four scanners that remember their place.
- **Run now shows an error**: the job itself stopped with a problem. The full reason is in the server log; on screen you get a plain sentence. Common causes are a mailbox that needs connecting or the Brain being switched off. Fix the cause and try again. If it says the job is already running, its scheduled run has just started - check back in a minute.
- **A run shows a problem in red**: the sentence says what kind of problem it was (for example a connected account that needs signing in again, or a service that didn't answer). Administrators can hover over it to see the technical detail to pass on to whoever runs BMI Brain.
- **Found is 0 but the scanner ran**: either nothing new turned up, or the job doesn't make Review Queue cards (see How it works).
- **Upload says "Reading cards needs the Brain"**: reading photos needs the Brain key. Ask your administrator. "Image too large (max 8MB)" means you need a smaller photo. "Couldn't read this image" means you should try a clearer, flatter photo.
- **Automation settings, Brain usage & cost or Email signals says "Administrators & Data Managers only"**: these pages are for administrators and data managers. Salespeople can still use **Today** and **Review Queue**.
