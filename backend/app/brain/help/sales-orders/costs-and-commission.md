---
title: Costs, profit and commission
screens: ["/sales/costs", "/sales/commissions", "/sales/commissions/[rep]/[period]", "/sales/commissions/plans"]
summary: The costs and profit report for every issue, event and awards, and each salesperson's monthly commission statements, plans, new business decisions and sign-off.
sources: ["frontend/src/app/(app)/sales/costs/page.tsx", "frontend/src/components/sales/costs-report.tsx", "frontend/src/app/(app)/sales/commissions/page.tsx", "frontend/src/app/(app)/sales/commissions/[rep]/[period]/page.tsx", "frontend/src/app/(app)/sales/commissions/plans/page.tsx", "frontend/src/components/commission/statement-view.tsx", "frontend/src/components/commission/plans-view.tsx", "frontend/src/components/commission/commission-ui.tsx", "frontend/src/components/commission/booking-new-business.tsx", "backend/app/api/routes/sales.py", "backend/app/api/routes/commission.py", "backend/app/sales/commission.py", "backend/app/sales/new_business.py", "backend/app/sales/commission_seed.py"]
---

## What this screen is for
**Costs & profit** shows what every issue, event and awards cost to produce against what it sold, for a whole year. It's for admins and data managers.

**Commissions** works out each salesperson's commission month by month from the order register and their plan. Salespeople see their own ("My commission"). Admins check each month, settle any new business questions, and approve it, which locks the figures that are paid. **Commission plans** sets what each person earns on each product.

## What you see
**Costs & profit** (admins and data managers only)
- At the top: a Financial year / Calendar year switch, a year switch and **Excel**.
- Four tiles: **Sold, editions with costs**, **Costs**, **Profit** (with the margin, as a % of what was sold) and **No costs recorded** (editions with bookings but no costs yet).
- **Where the money went**: every cost line in the year by what it was for, with bars and percentages.
- A filter sidebar, a search box and filter chips, and a line saying how many editions are shown with their sold, costs and profit (profit in green, a loss in red).
- A table: Edition (click to open; shows the number of cost lines, the biggest kind of cost and "signed off"), Date, Sold, Budget, Costs (amber when over budget), Profit (green or red) and Margin. Click a column heading to sort.

**Commissions** (Sales Orders > Commissions)
- **Commission plans** button (admins and data managers) and a year switch.
- A blue strip if no plans are loaded yet, with **Load BMI's commission structure** for admins.
- An amber strip if any bookings need a decision on new business.
- A table: one row per salesperson, one column per month up to this month, and the year total. "no plan, on 2%" shows next to anyone without a plan. In each month: a green tick means approved and locked; an amber dot means bookings still need a decision. Click any month to open that statement.
- Salespeople only see their own row. If their login isn't linked to a salesperson yet, they see "Your login isn't linked to a salesperson yet".

