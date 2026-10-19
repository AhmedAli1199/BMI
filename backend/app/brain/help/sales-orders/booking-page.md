---
title: Booking page
screens: ["/sales/deals/[id]", "/sales/deals/[id]/print", "/sales/orders/[id]"]
summary: One booking with its status, totals, schedule of items and details, and the actions to confirm, email, print, rebook or cancel it; plus the printable confirmation and the page for a single item.
sources: ["frontend/src/app/(app)/sales/deals/[id]/page.tsx", "frontend/src/components/deals/deal-actions.tsx", "frontend/src/components/deals/deal-invoicing.tsx", "frontend/src/components/deals/deal-handoffs.tsx", "frontend/src/components/deals/xero-invoice-button.tsx", "frontend/src/app/(app)/sales/deals/[id]/print/page.tsx", "frontend/src/components/deals/print-button.tsx", "frontend/src/app/(app)/sales/orders/[id]/page.tsx", "frontend/src/components/sales/booking-editor.tsx", "frontend/src/components/sales/order-sheet.tsx", "frontend/src/components/commission/booking-new-business.tsx", "backend/app/api/routes/deals.py", "backend/app/sales/deals.py", "backend/app/sales/accounts.py", "backend/app/automations/order_checks.py", "backend/app/sales/invoicing.py"]
---

## What this screen is for
The booking page shows one booking: what was sold, where each item runs, what it's worth, and where it is with Accounts. From here you confirm it, email or print the confirmation, rebook it for next year, change it or cancel it. Accounts also invoice from this page. The invoicing, locking, Xero and hand-off panels are covered in more depth in the invoicing guide; their buttons are listed briefly below.

