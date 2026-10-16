---
title: Sales overview - Selling now, and the weekly summary
screens: ["/sales/dashboard", "/sales/summaries"]
summary: How every issue and event is selling against the same point last cycle, the weekly flow of bookings and team activity, plus the Monday management brief and the behind-last-cycle alerts.
sources: ["frontend/src/app/(app)/sales/dashboard/page.tsx", "frontend/src/app/(app)/sales/summaries/page.tsx", "frontend/src/components/sales/weekly-chart.tsx", "frontend/src/components/run-job-button.tsx", "backend/app/api/routes/sales.py", "backend/app/sales/analytics.py", "backend/app/automations/management_reports.py", "backend/app/api/routes/management.py"]
---

## What this screen is for
**Selling now** (the second tab of **Overview** under Sales in the menu) shows how every issue and event that is still selling compares with its equivalent from last cycle, how many bookings came in each week, and what each person has done recently. **Weekly summary & alerts** (**More** > **Weekly summary** in the menu) is the one-page Monday brief for leadership and the early-warning alerts for editions running behind. Both use the same figures as the overview, so they never disagree. This is a picture of what's happening, not a league table or a target tool: people are always listed alphabetically.

## What you see
### Selling now
- **Header** "Sales overview" with the **Financial year / Calendar year** switch, and the tabs **This year** and **Selling now**.
- **Uncredited bookings warning** (only when there are some): "<number> bookings (<amount>) in <year> aren't credited to any salesperson". These don't appear in the per-person figures.
- **Three figure tiles** (the year's booked and invoiced totals are on the **This year** tab)
  - **Editions selling** - open editions publishing in the next few months.
  - **Editions behind last cycle** - how many selling editions are behind, and how many are ahead.
  - **Booked, last 12 weeks** - the value booked in the last twelve weeks, against the same weeks last year.
- **Edition tracker** - one row per edition still selling: its name and date ("Publishes" or "Runs"), bookings, **Booked**, **Last cycle, same point** (with a link to last cycle's edition), **Gap** in pounds and per cent, a progress bar and a **Status**:
  - **Behind** (amber) - booked at least the threshold (25% by default) less than last cycle at the same point.
  - **On pace** (grey) - within the threshold either way.
  - **Ahead** (green) - at least the threshold more.
  - **Too early to compare** (grey) - no equivalent edition last cycle, or last cycle had too little booked at this point. A short reason is shown underneath.
  Behind editions are listed first.
- **Weekly bookings** - a bar for each of the last 12 weeks (weeks start on Monday). The dark tick on each bar is the same week last year. Hover over a bar for the figures.
- **Team activity** - for the last 30 days, alphabetically: **Bookings** and **Booked value** credited to each person, **Follow-ups actioned** (items they dealt with in their queue) and **Waiting in queue**. "no login" means the salesperson isn't linked to a login yet, so their queue can't be counted.

### Weekly summary & alerts
- **Header** with **Run now** and **Open Selling now →**.
- **The brief** for the chosen week ("Week of <date>"), saying when it was written and whether the headline was written by the Brain or put together from the figures. Its sections are: the headline, **Revenue**, **Activity**, **By salesperson** (a table), **Editions to watch**, **Alerts this week**, **Sold-work delivery** and **Needs a decision**. Most lines link to the records behind them.
- **Recent alerts** - the latest 20 behind-last-cycle alerts, each linking to its edition, with its own **Run now** button.
- **Earlier weeks** - previous briefs (shown once there is more than one).

## Buttons and controls
### Financial year / Calendar year (Selling now)
Changes which year the uncredited warning uses. Financial years run July to June. The edition tracker, weekly chart and team activity don't depend on it.

### Edition names in the tracker
Open the edition page. The smaller link under **Last cycle, same point** opens last cycle's equivalent edition.

### Salesperson names in Team activity
Open All items filtered to that person. This shows all their bookings, not just the last 30 days - add a **Booked on** date filter there to narrow it.

### Run now (next to the brief)
Writes this week's brief straight away, without waiting for Monday. If this week's brief already exists it is rewritten with the latest figures, and nobody is notified again. Administrators and data managers only.

### Open Selling now →
Opens the Selling now tab of the Sales overview.

### Run now (next to Recent alerts)
Runs the behind-last-cycle check straight away. Any new alerts are sent to the recipients as notifications. Administrators and data managers only.

### Links in the brief
Names in **By salesperson** open All items filtered to that person's bookings from the last 7 days. The two commission figures open that person's commission statement for the month. Edition lines open the edition, and "Needs a decision" lines open the page where the work waits (Invoicing, the Review Queue or Selling now).

### Week of <date> (Earlier weeks)
Shows that week's brief.

## How it works
- **Equivalent edition:** the same title's edition from the year before with the same name once the year is taken out ("Jan 2026" and "Jan 2025"). For numbered issues it's the same position among that year's numbered issues ("OBH 105" and "OBH 101"). Failing both, it's the edition dated closest to a year earlier, within six weeks. Supplements and guides only match by name.
- **Same point before publication:** the tracker compares each edition with last cycle's at the same distance before its own publication date, not on the same calendar date. An issue that moved by a fortnight is still compared fairly.
- **Which editions are tracked:** open editions with a date, from 30 days ago onwards.
- **When an edition is judged:** only when last cycle had at least £2,000 across at least 3 bookings by that point (company settings). Below that it says "Too early to compare".
- **Weekly bookings** use the booking date. Each week is compared with the week exactly 52 weeks earlier, so weekdays line up. Only live bookings count.
- **Uncredited bookings:** live bookings worth more than £0 in the current year with no salesperson credited. Open the booking and pick a salesperson to fix it.
- **The weekly brief** is written on Monday mornings at about 7am, but only once "Weekly management summary" is switched on in the automation settings (it's off by default). The recipients get a notification (and an email once the automation mailbox is set up), plus a Teams message if Teams is set up. Recipients are the people listed in the settings, or all administrators if nobody is listed.
- **Only the headline may be written by the Brain.** If it contains any figure that isn't in the source data, it's thrown away and a headline is put together from the numbers instead. The Brain never sees individual people.
- **By salesperson in the brief** shows bookings taken in the last 7 days (each person's credited share), commission earned this week, and commission so far this month. Commission is earned when an issue publishes or an event runs, so it can differ from what was booked that week.
- **Alerts** are checked on weekday mornings once "Behind-last-cycle alerts" is switched on (off by default). An edition is alerted when the tracker would call it Behind. The same edition isn't alerted again for 14 days.

## Common questions
**Q: Which editions should I worry about?**
A: Open **Overview** > **Selling now** and look at the top of the **Edition tracker** - editions marked **Behind** come first, with the gap in pounds and per cent.

**Q: Why does an edition say "Too early to compare"?**
A: Either there's no matching edition from last cycle, or last cycle had less than the minimum booked by this point (£2,000 and 3 bookings by default). The reason is shown under the status.

**Q: What's the dark tick on the weekly bars?**
A: The value booked in the same week last year. A bar above its tick means a busier week than last year.

**Q: How do I fix "bookings aren't credited to any salesperson"?**
A:
1. Go to **All items** and search for or filter to the bookings.
2. Click the client to open the booking.
3. Choose a person under **Credited to** (or use **Split** for a shared booking).
4. Click **Save changes**.

**Q: How do I get this week's brief now instead of waiting for Monday?**
A: Open **Weekly summary** and click **Run now** next to the brief. The page refreshes with the new brief.

**Q: Can I see an older week's brief?**
A: Yes. Click the week under **Earlier weeks**.

**Q: Why is someone's commission shown as "-" in the brief?**
A: The commission figures couldn't be worked out for them when the brief was written. Their bookings are still shown.

**Q: Is the team activity a ranking?**
A: No. It's listed alphabetically on purpose, to show what's happening, not to rank people.

## If something doesn't work
- **I can't find Weekly summary in the menu, or the page says it can't be found.** It's only for administrators and data managers.
- **"No summary has been written yet."** The Monday brief is off until "Weekly management summary" is switched on in the automation settings. An administrator or data manager can click **Run now** to write one straight away.
- **"No alerts have fired."** Either alerts are switched off, or no edition has fallen far enough behind. An edition that was alerted in the last 14 days won't be alerted again yet.
- **"No editions are currently selling."** The tracker only shows open editions with a date from 30 days ago onwards. Editions with no date, or closed ones, don't appear.
- **Follow-ups show "no login".** That salesperson isn't linked to a login. An administrator can link them in Settings > Users.
- **Sold-work delivery says nothing is set up.** That section is a placeholder until delivery tracking exists.
- **The first two dashboard tiles show "Editions selling" instead.** The year figures couldn't be loaded; the rest of the page still works.
