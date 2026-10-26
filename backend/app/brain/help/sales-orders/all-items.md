---
title: All items and renewals
screens: ["/sales/bookings", "/sales/renewals"]
summary: Every booked item across every title and year, with filters, export and an edit panel, plus the list of last year's advertisers who haven't booked again yet.
sources: ["frontend/src/app/(app)/sales/bookings/page.tsx", "frontend/src/app/(app)/sales/renewals/page.tsx", "frontend/src/components/sales/orders-explorer.tsx", "frontend/src/components/sales/orders-table.tsx", "frontend/src/components/sales/order-sheet.tsx", "frontend/src/components/sales/renewals-table.tsx", "frontend/src/lib/sales-filters.ts", "backend/app/api/routes/sales.py", "backend/app/sales/order_query.py", "backend/app/sales/renewals.py"]
---

## What this screen is for
**All items** is the whole order register in one list: every item booked into every issue, month and event, across every title and year. Use it to find a particular booking, check what's still to invoice, or export exactly the rows you need. **Renewals** lists, for one title at a time, the advertisers who booked last year but haven't booked again this year - biggest spenders first - so you can win them back. Everyone who can see Sales Orders can use both pages.

## What you see
### All items
- **Header** with **New booking**.
- **Filter sidebar** on the left, with a count beside each option.
- A search box, **Export**, and the active filters as chips you can remove.
- A line with the number of bookings and their booked value (live bookings only).
- **The table:** **Client** (with its CRM company underneath, and a warning triangle if the imported row needs a check), **Edition** (with its date), **Booked** (date), **What** (size, series, page), **Rep** (initials; shared bookings show every person, for example "SW / KH"), **Value**, **Invoice** and **Status**.
  - **Invoice** shows the invoice number, an amber amount if the invoice differs from the booking with no reason given, "explained" if a reason is recorded, and the payment state from Xero (Paid, Part paid, Unpaid, Overdue, Voided, Draft in Xero). With no invoice yet it shows "Not yet", or an amber **Overdue** once the issue is out or the event has run. "—" means there's nothing to invoice.
  - **Status** is a coloured pill: Booked (green), Pencilled (amber), Cancelled (red), Contra, or Moved (with where it moved to). For cancelled and moved items the sheet's own words are shown underneath.
  - Cancelled, contra and moved values are struck through.
- A footer with the booked value of live bookings on this page, and page controls (50, 100 or 250 rows a page).

