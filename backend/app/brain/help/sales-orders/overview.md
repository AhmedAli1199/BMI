---
title: Sales Orders overview
screens: ["/sales"]
summary: The front page of the order book - what has been booked and invoiced this year against last year, by title and by salesperson, with links into every other Sales Orders page.
sources: ["frontend/src/app/(app)/sales/page.tsx", "frontend/src/components/sales/sales-ui.tsx", "frontend/src/components/sales/pace-chart.tsx", "frontend/src/components/app-sidebar.tsx", "backend/app/api/routes/sales.py", "backend/app/sales/analytics.py"]
---

## What this screen is for
This is the front page of BMI's order book: every booking across every title, issue and event in one place, instead of fifteen spreadsheets. It answers "how is this year going?" at a glance - how much is booked, how much has actually been invoiced, and how that compares with the same point last year. Every figure is added up from the bookings themselves; nobody types a total. Everyone who can see Sales Orders can open it.

## What you see
- **Header** - the title "Sales Orders", the **Financial year / Calendar year** switch, the year buttons and a button that takes you to the editions or bookings behind the figures.
- **Four figure tiles**
  - **Booked for <year>** - the value of live bookings for this year's editions. Underneath is last year's figure: "by this date last year" while the year is still running, or the whole of last year for a finished year. The small arrow shows the change: green when you're up, amber when you're down.
  - **Invoiced in <year>** - money actually billed: invoices dated in the year, whatever issue or event they were for. Underneath: last year's figure at the same point and the share of this year's booked value that has been invoiced.
  - **Awaiting invoice** - how many of this year's bookings have a value but no invoice number yet, with their total. The link opens Invoicing.
  - **Advertisers** - how many different clients have booked this year, how many are new (never booked before this year), and how many from last year are "not back yet". That link opens Renewals.
- **Booking pace** - a chart of the running total booked through the year (solid line) against last year (dashed line). Months still to come are not drawn for this year. Hover over a month to see its exact figures.
- **By title** - one row per title: booked value, the change against the same point last year (or "new" / "none yet"), and a bar. The bar is this year so far; the tick shows where last year was. A green bar means level or ahead, amber means behind. Click a row to see that title's editions or bookings.
- **Coming up** (current year only) - open editions publishing or taking place in the next ten weeks or so (up to eight), with bookings, how many are still to invoice, booked value and the change against last year's equivalent edition. Click one to open its edition page.
- **By salesperson** - each person's credited share of live bookings, with the number of bookings. Former salespeople are marked "former". Click a name to see their bookings.
- **Three cards at the bottom** - **Renewals**, **Invoicing** and **All editions**, each with a one-line count.

## Buttons and controls
### Financial year / Calendar year
Switches how the year is counted. **Financial year** runs from July to June (hover to see the months) and is named by the year it starts in, so "2026/27" is 1 July 2026 to 30 June 2027. **Calendar year** runs January to December. Which one opens first is a company setting (financial year by default). The choice is kept in the page address, so you can bookmark or share it.

### Year buttons (for example 2026/27, 2025/26 or 2026, 2025)
Pick which year to look at. Up to four of the most recent years are shown. Looking at a past year compares it with the whole of the year before it, rather than "by this date".

### Editions / Bookings
The button at the top right. In calendar-year mode it says **Editions** and opens the Editions list for that year. In financial-year mode it says **Bookings** and opens All items filtered to editions dated inside the financial year.

### <amount> not invoiced yet →
On the Awaiting invoice tile. Opens the Invoicing page.

### <number> from <last year> not back yet
On the Advertisers tile. Opens Renewals.

### Title rows in "By title"
Calendar year: opens the Editions list for that title and year. Financial year: opens All items for that title, filtered to the financial year's edition dates.

### Editions in "Coming up"
Opens that edition's page.

### Names in "By salesperson"
Opens All items filtered to that person (including bookings they share) for the same year.

### Renewals / Invoicing / All editions cards
Shortcuts to those pages. In financial-year mode, **All editions** opens the Editions list for the whole financial year (July to June), not a calendar year.

### This year / Selling now (tabs)
**This year** is this page. **Selling now** shows how each issue and event that is still selling compares with last cycle, the weekly bookings and team activity (see the "Sales overview: Selling now, and the weekly summary" guide).

