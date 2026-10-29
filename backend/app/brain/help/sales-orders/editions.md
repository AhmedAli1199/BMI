---
title: Editions and the edition page
screens: ["/sales/editions", "/sales/editions/[id]", "/sales/compare"]
summary: Every issue, month of online sales and event for a year, each edition's own page with its bookings, costs, notes and checks, and a side-by-side comparison of any two editions.
sources: ["frontend/src/app/(app)/sales/editions/page.tsx", "frontend/src/app/(app)/sales/editions/[id]/page.tsx", "frontend/src/app/(app)/sales/compare/page.tsx", "frontend/src/components/sales/editions-explorer.tsx", "frontend/src/components/sales/new-edition-dialog.tsx", "frontend/src/components/sales/edition-actions.tsx", "frontend/src/components/sales/edition-notes.tsx", "frontend/src/components/sales/edition-costs-panel.tsx", "frontend/src/components/sales/edition-link-button.tsx", "frontend/src/components/sales/renewal-pass-button.tsx", "frontend/src/components/sales/add-booking-button.tsx", "frontend/src/components/deals/unbooked-ad-button.tsx", "frontend/src/components/commission/edition-commission.tsx", "frontend/src/components/sales/compare-picker.tsx", "frontend/src/components/sales/compare-chart.tsx", "backend/app/api/routes/sales.py", "backend/app/api/routes/deals.py", "backend/app/api/routes/commission.py", "backend/app/automations/sor_checks.py", "backend/app/sales/analytics.py"]
---

## What this screen is for
An **edition** is one issue of a magazine, one month of online sales, or one event - what used to be one tab in a title's order register workbook. The **Editions** list shows every edition for a year. Each **edition page** shows everything booked into it, how it compares with last year, what it cost to produce and the profit, notes, and the checks accounts make once an issue has gone to press. **Compare editions** puts any two editions side by side.

## What you see
### Editions list
- **Header** with the year buttons, **Compare editions** and **New edition**.
- **Filter sidebar** and a search box, plus a **By title / One list** switch.
- A line saying how many editions match and their booked total.
- **The table:** Edition, Title (in One list), Date, Bookings, Booked, **vs last year** (change against last year's equivalent edition at the same point, plus its final total; "No match" if there isn't one), Invoiced (per cent by value), and a **To do** column with flags: an amber "<n> to invoice", a warning triangle when imported rows need a check, and "Closed".
- In **By title**, each title has a heading row with its edition count, booked total and change against last year.

### Edition page
- **Header:** the edition name, its title, type, period, date, exchange rate and a "Closed" badge if closed. Buttons along the right (see below).
- **Four figure tiles:** **Booked** (with a progress bar if a target was set), **vs last year's edition**, **Invoiced** (per cent by value, and "<n> of <m> paid bookings invoiced"), and **Pages sold** for print titles or **Average booking** for others.
- **By salesperson** - a coloured strip with each person's credited share.
- **A note about the original sheet's total**, if the imported sheet's own total didn't match the bookings. The bookings list is the complete one.
- **Commission panel** (only where it applies) - "New contract-publishing guide" on guides and supplements, and "Event costs for <name>'s profit share" on events where someone earns a share of the profit.
- **Costs & profit panel** - open straight away for events and awards; for an issue it shows a one-line "Add the first cost" until it has costs.
- **Notes** - free text about the edition.
- **Bookings in this edition** - the same filterable list as All items, without the year, title and edition filters.

### Compare editions
Two pickers (**This edition** against **Compared with**), then a table (Booked, Bookings, Advertisers, Average booking, Pages sold, Invoiced so far, with the difference), a chart **How fast each sold**, and three lists: **In <other>, not in <this>** (the ones to win back), **New in <this>** and **In both**.

## Buttons and controls
### Year buttons (Editions list)
Show a different year's editions. Your filters are kept.

From the overview in financial-year mode, **All editions** opens the Editions list for that financial year instead (for example 2026/27: editions published or held from 1 July 2026 to 30 June 2027; an undated edition counts from 1 January of its year). Pick a year button to go back to a calendar year.

### Filters (Editions list)
**Title**, **Type** (Print, Digital, Events, Awards), **Status** (Open, Closed), **Invoicing** (Has bookings to invoice / All invoiced), **Import check** (Has rows to check / No issues), **vs last year** (Level or ahead / Behind / Nothing to compare), **Booked value** range and **Edition / event date**. Click a column heading to sort.

