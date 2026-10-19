---
title: Invoicing
screens: ["/sales/invoicing", "/sales/deals/[id]", "/sales/editions/[id]"]
summary: What still needs invoicing, invoices that don't match their booking, Xero invoices with no booking, and the invoicing parts of a booking - when to invoice, reminders, the accounts check and locking.
sources: ["frontend/src/app/(app)/sales/invoicing/page.tsx", "frontend/src/components/deals/deal-invoicing.tsx", "frontend/src/components/deals/unbooked-ad-button.tsx", "frontend/src/components/sales/invoice-match-panel.tsx", "frontend/src/components/sales/not-booking-controls.tsx", "frontend/src/components/sales/xero-link-dialogs.tsx", "frontend/src/components/sales/order-sheet.tsx", "frontend/src/components/deals/deal-form.tsx", "frontend/src/app/(app)/sales/deals/[id]/page.tsx", "frontend/src/app/(app)/sales/deals/page.tsx", "backend/app/sales/invoicing.py", "backend/app/sales/accounts.py", "backend/app/automations/invoice_due.py", "backend/app/automations/order_checks.py", "backend/app/automations/xero_matching.py", "backend/app/api/routes/deals.py", "backend/app/api/routes/sales.py"]
---

## What this screen is for
The Invoicing page (Sales Orders > Invoicing) shows bookings that still need an invoice, invoices that don't match their booking, and imported rows to double-check. It also lists invoices in Xero that no booking fits. On each booking, the invoicing parts say when each item should be invoiced, remind Accounts on the day, and keep a checked or invoiced booking locked so only Accounts change it.

