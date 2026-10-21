---
title: Sales Orders cards in the Review Queue
screens: ["/automations/review"]
summary: Every kind of Review Queue card that comes from Sales Orders - booking checks, Ready to invoice, change requests, invoice matching and more - and what each button on them does.
sources: ["frontend/src/components/review-item-card.tsx", "frontend/src/app/(app)/automations/review/page.tsx", "frontend/src/components/sales/invoice-match-panel.tsx", "frontend/src/components/deals/xero-invoice-button.tsx", "backend/app/automations/order_checks.py", "backend/app/automations/invoice_due.py", "backend/app/automations/booking_changes.py", "backend/app/automations/allocations.py", "backend/app/automations/sor_checks.py", "backend/app/automations/xero_matching.py", "backend/app/automations/booking_forms.py", "backend/app/automations/sales_orders.py", "backend/app/automations/save_the_sale.py", "backend/app/automations/client_owners.py", "backend/app/automations/workstreams.py", "backend/app/api/routes/review_queue.py", "backend/app/sales/accounts.py"]
---

## What this screen is for
The Review Queue (Automations > Review queue) is where the Brain puts things that need a person's decision. These Sales Orders cards cover checking bookings, invoicing, change requests, matching Xero invoices and similar jobs. They belong to the "Revenue & Orders" group. Each card shows everything you need to decide, with links to every record it mentions, and one button for each decision.

## What you see
- **Tabs**: **Pending** (the working queue), **Approved**, **Rejected** and **Snoozed** (what was decided). A button counts as approved, rejected or snoozed depending on the action. **Remind me on…**, **Not yet - next week**, **Remind me next week**, **Look again next week** and **Not yet - remind me later** count as snoozed, not rejected.
- **A chip for each kind of card**, with a count. Click one to see only that kind.
- **Filter by:** filters for the chosen kind, such as Salesperson, Title or Due, with counts.
- **Sort**: kinds with a date offer **Latest <date> first**, **Oldest <date> first** and **Recently added**.
- **Each card**: the kind in capitals, how long ago it arrived, a one-line summary, and **View company record** if it is about a company. Below that are the details (blue values are links), **Every record this affects**, and the action buttons. Every link opens in a new tab, so you keep your place.
- After you act, the card turns green ("Recorded on the CRM. Moving to the next item…").

Buttons that need more information open a small form under the card. Fill it in, then press **Confirm <action>**, or **Cancel**. A **Note** box ("Why, or any context worth keeping on the record…") must be filled in where the action asks for one.

**Who sees what**: cards marked "Accounts" are seen only by people with the Accounts permission. Administrators see them too while **Accounts are away** is on, or if nobody has the Accounts permission yet. Salespeople see the "sales" cards. Items to allocate and renewals show only to the salesperson they belong to.

## Buttons and controls
### Booking check (Accounts)
A confirmed booking, or a checked one whose client, addresses or items changed. It shows the booking, client, CRM company, contact, addresses, PO, agency, items, total, salesperson and when to invoice. "Worth a look" appears if the client name differs from the linked CRM company. "Asked to fix last time" appears when it comes back after a fix. Filters: Salesperson, Title, CRM company. Sorted by booking date.
- **Looks right**: marks the booking checked. It locks (changes then go through Accounts), and the hand-off emails go to editorial and production.
- **Needs a fix**: needs a note. The salesperson and whoever made the booking get "Booking <number> needs a fix before it's invoiced" with your note. When they save the booking, it comes back to you.

### Ready to invoice (Accounts)
One card per booking, listing the items whose invoice date has arrived. It shows each item with its issue, run date and value, plus the total before VAT, when to invoice, invoice instructions, invoice to, PO number, agency, currency, CRM client and salesperson. Filters: Salesperson, Title, When to invoice, Due (Due now / Overdue a week or more). Sorted by due date.
- **Create the invoice in Xero**: makes a draft invoice in Xero for these items (see the "Draft invoices in Xero" guide). The card closes by itself once it's made.
- **Already invoiced in Xero**: you raised it yourself. Type the **Invoice number from Xero**. It goes on each item with the booking value and today's date, and the Xero sync links it. The booking locks.
- **Remind me on…**: pick a date after today. The items get that date and the card closes; a new card comes on the day.
- **Not yet - next week**: the same, for a week from today.
- **No invoice needed**: needs a note. The items are marked "No invoice needed" and never come back.