### Renewals
- **Header** with the **Financial year / Calendar year** switch and the year buttons.
- **Title buttons** - pick one title at a time.
- **Four tiles:** **<last year> advertisers**, **Back in <this year>**, **Retention so far** (per cent of last year's advertisers who are back) and **Not back yet** (what those still missing spent last year).
- A note about the **Renewal outreach** automation.
- **Filter sidebar**, search, and **Book renewals into** (which edition new bookings go into).
- **The table:** **Advertiser** (and CRM company), **Last booking** (edition, size, value and booking date), **Spent last year** (and how many bookings), **Salesperson**, and a **New booking** button. An amber "booking date looks wrong" line links to the booking that needs fixing.

## Buttons and controls
### New booking (All items header)
Opens the full booking form, for a proper booking with a confirmation.

### Search bookings
Searches client, invoice number, order reference, size, notes, reason for difference, edition name, CRM company and salesperson name or initials.

### Filters (All items)
- **Year**, **Type** (Print, Digital, Events, Awards), **Title**
- **Salesperson** - includes bookings the person shares a credit on
- **Status** - Booked, Pencilled (held for the client, not confirmed yet), Cancelled, Contra, Moved
- **Invoice** - Invoiced / Awaiting invoice (live bookings with a value and no invoice number)
- **Payment (Xero)** - Draft in Xero (the invoice is made in Xero but not sent to the client yet), Paid, Part paid, Unpaid, Overdue, Voided, Not found in Xero
- **CRM company** - Linked / Not linked
- **Import check** - Needs a check / No issues
- **Filler ads** - Filler ads / Sold space
- **Value**, **Booked on** and **Edition / event date** ranges

### Column headings
Click to sort; click again to reverse.

### Export
Downloads exactly the filtered, sorted list as an Excel sheet (up to 20,000 rows).

### Client name (or anywhere on a row)
Opens the item sheet on the right. Clicking the CRM company opens the company; clicking the edition opens the edition page.
Drag the grip on the sheet's left edge to make it wider (or narrower); once it's wide, its sections sit side by side. It remembers the width for every side panel; double-click the grip to go back to the usual width. **Ask the Brain** and **Feedback** stay just outside the sheet and can be used without closing it.

### The item sheet
- **Client (as it should appear on the order)** - start typing to reuse a name already on the register, so one advertiser doesn't end up under three spellings.
- **CRM company** - link the item to its company record.
- **Size / product**, **Series**, **Page / position**, **Value (£)**, **Rate (US$)**, **Booked on**.
- **Credited to** and **Split** - share a booking between salespeople. **Add person** adds another share and the bin beside a share (**Remove this share**) takes it off; the shares total is shown in amber if it doesn't match the value. **Go back to one salesperson** undoes the split.
- **Invoice** - **Invoice number**, **Invoiced (£)**, **Invoiced on**, **Agency cut (£)** and **Reason for difference**. When the item is linked to a Xero invoice the amount and date come from Xero and can't be typed. **Open in Xero**, picking an invoice from Xero, and undoing a match are covered in the "Invoicing" guide.
- **Status** - **Booked**, **Pencilled**, **Cancelled**, **Contra** or **Moved**. Pencilled items are held for the client but not counted in totals or commission. For Moved, choose the edition under **Moved to** (this year's or next year's editions of the same title).
- **Notes** and the **Filler ad** tick box.
- **Mark checked** - on items the spreadsheet import flagged, once you've checked them.
- **Show change history** - who changed what, and when.
- **Save changes** (or **Add item**), **Cancel**.
- **Delete** - administrators and data managers only, and only for an item with no booking behind it. It can't be undone; use **Cancelled** to keep a record instead. For an item that belongs to a booking, **Remove it on the booking** opens the booking in a new tab instead.
- On an item that belongs to a booking, the client, CRM company, value, booking date, agency cut and salesperson are shown but can't be typed in; **Change this on the booking** opens the booking in a new tab.

### Financial year / Calendar year and year buttons (Renewals)
Choose which year counts as "this year". Financial years run July to June. Last year's advertisers are the ones who booked into the previous year's editions.

### Title buttons (Renewals)
Show renewals for that title.

### Filters (Renewals)
**Salesperson** (or "No salesperson"), **CRM company** (Linked / Not linked), **Spent last year**, **Frequency** (Booked more than once / Booked once), **Last size booked**, **Last booked on**, and **Booking date** (Looks wrong / Looks fine).

### Book renewals into
Choose the edition that **New booking** should use. It starts on the next open edition.

### New booking (on a renewal row)
For an advertiser linked to a CRM company, this opens the full booking form for that company: the client name and confirmation address from the company, the invoice details and agency from their last booking (invoice to, invoice email, agency and agency %), and one empty item in the chosen edition - add what they're buying and the price before saving. For one not linked, it opens the item sheet with the client, salesperson, size and last value filled in - adjust anything and click **Add item**.

### <problem> Open the booking to fix it.
Opens the booking with the odd date in a new tab.

### Revenue & Orders automations →
Opens the automations page where the renewal outreach is set up.

## How it works
- The **booked value (live bookings only)** in the line above the All items table adds up the live (Booked) rows that match your filters, across every page. The footer adds up the live bookings on the current page the same way. The count of bookings includes every status.
- **Live bookings** are those with the status Booked. Cancelled (the sheet's CANX), contra (a free swap with a partner) and moved bookings are kept on record but not counted anywhere.
- **Overdue** means the edition has published or the event has run, and the item still has no invoice number.
- **An invoice difference** is shown when the invoiced amount differs from the value (after any agency cut) by more than £1. If a reason is recorded it's "explained".
- **Items that are part of a booking** (made with the booking form) can't have their client, CRM company, salesperson, value, agency cut, edition, booking date or split changed here. Change those on the booking, so the confirmation and every item stay in step. Invoice details, notes, status and the filler tick can still be changed on the item.
- **Typing an invoice number** fills in the invoiced amount (the value) and today's date if they're blank, and links the item to the Xero invoice with that number. If it isn't in Xero yet, it links by itself once it appears.
- **Every change is recorded** in the change history.
- **Renewals - who counts as "back":** anyone who booked into one of this year's editions of the title, or took any booking with the title during this year, even into an older issue. Booking dates in the future don't count. Someone who has paid this year never gets a renewal email.
- **Renewals - matching:** advertisers are matched on the client name (small spelling differences ignored) or the linked CRM company.
- **Renewals - who is listed:** last year's advertisers with more than £0 spent, not back yet, biggest spend first. The "last booking" is picked by issue date, so a mistyped booking date can't decide it.
- **Booking date looks wrong:** flagged when a booking date is in the future (often a typo like "2035") or more than 60 days after the issue came out.
- **Renewal outreach** (when switched on) drafts a renewal email for each advertiser as the anniversary of their booking approaches, and puts it in their salesperson's Review Queue. It never sends on its own.

## Common questions
**Q: How do I find everything a client has booked?**
A: Type the client's name in **Search bookings** on **All items**.

**Q: How do I list what's still to invoice for one title?**
A: On **All items**, tick the title under **Title** and choose **Awaiting invoice** under **Invoice**. Click **Export** if you need it as a sheet.

**Q: How do I split a booking between two salespeople?**
A:
1. Click the client to open the item.
2. Click **Split** next to **Credited to**.
3. Choose each person and their £ share (they should add up to the value).
4. Click **Save changes**.

**Q: A client cancelled. Should I delete the item?**
A: No. Open it, choose **Cancelled** under **Status** and click **Save changes**. It stays on record but stops counting.

**Q: How do I move a booking to a later issue?**
A: Open it, choose **Moved**, pick the edition under **Moved to**, and save. Then add it to the new edition so it counts there once.

**Q: How do I mark a filler ad?**
A: Open the item, tick **Filler ad**, and click **Save changes**.

**Q: Who should I call first for renewals?**
A: Open **Renewals**, pick the title, and work down the list - it's sorted by what each advertiser spent last year. Use **Salesperson** to see only your own.

**Q: How do I book a renewal straight away?**
A: Choose the issue in **Book renewals into**, then click **New booking** on the advertiser's row.

**Q: Why is an advertiser I know has rebooked still on the Renewals list?**
A: Their new booking may be under a different client name and not linked to the same CRM company, or its status isn't Booked yet. Link both to the same CRM company to match them.

## If something doesn't work
- **"This item is part of order <number>. Change the client, issue, price or salesperson on the order..."** Open the booking (the link at the top of the item sheet says "Part of Order <number>") and make the change there.
- **Delete is missing.** Only administrators and data managers can delete items, and an item that belongs to a booking is removed or cancelled on the booking (**Remove it on the booking**).
- **"This item is part of booking N..."** Open the booking (**Change this on the booking**) and change it there.
- **"Only administrators and data managers can delete a booking - mark it cancelled instead."** Use **Cancelled** instead.
- **"Enter the client's name."** The client box is empty.
- **"Amounts must be numbers, e.g. 1250 or 1250.50."** Remove any letters from the money boxes.
- **"Choose a salesperson for every share of the split."** Pick a person for each share, or remove the empty one.
- **I can't type in Invoiced (£) or Invoiced on.** The item is linked to a Xero invoice, so those come from Xero.
- **I can't filter by Pencilled.** The Status filter doesn't offer it yet. Pencilled items still show in the list with an amber pill.
- **New booking is greyed out on a renewal row.** There is no edition to book into - create the edition first.
- **Renewals says "No <last year> bookings for this title".** Nothing was booked for the title last year, so there's nothing to compare.
- **Renewals says "Everyone's back".** Every advertiser from last year has booked again.