## What you see
**On the Invoicing page**, top to bottom:
- Four figures: **Overdue**, **Awaiting invoice**, **Difference explained** and **Unexplained difference**, each with a count and value.
- A note that the **Uninvoiced booking scan** can put overdue bookings into the Review Queue, with a link to **Revenue & Orders automations →**.
- A row of views (the "i" next to them explains the one you're on): **Overdue**, **All awaiting invoice**, **Unexplained difference**, **Difference explained**, **Needs a check**, **Not linked to CRM** and **In Xero, not in the register** (with a count).
- For the first six views, a bookings table with filters on the left, a search box and an export button. Click a row to open that item's side panel.
- For **In Xero, not in the register**, a table of Xero invoices: Invoice (opens Xero in a new tab), Customer, What it says it's for, Before VAT, Dated, and two buttons. Above it, a fold-out **Marked as not a booking (N)** list.

**On a booking page**, the invoicing parts are:
- A coloured banner for the accounts check: green **Checked by accounts**, or amber **Waiting for the accounts check** or **Accounts asked for a fix**.
- A grey banner when it's **Locked.** or **Unlocked**, with the lock buttons for Accounts.
- Tiles for **To invoice in all**, **Invoiced so far** and **Ready to invoice**.
- In the schedule, an amber "N ready to invoice" badge, and an **Invoice** column for each item: the invoice number and its Xero state (Paid, Part paid, Awaiting payment, Overdue, Voided, Draft in Xero, Not found in Xero), or **Ready to invoice** in amber, or "Due <date>" / "Date not known yet", or "Once it's allocated" for items with no issue yet. "(set by accounts)" or "· yours" means Accounts chose that date.
- In the details: **When to invoice** (with currency and instructions) and **Xero contact** once one is linked.

## Buttons and controls
### Overdue / All awaiting invoice / Unexplained difference / Difference explained / Needs a check / Not linked to CRM
Switch the list. Your filters (for example one title or one salesperson) are kept when you switch.
- **Overdue**: has a value, no invoice number, and the issue has published or the event has run.
- **All awaiting invoice**: every live booking with a value and no invoice number, including future issues.
- **Unexplained difference**: invoiced for a different amount (after any agency cut) and no reason written.
- **Difference explained**: a different amount, with a reason recorded.
- **Needs a check**: spreadsheet rows the import couldn't read for certain. Open one, fix it and mark it checked.
- **Not linked to CRM**: bookings whose client isn't linked to a CRM company yet (one row per booking).

### In Xero, not in the register
Sales invoices in Xero that don't fit any booking: billed but never entered, or the amount doesn't line up. It is updated each time invoice matching runs.

### Link to a booking
On an invoice in the Xero list. Opens "Which booking is invoice <number> for?" with suggested bookings first, and a search by client name. Press **Link** on the right one (several bookings can share one invoice). The booking gets the invoice number, amount and date. Anyone who can use Sales Orders can do this.

### Not a booking
On an invoice in the Xero list. For money that isn't a sale, such as a cost share, a refund or a recharge. Add an optional note ("What is it?") and press **Not a booking** (or **Cancel**). The invoice is never matched to bookings again, any waiting Review Queue card for it closes, and it moves to **Marked as not a booking**.

### Marked as not a booking (N) and Put back
Click to open the list: invoice, customer, amount, note, who marked it and when. **Put back** undoes it, so the invoice is matched to bookings again on the next matching run.

### Find in Xero and Undo this link (item side panel)
In an item's side panel, under Invoice. **Find in Xero** lists Xero invoices no booking has yet, most likely first; search by number, customer or reference, then **Link**. If the invoice was linked automatically or by a person, the panel shows "Linked to Xero invoice <number>" with **Open in Xero** and **Undo this link**. Undo clears the invoice number, amount and date, and that invoice isn't offered for this booking again.

### When to invoice (booking form)
What the salesperson agreed with the client. The options are:
- **As soon as allowed** (the default): straight away if it runs this quarter, otherwise at the start of the quarter it runs in.
- **When it runs**: the day the issue comes out or the event happens.
- **After it has run**: a few days after it runs (3 by default), for clients who want the tear sheet or link first.
- **On a date agreed with the client**: an **Invoice on** date box appears, and you must fill it in.
- **The quarter after it runs** and **The financial year after it runs**: for clients with no budget left.

Beside it are **Invoice in** (Pounds, Euros or US dollars; prices stay in pounds), **Invoice instructions for accounts (never printed)**, **Invoice to** (with **Same as confirmation**), **Client's order or PO number** and **Email the invoice to**.

### Due <date> / Date not known yet (Invoice column) - Remind me to invoice on
Accounts only. Click the date on an item to open **Remind me to invoice on**. Pick a date and press **Save**, or press **Booking's rule** to go back to the booking's own rule, or **Cancel**. Your date wins over the booking's rule, and the salesperson gets a notification. Everyone else just sees the date.

### Unlock for the salesperson
Accounts only, on a locked booking. You are asked for an optional note. The salesperson and whoever made the booking are notified ("Booking <number> is unlocked for you to change"). It locks again, and goes back to Accounts to check, as soon as they save.

### Lock it again
Accounts only, on an unlocked booking. Locks it again without waiting for the salesperson.

### Create the invoice in Xero / Invoice it now
Accounts only. Makes a draft invoice in Xero. See the "Draft invoices in Xero" guide.

### To invoice (Bookings list filter)
On Sales Orders > Bookings, in the filter panel: **Due to invoice now** (items that have reached their invoice date) or **Due by the end of this month** (for the month-end check).

### Advert with no booking (issue page)
On an issue's page. For an advert in the printed issue that has no booking. Choose the **Client company** (or type the name), the **Page**, and **What is it?**:
- **Someone forgot the booking**: choose the **Salesperson** and press **Ask them to book it**. They get a notification and an email with a link to a new booking for that issue and client. It can be dated back. Only people who can sign in to the Brain are listed.
- **A filler**: press **Record the filler**. A no-charge filler item is added to the issue, with the page noted.

## How it works
- **Quarters follow BMI's financial year**, which starts on 1 July: July-September, October-December, January-March, April-June. BMI invoices in the same quarter the item runs, for VAT.
- **Each item's invoice date** comes from the booking's rule and the item's run date (its own date, or the issue date). If an issue moves, its reminder moves with it. If an issue has no date yet, "As soon as allowed" counts as due now; the other rules wait for a date. A date Accounts set always wins.
- A date agreed with the client that is a quarter before the first item runs shows a gentle warning on the booking. That's allowed if the client asked.
- **Ready to invoice** means: the booking is confirmed, the item is booked, has a value, isn't free, has no invoice yet, and its date has arrived. Accounts get one **Ready to invoice** card per booking in the Review Queue, plus a bell notification and email. Cards are made each weekday morning and updated whenever the booking is saved. A card closes itself when nothing on it is due any more.
- **The accounts check**: when a salesperson presses **Confirm** (or sends the confirmation from Outlook), the booking goes to Accounts as a **Booking check** card. Pencilled bookings aren't checked. If a checked booking's client, CRM company, contact, addresses, PO, agency, items or total change, it is checked again.
- **Locking**: a booking locks once Accounts have checked it, or once any item has an invoice number or Xero link. Locking only happens when someone has the Accounts permission and the setting "Only accounts can change checked bookings" is on. On a locked booking, salespeople use **Request a change**, and Accounts approve or decline it.
- **Who counts as Accounts**: people with the Accounts permission. If nobody has it, administrators and data managers do the checks and nothing is locked. While **Accounts are away** is switched on, administrators can also check, approve, unlock, set invoice dates and make invoices, and they get Accounts' notifications.
- **Invoice matching** (if switched on, hourly): a typed invoice number that matches Xero becomes a real link. A clear match is filled in on its own and noted in the booking's history. Anything less clear becomes an **Invoice to booking** card. **None of these** is remembered, so the same bookings aren't offered again, but a booking added later can still be suggested.
- **Amounts**: a link takes Xero's amount (before VAT, in pounds) only when nobody recorded one. A recorded amount is never overwritten. Differences are compared per client within an issue, and gaps under £2 are ignored.

## Common questions
**Q: How do I see everything that needs invoicing this month?**
A: Go to Sales Orders > Bookings, open the filters and choose **To invoice** > **Due by the end of this month**.

**Q: The client wants to be invoiced in January, not now. What do I do?**
A: Edit the booking, set **When to invoice** to **On a date agreed with the client**, fill in **Invoice on** and save. Accounts can also set their own date on the item with **Remind me to invoice on**.

**Q: I'm Accounts and want to hold an item for two weeks.**
A: On the booking, click the item's date in the Invoice column, pick the new date and press **Save**. Or, on its Ready to invoice card, use **Remind me on…** or **Not yet - next week**.

**Q: I need to change a locked booking. What do I do?**
A: Press **Request a change** on the booking and say why. Accounts approve it, or unlock it for you. Once unlocked, make your change and save; it locks again.

**Q: There's an invoice in Xero for a booking nobody entered.**
A: Open **In Xero, not in the register**. If the booking exists, press **Link to a booking**. If it doesn't, make the booking, then link it. If it isn't a sale at all, press **Not a booking**.

**Q: I marked an invoice "Not a booking" by mistake.**
A: Open **Marked as not a booking**, find it and press **Put back**.

**Q: The wrong invoice was linked automatically.**
A: Click the item's name in the booking's schedule (it opens in a new tab) and press **Edit booking**, or click its row in a bookings table. In the side panel, under Invoice, press **Undo this link**, then use **Find in Xero** to pick the right one.

**Q: Accounts found an advert in the magazine with no booking.**
A: On the issue page press **Advert with no booking**, choose **Someone forgot the booking** and the salesperson, then **Ask them to book it**.

## If something doesn't work
- **"Choose the date to invoice on, or pick another option for when to invoice."** You chose **On a date agreed with the client** but left **Invoice on** empty.
- **I can't see the date editor or the lock buttons.** Only Accounts (or administrators while Accounts are away) see them.
- **"Accounts has checked this booking, so changes go to them for approval."** The booking is locked. Use **Request a change**.
- **"This booking isn't locked, so it can already be changed."** Someone already unlocked it, or it was never locked.
- **"Only accounts can do this (or an administrator while accounts are away)."** Unlocking, relocking and setting invoice dates are for Accounts only.
- **Nothing shows in In Xero, not in the register.** The matching hasn't run yet. An administrator switches on "Xero invoice matching" in the automation settings, or uses Run now.
- **Put back didn't bring the invoice back.** It comes back on the next matching run, and only if invoice matching is switched on.
- **No Ready to invoice cards appear.** Check "Ready to invoice reminders" is on, the booking is confirmed (not pencilled) and the item's date has arrived.
- **"Choose the salesperson who should make the booking."** The salesperson you chose for **Someone forgot the booking** has no login to the Brain, so they can't be told. Choose someone who does.