### The Sales items in the menu
Everything for sales is under **Sales** in the menu. An amber number next to **Invoicing** is the count of bookings overdue for an invoice. Administrators can hide items from the menu for a role or a person; hiding only tidies the menu.
- **Overview** - this page, with its two tabs.
- **Bookings** - the bookings and order confirmations you create for clients (see the "Bookings list", "Booking page" and "New booking and change booking form" guides).
- **Proposals** - building and sending proposals to clients (see the "Proposals" guide).
- **Rate card** - prices and products for each title (see the "Rate card" guide).
- **Editions** - every issue, month and event, and each edition's own page (see the "Editions and the edition page" guide).
- **Invoicing** - what still needs an invoice and invoice checks (see the "Invoicing" guide).
- **Commissions** (salespeople see **My commission**) - commission statements (see the "Costs, profit and commission" guide).
- **More** opens the rest:
  - **All items** - every booked item across every title and year (see the "All items and renewals" guide).
  - **Renewals** - last year's advertisers who haven't rebooked (see the "All items and renewals" guide).
  - **Weekly summary** - the Monday brief and alerts, administrators and data managers only.
  - **Costs & profit** - costs and profit across all editions, administrators and data managers only (see the "Costs, profit and commission" guide).

## How it works
- **Booked** counts only bookings with the status Booked. Cancelled, contra (free swaps) and moved bookings are never counted. Pencilled bookings are not counted either.
- **Which bookings belong to a year:** in calendar-year mode an edition belongs to the year it is filed under. In financial-year mode it goes by the edition's date. An edition with no date counts from 1 January of its year.
- **Same point last year:** while the year is running, last year's figure only counts bookings that had been taken by today's date a year ago. That keeps the comparison fair while sales are still coming in.
- **Invoiced in <year>** goes by the invoice date, not the issue. The date is the one from Xero when the booking is linked to a Xero invoice, otherwise the date typed on the booking. So an invoice dated in August for a June issue counts in August's year.
- **The percentage invoiced** under that tile is the invoiced value on this year's editions divided by this year's booked value.
- **Awaiting invoice** counts this year's live bookings worth more than £0 that have no invoice number yet. It includes editions that haven't come out yet.
- **New advertisers** are clients booking this year who never booked before it. **Not back yet** counts last year's paying advertisers who haven't booked this year. Anyone who took any booking during this year counts as back, whatever issue it went into. Client names are matched loosely, so small differences in spelling count as the same client.
- **Booking pace** places each booking in the month it was taken. Bookings taken before the year began (selling this year's issues early) all go into the first month. Bookings with no date go by their edition's date.
- **By salesperson** uses each person's credited share. A shared booking is split between the people on it.

## Common questions
**Q: Why does the booked figure differ from the invoiced figure?**
A: They measure different things. Booked counts every live booking for this year's editions, invoiced or not. Invoiced counts invoices dated in this year, whatever issue they were for. An issue sold this year but invoiced next year shows in this year's Booked and next year's Invoiced.

**Q: How do I see the calendar year instead of July to June?**
A: Click **Calendar year** at the top. Click **Financial year** to go back.

**Q: How do I look at last year?**
A: Click last year's button next to the year switch (for example **2025/26**). Its figures are compared with the whole of the year before it.

**Q: Which bookings are behind the "Booked" number for one title?**
A: Click the title's row in **By title**. You get its editions (calendar year) or its bookings filtered to the year (financial year).

**Q: How do I see everything one salesperson has booked this year?**
A: Click their name under **By salesperson**. All items opens filtered to them for the same year.

**Q: Who counts as a "new" advertiser?**
A: A client booking this year who has no live booking in any earlier year.

**Q: Why is a booking I just made not in the total?**
A: It only counts once its status is Booked. Pencilled, cancelled, contra and moved bookings are left out. Also check that its edition falls inside the year you're looking at.

**Q: Where do I start following up last year's advertisers?**
A: Click **<number> from <last year> not back yet** on the Advertisers tile, or the **Renewals** card at the bottom.

## If something doesn't work
- **"Coming up" is missing.** It only shows for the current year. On a past or future year it is hidden.
- **"Coming up" says "Nothing publishing in the next 10 weeks."** Only open editions with a date in the next ten weeks or so are listed. A closed edition, or one with no date, doesn't appear.
- **A title shows "new" in the comparison column.** It had nothing booked at the same point last year, so there's nothing to compare it with.
- **A salesperson is missing from By salesperson.** Only people credited on live bookings for the year appear. Bookings with no salesperson credited don't show here - the Dashboard flags them.
- **I can't see Sales in the menu, or an item in it.** An administrator may have hidden that item for your role or for you. Ask an administrator to check "Sections people see" in Settings.
- **Weekly summary and Costs & profit aren't in my menu.** They are only for administrators and data managers.