**A statement** (one salesperson, one month)
- The title "<name>: <month>", with buttons to go to the previous and next month (not past this month), **Excel**, **Print** and, for admins, **Approve this month**.
- A green note once approved (when, by whom, and any change since that will go on the next statement).
- An amber box listing bookings that need a decision on new business.
- Six tiles: Their revenue, Commission, New business top-up, Bonuses, Event profit share (or Events, when attendances are paid) and Total.
- The main table, grouped by product: Issue or event (opens in a new tab), Client (opens the company in a new tab), Their share, Rate ("not in plan" in amber if the title isn't in their plan), Commission, New business (a pill: new business in green, returning in grey, needs a decision in amber, plus who decided) and Total. Then Bonuses, Event profit share, Event attendance and adjustments for earlier months.
- **What's paid**: total, less retention for PAYE/NIC, net due, less advances, cheque amount.
- **New business this month**: each new client, the bookings it came from and the top-up and bonus.
- **Issues and events this month**: each issue's total invoicing next to this person's sales and commission.
- **<first name>'s plan** (folded away).

**Commission plans** (admins and data managers can view; only admins can change)
- **How the plans are applied**: the settings box.
- One card per salesperson with each product group in their plan, its rates, bonuses and the titles it covers.

## Buttons and controls
### Financial year / Calendar year and year switch (Costs)
Choose the year. BMI's financial year runs 1 July to 30 June and is named by the year it starts in (2026 = 2026/27).

### Excel (Costs)
Downloads the report as shown (same year and setting), with totals and costs by type.

### Show them in the list / Show only editions with costs
On the **No costs recorded** tile. Adds editions that have bookings but no costs to the table, or takes them out again.

### Filters (Costs)
**Title**, **Type**, **Result** (Made a profit, Made a loss, No costs recorded), **Against budget** (Over budget, Within budget, No budget set), **Signed off for commission** and **Edition / event date**. Search looks at the edition and title.

### Edition name (Costs)
Opens the edition's page, where its costs are added under "Costs & profit".

### Load BMI's commission structure / Reload BMI's structure
Admins only. Fills everyone's plans with BMI's commission structure. Reload replaces every plan (it asks first) and your own changes are lost.

### A month figure (Commissions)
Opens that month's statement.

### Previous / next month
Move between months on a statement.

### Excel / Print (statement)
Download the statement as a spreadsheet, or print it (buttons and editing boxes are left off the printout).

### Approve this month
Admins only, once the month has ended and every "Needs a decision" booking is decided. Opens **Approve <name>'s <month>?**; press **Approve** to lock the total as the amount due, or **Cancel**.

### New business / Same customer (in the amber box)
For a booking where a similar name has spent with BMI recently. Type a reason if you like, then press **New business** (a different customer) or **Same customer** (returning). Admins, data managers and the salesperson on the statement can decide, until the month is approved.

### Tick as new business / Not new business?
Under any booking's New business pill. Opens a dialog with an optional **Why** box, then **Tick as new business** or **Not new business**. Your choice replaces the suggestion and is kept in the booking's history.

### Use the suggestion
Goes back to the automatic suggestion for that booking.

### Attendances box
In Event attendance. Type how many attendances to pay (0 to 100) and press Enter or click away. Admins and data managers only, until the month is approved.

### Advances (£), Note (optional), Save
In **What's paid**. Advances already paid for this month come off the cheque amount. Admins only, until the month is approved.

### Settings box (Commission plans)
- **A booking counts in the month**: its issue publishes or event runs (the default), or it was booked.
- **New business means no spend in the last <n> months** (24 by default).
- **A new customer's first deal is**: everything on their first invoice (BMI's rule), or bookings within a number of days.
- **Event profit is worked out from**: the whole event's income, or only their own sales on it.
- **Held back for PAYE/NIC** (35% by default).
**Save** applies it (unapproved months are worked out again); **Undo** puts back what was there. Admins only.

### Add a product / pencil (Commission plans)
Admins only. Opens a side panel for one product group: **Product group**, **Titles it covers**, **Rate on their revenue (%)** (required), **Extra on new business (%)**, **New business rate changes for issues from** and **...to (%)**, **Bonus per new customer (£)**, **Bonus per new contract-publishing guide (£)**, **Bonus when a title's yearly revenue passes (£)** and **...this much (£)**, **Share of each event's profit (%)**, **Bonus per event attendance (£)**, **Only issues named with** / **Except issues named with**, **Applies from** / **Until**, and **Notes**. Leave a box empty if it doesn't apply. **Save**, **Cancel**, or **Remove** (asks first).

### New business tick box on a booking
On a booking's edit panel, the salesperson on the booking (or a manager) ticks **New business** themselves. **Use the suggestion** goes back to the automatic one.