### By title / One list
Groups the table under each title, or shows one list with a Title column.

### Compare editions
Opens the comparison page.

### New edition
Opens the **New edition** dialog: **Title**, **Year**, **Name** (for example "109", "Jan 2027", "Feb Asia"), **Publishes / takes place**, **Period label**, **Exchange rate (US$ per £)** and **Target (£)**. Click **Create edition** to make it; you are taken to its page. **Cancel** closes it. The date drives "Coming up", invoice chasing and the comparison with last year; the target adds a progress bar. Anyone who can see Editions can create one.

### Previous / next arrows (edition page)
Step to the previous or next edition of the same title in the same year.

### New booking
Opens the full booking form with this edition already chosen - use this for a proper booking with a confirmation.

### Compare
Opens Compare editions with this edition on the left and last year's equivalent on the right.

### Export .xlsx
Downloads the edition as a spreadsheet in the old order register layout, with totals, every booking, each person's credit and the commission payable.

### Add online link / Online link
Administrators and data managers only. Saves where the issue can be read online. Next year's renewal emails link advertisers back to it. Click **Save** in the dialog. When **Watch for new issues online** is on, the Brain fills this in for you from BMI's Issuu page once someone confirms the match on a **New issues online** card.

### Start renewals
Administrators and data managers only, on open editions that have an equivalent last year. The dialog explains what will happen; **Draft renewal emails** drafts a personal renewal email for every advertiser in last year's edition who hasn't booked again this year. Each goes to the salesperson who sold it, to check and send from their own Outlook. People already booked, or already sent a renewal this year, are left out, so it's safe to run again. The result shows how many were drafted, with a link to see them (**See them in Revenue & Orders →**). **Done** closes it.

### Close edition / Reopen
Marks the edition as finished selling, or opens it again. A closed edition drops out of "Coming up", the dashboard tracker and renewal passes. Nothing is locked: invoices can still be recorded against it.