## What you see
- **Header**: "Booking <number>: <client>". Underneath: the months it runs in, who sold it (with each person's % if shared), and the order date. The action buttons are on the right.
- **Status line**: the status pill. **Pencilled** (amber) says it's held for the client and doesn't count in sales figures or commission until it's confirmed. **Cancelled** (red) shows the reason. **Confirmed** (green) shows "Confirmation sent <date> to <address>", or in amber "The confirmation hasn't been sent yet". It also links to "Rebooked from booking <number>" or "From a proposal" (new tab) where that applies.
- **Accounts check banner** (when the accounts check is on): green **Checked by accounts** (who and when; it's ready to invoice when it's due), amber **Waiting for the accounts check**, or amber **Accounts asked for a fix** with their note. After a fix, change the booking and save it; it goes back to them.
- **Lock banner**: **Locked.** once Accounts have checked it or anything is invoiced, or **Unlocked by <name>** when Accounts have opened it for the salesperson.
- **Change or Cancellation waiting for accounts**: who asked, why, and the details. The booking stays as it is until they approve.
- **Still to be allocated banner**: how many items and their value have no issue yet, with the decide-by date (amber once it's passed) and a **Choose the issues** link.
- **Warnings** in amber: for example an item booked after its advertising deadline, an issue marked closed, an invoice date a quarter before the item runs, or package shares that didn't add up.
- **Totals tiles**: **Booking total** (before VAT), **Agency commission**, **To invoice in all** (total less agency), **Invoiced so far**, **Ready to invoice** (due now and not invoiced) and **Below rate card**.
- **Schedule**: one row per item, in date order. **Runs** (with "ran" once it's past), **Item** (opens the item in a new tab; "Free" and "cancelled" tags), **Issue, month or event** (opens the issue in a new tab, or "To be allocated"), **Copy due** (amber and bold within 14 days), **Value** (and any agency share), and **Invoice** (the invoice number and its Xero state such as Draft in Xero, Paid, Part paid, Awaiting payment, Overdue, Voided or Not found in Xero; or "Ready to invoice", "Due <date>", "Date not known yet", "Once it's allocated"). Cancelled items are struck through. A badge shows how many are ready to invoice.
- **Hand-offs to editorial and production**: each item's team, addresses and state: Sent, Didn't go, No address yet, Waiting for the format, Goes after the accounts check, or Ready to send.
- **Details**: Their contact, Confirmation address, Invoice to, Their order or PO number, Agency, When to invoice (with currency and instructions), Xero contact, Copy and artwork from, Client company (new tab), Document, Special instructions, Copy and artwork, Production contact and Notes for the team.

## Buttons and controls

### Change / Request a change
Opens the booking form. It says **Request a change** when Accounts have checked the booking and you're not in Accounts; then your change goes to them for approval. Shown to the salesperson, anyone in the split, whoever created it, managers and Accounts. Not shown on a cancelled booking.

### Confirm
Pencilled bookings only. Marks it confirmed (the client has said yes). Its items now count in sales figures and commission, and it goes to Accounts to check if the check is on.

### Email the confirmation / Email the schedule of works
Opens an email with **To** (the contact's email), **Copy to (optional)**, **Subject** and **Message** filled in. **Send** sends it from your own Outlook with the confirmation attached as a Word file, and notes it on the client's company. Production and accounts addresses from Confirmation details are always copied. Sending a pencilled booking confirms it. **Close** shuts it without sending. If your Outlook isn't connected, the dialog tells you to connect it in Settings > Email, or to download it and use **I sent it another way**. The button is highlighted while a confirmed booking hasn't been sent yet.

### Print or PDF
Opens the printable confirmation in a new tab (see below).

### ... (More) menu
- **Download as Word**: the confirmation as a Word file, named like "Order confirmation <number> <client>.docx". Anyone can download it.
- **I sent it another way**: notes it as sent to the contact's email and adds a note to the client's company, without emailing anything.
- **Rebook for next year**: makes a new pencilled booking for the same client, with each item moved to next year's matching issue at next year's rate card price. Notes say what couldn't be matched or what prices changed. It opens the new booking. Nothing is confirmed until you confirm it. Shown to people who can change the booking, and not on cancelled bookings.
- **Back to pencilled**: confirmed bookings with nothing invoiced. It stops counting and is taken out of the accounts check.
- **Reopen**: cancelled bookings. Brings it back as pencilled. Only the items the cancellation cancelled come back as pencilled; items kept booked because they had already run or been invoiced stay booked.
- **Cancel the booking** / **Ask accounts to cancel it**: opens a dialog. Type **Why** (required) and choose **Keep items that have already run or been invoiced** (ticked by default: they were delivered, so they stay booked). Press **Yes, cancel the booking** (or **Yes, send to accounts** on a locked booking), or **No, keep it** to back out without changing anything.
- **Delete**: pencilled bookings with nothing invoiced only. Asks you to confirm, then removes the booking and its pencilled items.

### Choose the issues
In the still-to-be-allocated banner. Opens the booking form so you can pick issues for those items.

### Invoicing, lock and hand-off buttons (see the invoicing guide)
- **Unlock for the salesperson** (Accounts): asks for an optional note, then lets the salesperson change it. It locks again when they save. **Lock it again** undoes that.
- **Create the invoice in Xero (N)** (Accounts, confirmed bookings): makes a draft invoice in Xero for the items ready to invoice. **Invoice it now** does the same for one item that isn't due yet. A dialog shows the draft (**Open it in Xero**, **Done**), or lists what to fix with **Make the draft invoice**.
- **Due <date>** in the Invoice column (Accounts): opens **Remind me to invoice on** with **Save**, **Booking's rule** (back to the booking's timing) and **Cancel**. The salesperson is told.
- **Send** / **Send again** next to each team on a hand-off (once it's confirmed and Accounts have checked it, or just confirmed if the check is off; it goes to that team only), and **Save and tell editorial** when a sponsored format is still to be decided. On a locked booking, **Change hand-off** on each item changes its teams, addresses, format and where else it appears (see the hand-offs guide).

### Printable confirmation page
Shows the confirmation in BMI's layout: ORDER CONFIRMATION "(Invoice to follow)" or SCHEDULE OF WORKS, the date, BMI's address, the confirmation and invoice-to addresses, your contact and ours, the order number and their ref, the publication, insertions, the items table with cost per insertion, discount, agency commission and total, "VAT is not included", special instructions (including copy due dates and the invoice email), production contact, artwork specification, terms and footer.
- **Back to booking <number>** returns to the booking.
- **Print or save as PDF** opens your browser's print window. Choose "Save as PDF" there for a PDF.
- If the booking is still pencilled, a note says to confirm it before sending.

### The item page
Clicking an item in the Schedule opens that one item in a new tab, with its edition, dates, what was sold, salesperson, the booking it belongs to, value and invoice. Its edit panel opens straight away; **Edit booking** reopens it. In the panel:
- Client, CRM company, size, series, page, value, booking date and salesperson can be seen, but on an item from a booking the client, issue, price and salesperson must be changed on the booking itself.
- **Commission**: the **New business** tick box (the item's credited salesperson or a manager), with **Use the suggestion** to go back to what the system worked out from the last 24 months.
- **Invoice**: invoice number, invoiced amount and date, agency cut and reason for a difference; **Find in Xero**, **Open in Xero** and **Undo this link**.
- **Status**: **Booked**, **Cancelled**, **Contra** or **Moved**; **Notes**; **Filler ad**.
- **Show change history**: who changed what on this item, and when.
- **Mark checked** (for imported rows with a warning), **Save changes**, **Cancel**, and **Delete** (administrators and data managers only).

## How it works
- Pencilled bookings don't count anywhere. Confirming makes every item "booked". Cancelling marks items cancelled, except (by default) any that already ran or were invoiced.
- If the accounts check is on, every confirmed booking gets one check card for Accounts. "Looks right" marks it checked; "Needs a fix" sends the salesperson a note. Pencilled bookings aren't checked.
- A booking locks once Accounts have checked it or any item is invoiced. Then only Accounts change it directly; everyone else's changes and cancellations go to Accounts for approval.
- If the "Confirmation waits for the check" setting is on, a booking can't be emailed or marked as sent until Accounts have checked it. This setting is off by default.
- When to invoice follows the booking's rule and the date each item runs, unless Accounts set their own date. Quarters follow BMI's financial year, which starts on 1 July.
- Hand-offs go out once the booking is confirmed and Accounts have checked it (or when it's confirmed, if the check is off). Each item is sent once, plus one update if it changes after it has gone.
- Rebooking moves each item to next year's issue of the same kind nearest the same date, and uses next year's rate card price if the price was the rate card one.

## Common questions
**Q: How do I send the confirmation to the client?**
A: Press **Email the confirmation**, check the To, Subject and Message, then press **Send**. It goes from your Outlook with the Word file attached.

**Q: I emailed it from my own mail. How do I record that?**
A: Open the **...** menu and choose **I sent it another way**.

**Q: How do I get a PDF?**
A: Press **Print or PDF**, then **Print or save as PDF**, and choose "Save as PDF" in the print window.

**Q: The client said yes. What do I press?**
A: Press **Confirm** (or just email the confirmation, which confirms it).

**Q: How do I rebook a client for next year?**
A: Open the **...** menu and choose **Rebook for next year**. Check the new pencilled booking, then press **Confirm** when they agree.

**Q: The client cancelled. What do I do?**
A: Open the **...** menu, choose **Cancel the booking**, type why, and press **Yes, cancel the booking**. Leave "Keep items that have already run or been invoiced" ticked unless they should go too.

**Q: Why does it say Request a change instead of Change?**
A: Accounts have checked or invoiced it. Make your change, say why, and press **Send to accounts**. It changes once they approve.

**Q: How do I mark an item as new business?**
A: Click the item's name in the Schedule. In its panel, under Commission, tick **New business**.

**Q: Where's the booking's history?**
A: The status line shows when it was sent and to whom, and each sent confirmation is noted on the client's company. For an item, open it and press **Show change history**.

## If something doesn't work
- **Email the confirmation is greyed out**: you can't change this booking, or it's waiting for the accounts check (hover to see "Waiting for the accounts check"). With "Confirmation waits for the check" on, a pencilled booking has to be confirmed and checked first.
- **"Connect your Outlook first (Settings > Email)..."** or **"Your Outlook connection has expired..."**: connect or reconnect your Outlook in Settings > Email.
- **"Outlook is asking us to slow down - try again in a minute."** or **"Outlook didn't accept the email, so nothing was sent."**: try again shortly.
- **"... doesn't look like an email address."**: check the To and Copy to boxes. Separate addresses with commas.
- **There's no Delete**: only pencilled bookings with nothing invoiced can be deleted. Cancel it instead, so it stays on record.
- **There's no Back to pencilled**: something on the booking is already invoiced, or it's locked.
- **No Change button**: the booking is cancelled (use **Reopen**), or you're not its salesperson, in the split, its creator, a manager or Accounts.
- **Rebook says next year's issues aren't all in the editorial plan yet**: plan next year's issues in the editorial plan, then try again.
- **I can't change the price or salesperson on the item page**: items from a booking are changed on the booking, so the confirmation and every item stay in step.
- **No Xero, unlock or invoice-date buttons**: these are for Accounts (or administrators while Accounts are away).