## How it works
- **Profit** = what was sold (booked value) minus every cost line on that edition. Margin = profit as a % of what was sold. The tiles and totals only count editions that have costs.
- Costs are added on each edition's own page. For events, the organiser, admins or data managers enter costs and mark them final; an admin signs them off, which locks them.
- **Which month:** a booking counts in the month its issue publishes or its event runs (or an order item's own date), unless the setting says "it was booked".
- **Their revenue** is the salesperson's credited share of each booking, after any agency's cut. Cancelled, contra and moved bookings earn nothing.
- **Commission** = their revenue x the plan's rate for that title. A title not in their plan uses their standard rate (2% by default) and is flagged "not in plan". A rule limited by issue names (for example "Hub") wins over the title's general rule.
- **New business:** the salesperson ticks it on the booking; managers check it each month. Until someone ticks it, the Brain suggests it: new if the customer had no booked spend or paid invoice in the look-back (24 months). Everything on a new customer's first invoice counts. If a similar name has spent recently, it's "Needs a decision", earns no top-up, and the month can't be approved until it's decided.
- **Bonuses:** per new customer; per new contract-publishing guide (ticked on the guide's edition page, paid when it publishes); when a title's revenue for the calendar year passes a set amount (paid once, in the month it passes); and per event attendance.
- **Event profit share:** paid in the month the event's costs are signed off. A loss pays £0 profit share (their own commission on sales still applies).
- **What's paid:** total, less retention for PAYE/NIC (35% by default), less advances, gives the cheque amount.
- **Approving** freezes the month. If bookings for an approved month change later, the difference appears once, as an adjustment on the next statement.
- Changes to plans and settings apply to every month that isn't approved yet.

## Common questions
**Q: Where do I see my commission?**
A: Sales Orders > **Commissions**. Click any month to see every booking, the rate it earned and why.

**Q: Why is a month empty?**
A: A booking counts in the month its issue publishes or its event runs, not when you booked it. Check the month the issue comes out.

**Q: How do I approve a month?**
A: 1. Open the statement (the month must have ended). 2. Decide every booking in the amber "needs a decision" box. 3. Check the advances in **What's paid**. 4. Press **Approve this month**, then **Approve**.

**Q: A booking says "Needs a decision". What do I do?**
A: Check whether it's the same customer as the similar name. Then press **New business** or **Same customer**, with a reason if useful.

**Q: A booking shows "not in plan". What does that mean?**
A: That title isn't in the salesperson's plan, so their standard rate was used. An admin can add it in **Commission plans** with **Add a product** or the pencil on the right product.

**Q: A booking changed after the month was approved. Is the paid figure wrong?**
A: No. Approved figures don't change. The difference goes on the next statement as an adjustment.

**Q: How do I enter Selling Travel Connect attendances?**
A: Open the statement for the month the event ran, find Event attendance, type the number and press Enter.

**Q: How do I see which events lost money?**
A: Open **Costs & profit**, then in the filter sidebar choose **Result** > **Made a loss**.

**Q: Why is an event missing from the costs report?**
A: It has no costs yet. Press **Show them in the list** on the No costs recorded tile, or add its costs on the event's page.

## If something doesn't work
- **I can't open Costs & profit**: it's for admins and data managers only.
- **"Your login isn't linked to a salesperson yet"**: an admin links your account to your initials in Settings > Users.
- **Approve this month is greyed out**: some bookings still need a decision on new business.
- **Approve this month is missing**: only admins can approve, and only once the month has ended and while it isn't approved yet.
- **"A month can be approved once it has ended"** or **"This month is already approved"**: as it says.
- **I can't change advances, attendances or new business on a statement**: the month is approved, so it's locked. Advances are admin-only; attendances are admins and data managers.
- **"Only the salesperson on this booking or a manager can change this"**: you aren't credited on that booking.
- **I can see the plans but can't change them**: only admins can change commission plans and settings.
- **"Give the product a name"** or **"Enter the rate on their revenue"**: fill in those boxes before saving a plan.
- **"This event has no date yet, so it can't go on a statement"**: give the event a date on its edition page.
- **The next month button is missing**: you can't go past the current month.
- **Someone isn't in the Commissions table**: people with no bookings and no commission in that year aren't listed.