### Costs & profit panel
- **Add the first cost** / **Add a line** - adds a line (only for administrators, data managers and the event's organiser, until the costs are signed off; everyone else sees the costs without these buttons). Choose **Cost**, **Other income** or **Note**, describe it, and for a cost pick **What was it for?**, an optional **Part** (for example "Judging day"), whether it was **For the whole edition** or for one booking, a **Budget £** and the **Actual £**. Click the tick (**Save line**) to save or the cross to cancel.
- **Add** on a part's heading adds a line to that part.
- The pencil and bin icons (shown when you hover over a line) edit or remove it. Greyed "Sheet total" lines from the imported sheet can't be edited.
- Booking names under **Bookings with their own costs** open the booking in a new tab.

### Commission panel buttons
- **Yes** and **Who sold it?** (New contract-publishing guide) - administrators and data managers tick this on a guide or supplement that is a new contract-publishing job. Whoever sold it gets the new-guide bonus in the month it publishes.
- **Costs are final** / **Not final yet** - administrators, data managers and the person earning the profit share mark the event's costs final once every bill is in.
- **Sign off** - administrators only, once costs are final. The costs are then locked and the share goes on that month's statement.
- **Reopen** - administrators only, to unlock signed-off costs. Later changes show as an adjustment on the next statement.

### Notes
Type in the box, then **Save notes** (or **Cancel**). The buttons only appear once you've changed something. Notes are kept when the register is re-imported.

### Advert with no booking
For an advert found in the printed issue with nothing on the register. Pick the **Client company** (or type the name), the **Page**, and choose **What is it?**:
- **Someone forgot the booking** - choose the **Salesperson** and click **Ask them to book it**. They get a notification and an email linking to a new booking for this issue and client, which they can date back. Only people who can sign in to the Brain are listed, as they're the ones who can be sent a notification - tell anyone else yourself.
- **A filler** - click **Record the filler**. A £0 item marked as a filler ad is added to this issue, with the page noted.

### Add item
Opens the item sheet to add a single line straight onto this edition's register (see the All items guide for every field). Items added this way have no booking behind them, so no confirmation goes out and the accounts check will flag them.

### Bookings list
Search, filters, **Export** and the table work exactly as on All items. Click a client to open the item.

### Compare editions pickers
Choose any edition from the last four years in each box. The page updates straight away. Edition names in the table headings open their pages.

## How it works
- **Booked** counts live bookings only - cancelled, contra and moved ones are left out.
- **vs last year** compares with last year's equivalent edition, counting only what it had booked by today's date a year ago. The equivalent is matched by name without the year, then by position among numbered issues, then by the nearest date within six weeks.
- **Invoiced %** is by value: £ invoiced out of £ booked. £0 bookings (tickets, guests' seats, contra) are left out of the "paid bookings" count.
- **Pages sold** is worked out from each item's size.
- **Profit** = booked value minus the cost lines. "Other income" lines are shown but not added, because they're usually the same money as the bookings. Sheet totals are for reference only. A cost with a budget is shown in amber when it's over budget.
- **Who can change costs:** administrators, data managers, and the person earning that event's profit share. Changing a cost that was marked final takes it back to draft. Signed-off costs can't be changed until an administrator reopens them.
- **Issue gone to press check:** when switched on, a few days (2 by default) after an issue's copy deadline - or its date if it has no copy deadline - accounts get one card in the Review Queue for that issue. It lists, each with a link: items with no booking behind them, items that don't match their booking, items still pencilled, confirmed bookings whose confirmation was never sent, and packages for this title still to be allocated to an issue. It also shows how many items are still to invoice and how many filler ads (and pages) the issue carries. **All checked** closes it; **Look again next week** brings it back in a week. Only accounts can act on it (administrators too while accounts are away). It changes nothing by itself.
- **Packages to be allocated** are booking lines that are paid for but have no issue chosen yet. They're allocated on the booking page, not here; the press check reminds accounts they may belong in this issue.
- **Filler ads** are kept apart from sold space. Filter the bookings list with **Filler ads** to see them.
- **Compare editions** lines both editions up on their own publication dates, from 26 weeks before to 4 weeks after. Bookings with no date count from the publication date. Advertisers are matched loosely by name.

## Common questions
**Q: How do I set up next issue?**
A:
1. Go to **Editions** and click **New edition**.
2. Choose the **Title**, check the **Year**, and type the **Name**.
3. Add the **Publishes / takes place** date.
4. Click **Create edition**.

**Q: How do I record the printing cost of one client's cover wrap?**
A: On the edition page, click **Add a line**, choose **Cost**, describe it, pick "Printing & paper" under **What was it for?**, choose **For <client>** in the booking box, enter the **Actual £** and click the tick. The booking then shows under **Bookings with their own costs**.

**Q: I found an advert in the magazine that isn't on the register. What do I do?**
A: Click **Advert with no booking** on the edition page. Choose **Someone forgot the booking** and the salesperson, or **A filler** if the space was given away.

**Q: How do I compare this issue with last year's?**
A: Click **Compare** on the edition page. Last year's equivalent is picked for you.

**Q: How do I see what's still to invoice in this edition?**
A: In the bookings list on the edition page, set **Invoice** to **Awaiting invoice**.

**Q: How do I get the old spreadsheet view for finance?**
A: Click **Export .xlsx** on the edition page.

**Q: How do I start renewals for an issue that's just opened for bookings?**
A: An administrator or data manager clicks **Start renewals**, then **Draft renewal emails**.

**Q: How do I change an edition's date?**
A: Dates and deadlines are set on the Editorial plan's issue page.

## If something doesn't work
- **Start renewals is missing.** It only shows to administrators and data managers, on open editions that have an equivalent edition last year.
- **Add online link is missing.** Only administrators and data managers see it.
- **"<Title> already has an edition called <name> in <year>."** An edition with that name already exists for the title and year. Open that one instead, or use a different name.
- **Create edition is greyed out.** Type a **Name** first.
- **"Exchange rate and target must be numbers."** Remove letters or symbols other than £ and commas.
- **"Only administrators, data managers and the event's organiser can change its costs."** You can see the costs panel but not change it. Ask a manager.
- **"These costs are signed off for commission."** An administrator must click **Reopen** first.
- **"Choose what the cost was for from the list."** Pick an option under **What was it for?**.
- **Ask them to book it is greyed out.** Choose a client and a salesperson first. If you get "Choose the salesperson who should make the booking.", that person has no login linked yet - pick someone else, or ask an administrator to link them.
- **"No equivalent edition last year" / "No match".** The edition's name or date doesn't match one from last year, so there's nothing to compare it with. Use **Compare editions** to pick one yourself.
- **Compare editions doesn't list an old edition.** Only the last four years are offered.
- **"Those editions couldn't be compared."** One of them may have been removed. Pick them again.