### Booking change (Accounts)
A salesperson wants to change or cancel a checked booking. It shows who asked and why, what changes (items added, removed or changed, the new total) and the knock-on: issues it leaves or moves into, and invoiced items that would need a credit note. Filters: Salesperson, Kind of change, Invoiced items. Sorted by request date.
- **Approve and apply**: applies it exactly as asked (or cancels the booking). It stays checked. The salesperson is told, with a reminder to send an updated confirmation if the client needs one.
- **Decline**: needs a note, which is sent to the salesperson.

### Items to allocate (the salesperson)
A booking with items sold but no issue chosen, as the "decide by" date or the title's next booking deadline gets close. Links go to the booking, the client and the next issue. Filters: Salesperson, Title, When. Sorted by decide-by date.
- **All allocated**: closes it. It only works once every item has an issue. The card also closes by itself when they're all allocated.
- **Remind me next week**: hides it for 7 days.

### Who looks after a client (administrators and data managers)
A client the Brain couldn't place with a salesperson by the agreed rules, usually a Selling Travel client with no destination it can find. It asks once per client and magazine, at most 50 new cards a night, most recently active first. The card links to the client (and its website), says why it isn't sure, and gives a suggestion if someone was in touch long ago. Filters: Magazine, Suggestion, Why. Sorted by last contact (Latest contact first or Oldest contact first).
- **Use the suggestion**: that salesperson looks after the client. Also works for several cards at once.
- **Someone else**: pick the **Salesperson** from the drop-down (that magazine's team).
- **Not now**: closes the card without deciding. It isn't asked again; change it on the company page instead.
- Your answer is kept for good, the same as pressing **Change** on the company page. The card closes by itself if a note or booking settles it first.

### Issue gone to press (Accounts)
A few days after an issue's copy deadline: anything in its order register worth a look before invoicing. That means items with no booking, items that don't match their booking, items still pencilled, confirmations never sent, and packages for that title still to allocate. It also shows how many items are still to invoice and how many filler ads there are. Each row links to the item, booking or issue. Up to 40 rows are shown, then "And more". Filters: Title, What it found. Sorted by issue date.
- **All checked**: closes it. It won't come back for that issue.
- **Look again next week**: brings it back after a week.

### Invoice to booking (salespeople and managers)
A new Xero invoice that isn't clearly one booking's. On the left is the invoice (number, payment state, customer, reference, what it's for, dates, amounts) with **Open in Xero**. On the right are the likely bookings, each marked **Strong**, **Likely** or **Possible match**, with **Open booking**, the issue link and a checklist of why (client, amount, issue, timing). "Why this needs you" says what stopped it linking by itself. If there's more than one booking, click the right one to select it; the first is selected to start with. Filters: Salesperson, Title, Invoice status, How sure, Why it needs you.
- **Yes, link this invoice**: puts the invoice number, amount and date on the selected booking(s) and shows its payment state. Nothing changes in Xero. Afterwards, the Approved tab shows the link with **Undo this link**.
- **None of these**: remembered. Those bookings aren't offered for this invoice again, but a booking entered later can still be suggested. If nothing fits, it shows on Invoicing > In Xero, not in the register.
- **Not a booking**: for a cost share, refund or other money that isn't a sale. It's never matched again, and it's listed under "Marked as not a booking" on the Invoicing page, where it can be put back.

### Online bookings (salespeople and managers)
An entry from an online booking form (awards, event seats, quiz teams). Filters: Form, Client. Sorted by date received.
- **Create booking**: optionally type **Client name, if different from the form** and **How many, if different from the form**. It makes a confirmed booking, which goes to the accounts check, and adds a "Booking made" link to the card.
- **Not a booking**: needs a note.

### Uninvoiced Bookings (administrators and data managers)
An item on the order register whose issue has published, still with no invoice number. While Ready to invoice reminders are on, bookings made in the Brain get Ready to invoice cards instead, so these are for imported rows. The client, edition, item and booking on the card each open in a new tab. Filter by **Salesperson**, **Title** or **Waiting** (under 30 days, 30-90 days, over 90 days), and sort by publication date.
- **Record invoice**: type the **Invoice number** and, if different, the **Invoice value (£)**. Blank means the booking value.
- **Not yet - remind me later**: comes back after the snooze period in the settings.
- **No invoice needed**: needs a note.

### Order Register Client Matching (administrators and data managers)
"Is SOR client <name> the CRM company <company>?", with the number of bookings affected and how alike the names are. The client's bookings and the suggested company each open in a new tab. Filter by **Title** or **How close the names are**, and sort by the latest booking.
- **Yes - link all their bookings**: links every unlinked booking with that client name to the company.
- **Not the same company**: they aren't suggested again.

### Renewal Outreach and Save the sale (the salesperson)
Drafted emails: a renewal for last year's advertisers, or a reply to a client who said no. **Send from my Outlook** and **Log to CRM only** first open the draft, so you can edit it or **Regenerate** it with instructions.
- **Send from my Outlook**: sends it to the address given, then logs it on the CRM.
- **Log to CRM only**: logs it on the CRM without sending, so you can send it another way.
- **Skip this year** (renewals) or **Let it go** (save the sale): closes it without sending.

Renewal cards link the advertiser's CRM company, last year's booking, the issue to offer and the previous ad online, each in a new tab. Filter renewals by **Salesperson**, **Title**, **Price** (on this year's rate card or not) and **Recipient** (has an email address or not), and sort by renewal date.

## How it works
- Most cards update themselves. A booking check always shows the latest version of the booking. It is withdrawn if the booking goes back to pencilled. A Ready to invoice card closes when nothing on it is due any more. An Invoice to booking card closes if someone types that invoice number on a booking first.
- Ready to invoice cards are made each weekday at about 7am and whenever a booking is saved. Accounts also get a bell notification and an email. Booking checks arrive when a salesperson presses Confirm, also with a notification.
- Issue gone to press cards are made each weekday morning for issues whose copy deadline passed a set number of days ago (within the last 45 days). Items to allocate cards are made each weekday morning.
- Each of these automations can be switched on or off by an administrator in the Revenue & Orders automation settings.

## Common questions
**Q: Where do I find the bookings I need to check?**
A: Open the Review Queue and click the **Booking check** chip. You need the Accounts permission.

**Q: How do I invoice from a Ready to invoice card?**
A: Press **Create the invoice in Xero**, check the draft in the dialog, then press **Open it in Xero** to approve and send it.

**Q: The client asked us to wait until next month.**
A: Press **Remind me on…**, pick the date and press **Confirm remind me on…**.

**Q: The booking is fine except the PO number. What do I do?**
A: Press **Needs a fix**, write what's wrong in the note, and confirm. The salesperson is told, and the booking comes back to you when they save it.

**Q: I linked the wrong invoice from an Invoice to booking card.**
A: Open the **Approved** tab, find the card and press **Undo this link**. Or open the item, press **Edit booking** and use **Undo this link** in the Invoice section.

**Q: How do I check a card's booking without losing my place?**
A: Click the booking number in the details, or **Open booking**. It opens in a new tab.

**Q: Why did a Ready to invoice card disappear?**
A: Nothing on it is due any more. It may have been invoiced and matched, moved to a later date, or cancelled.

## If something doesn't work
- **I can't see Booking check, Ready to invoice, Booking change or Issue gone to press cards.** They're for Accounts only. Administrators see them only while **Accounts are away** is on.
- **"Only accounts can check bookings." / "Only accounts can record invoicing." / "Only accounts can approve changes to a checked booking." / "Only accounts can sign off the order register check."** You don't have the Accounts permission.
- **"Say what needs fixing, so the salesperson knows." / "Say why, so the salesperson knows what to do next."** Fill in the note.
- **"Enter the invoice number from Xero."** Type the number before confirming.
- **"Choose a date after today."** Remind me on… needs a future date.
- **"Booking <number> still has N items with no issue..."** Open the booking, press **Choose the issues**, then press **All allocated**.
- **"This booking has been cancelled since the change was asked for."** The change can't be applied now; decline it.
- **"Pick which booking this invoice is for."** Click one of the bookings first.
- **"That invoice has been voided or deleted in Xero..." / "This invoice is already linked to..."** Nothing is left to link; choose **None of these** or **Not a booking**.
- **"The <form> form has no price yet" / "isn't linked to a title yet."** A manager fixes the form in Bookings settings, then try again.
- **"Connect your Outlook first (Settings › Email)..."** Connect Outlook to send renewals or save-the-sale replies, or use **Log to CRM only**.
