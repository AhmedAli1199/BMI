---
title: Bookings list
screens: ["/sales/deals"]
summary: Every client booking in one list, with filters for status, salesperson, title and what's due to invoice, plus the bookings settings (confirmation details, hand-offs, online forms, Xero codes).
sources: ["frontend/src/app/(app)/sales/deals/page.tsx", "frontend/src/components/deals/deal-ui.tsx", "frontend/src/components/deals/booking-forms.tsx", "frontend/src/components/deals/deal-settings.tsx", "frontend/src/components/deals/handoff-routes-button.tsx", "frontend/src/components/deals/xero-codes-button.tsx", "backend/app/api/routes/deals.py", "backend/app/api/routes/booking_forms.py", "backend/app/sales/deals.py", "backend/app/sales/accounts.py"]
---

## What this screen is for
The Bookings list (Sales Orders > Bookings) shows every client booking. A booking holds everything the client agreed: the items across issues, months and events, the price, any discounts and any agency commission. Each booking prints as BMI's order confirmation or schedule of works. Use this list to find a booking, check what is still pencilled or not yet sent, and see what is due to invoice.

## What you see
- **Header**: the title "Bookings", a short description, and buttons on the right: **Online forms**, **Confirmation details**, **Hand-offs**, **Xero codes** and **New booking**. You only see the buttons your role allows (see below).
- **Filter bookings** sidebar on the left, with a search box above the table and chips for each filter you have switched on.
- **Summary line** above the table: how many bookings match, their total value (cancelled bookings are left out), and, if some items are not yet placed in an issue, "of which £X still to be allocated" with a link to those bookings.
- **The table**, newest booking number first:
  - **Booking**: the booking number. Click it to open the booking.
  - **Client**: the client name as booked. Underneath: "via <agency>" if booked through an agency, "PO <number>" if there is one, and the order date.
  - **Runs**: how many items, and the first and last dates they run. "+ N to allocate by <date>" means some items have no issue chosen yet. It turns amber once the decide-by date has passed.
  - **Salesperson**: the main salesperson.
  - **Total**: the booking total before VAT.
  - **Invoiced**: the value of items that already have an invoice number.
  - **Status**: a coloured pill. **Pencilled** (amber) is held for the client but not confirmed. **Confirmed** (green) means the client has said yes. **Cancelled** (red) is kept on record but no longer counts. "not sent yet" in amber under a confirmed booking means the confirmation has not been emailed or marked as sent.
- **Pages** at the bottom, with 50, 100 or 200 bookings per page.

## Buttons and controls

### Search bookings
Type a client name, booking number, PO number, contact name or agency name. A number on its own also finds that booking number.

### Status
Tick **Pencilled**, **Confirmed** and/or **Cancelled** to show only those.

### Whose: Only my bookings
Shows bookings where you are the main salesperson, or that you created.

### To invoice
- **Due to invoice now**: confirmed bookings with at least one item that has reached its invoice date and has no invoice yet.
- **Due by the end of this month**: the same, for anything due by the last day of this month. Use it for the month-end check.

Items marked "No invoice needed", free items and items worth £0 are left out.

### Still to allocate: Has items with no issue yet
Shows bookings (not cancelled) with items that were sold but not yet placed in an issue, such as packages sold for the year.

### Salesperson
Shows bookings whose main salesperson is one of the people you tick. Only active salespeople are listed.

### Title
Shows bookings with at least one item in the chosen magazines or events. You can search the list.

### Ordered in
Shows bookings by the year of their booking date (next year, this year and the two years before).

### Booking, Client and Total column headings
Click to sort. Click again to reverse the order.

### New booking
Opens the blank booking form. You can also start a booking from a company page, an issue, or a proposal the client has agreed to.

### Confirmation details
Opens a side panel with what every order confirmation and schedule of works carries. Everyone can look, but only administrators can change it. Others see "Only administrators can change these."
- **Next booking number**: the number the next new booking gets. It must be higher than any booking that already exists.
- **BMI's name and address (top right)**.
- **Terms line (general)**, plus **Terms for each publication**. A publication with its own terms prints those; leave one empty to use the general terms.
- **Artwork specification**: printed when a booking has "Print the artwork specification" ticked.
- **Production - always copied on confirmations** and **Accounts - always copied on confirmations**: these addresses get a copy of every confirmation emailed from BMI Brain. The Accounts addresses also get every new booking by email as soon as it is created, with its confirmation attached.
- **Filled in on every new booking**: **Production contact**, **Copy and artwork** and **Special instructions**. These are typed into each new booking for you, and the salesperson can still change them. If the production contact is left empty, the first production address is used.
- **Footer**.
- **Save** and **Cancel** (administrators only).

### Hand-offs
Administrators only. Opens "Who gets the hand-offs": the editorial and production email addresses for each magazine, plus an **Every magazine** row used when a magazine has no row of its own. The booking form suggests these addresses on each item. Once accounts have checked a booking, each item is emailed to editorial (sponsored content, social media) or production (adverts, banners, HTML emails). Separate several addresses with commas. Press **Save**.

### Online forms
Administrators and data managers only. Opens "Online booking forms", the list of connected Jotform and Stova forms (awards entries, event seats, the Quiz). Each entry someone sends arrives in the Review Queue under Online bookings, ready to become a booking without retyping.
- Each form shows what each entry becomes, how many entries have come in, a **see them** link (opens the Review Queue in a new tab), its address and a **Copy** button.
- Pencil button (**Change <form name>**): edit the form.
- Bin button (**Remove <form name>**): removes the form after you confirm. Entries sent to its address after that are turned away. Bookings already made stay.
- **Add a form**: fill in **Name**, **Where it comes from** (Jotform, Stova or Another form), **Title**, **Issue or event** (leave as "Not decided - allocate each booking later" for a form that runs all year), **Each entry is** (for example "Awards entry"), **Price each (£, before VAT)**, **Salesperson** (or House account) and **Taking entries**. **Save** needs a name and a title. **Back** returns to the list.
- To connect a form: add it here and copy its address. In Jotform, open the form, then Settings, Integrations, Webhooks, and paste the address. In Stova, ask for entries to be sent to the address. Send a test entry; it shows up in the Review Queue within a few seconds.

### Xero codes
Accounts only (or administrators while accounts are away). Sets the Xero account, item and tracking codes used on draft invoices, for each publication or for every publication. This is covered in the invoicing guide.

## How it works
- Booking numbers carry on from BMI's old numbering. Each new booking takes the next number.
- **Pencilled** bookings hold the space but do not count in sales figures, issue totals or commission until they are confirmed.
- **Confirmed** bookings count. If the accounts check is switched on, confirming puts the booking in front of Accounts to check.
- **Cancelled** bookings stay on record with their reason. Items that had already run or been invoiced can stay booked.
- The total in the summary line adds up every booking that matches your filters, except cancelled ones.
- Items "still to be allocated" count in the booking total but are not on the order register or in any issue's figures until an issue is chosen.
- When an item is due to invoice depends on the booking's "When to invoice" choice and the date the item runs. Quarters follow BMI's financial year, which starts on 1 July.

## Common questions
**Q: How do I find a client's bookings?**
A: Type the client's name in **Search bookings**. Or open the company page and use its Bookings tab.

**Q: How do I see just my bookings?**
A: In the filter sidebar, under **Whose**, choose **Only my bookings**.

**Q: Which confirmations haven't gone to the client yet?**
A: Filter **Status** to **Confirmed** and look for "not sent yet" under the status pill.

**Q: How do I do the month-end invoicing check?**
A: Under **To invoice**, choose **Due by the end of this month**. Each booking listed has at least one item due by then that has not been invoiced.

**Q: Which packages still need their issues chosen?**
A: Under **Still to allocate**, choose **Has items with no issue yet**, or click the "N bookings" link in the summary line. Open each booking and use **Choose the issues**.

**Q: How do I start a new booking?**
A: Press **New booking**. To have the client's details filled in for you, start from the company page or from an agreed proposal instead.

**Q: How do I connect a Jotform awards entry form?**
A: Press **Online forms**, then **Add a form**. Fill in the name, title, issue or event and price each, then press **Save**. Press **Copy** next to its address, and paste it in Jotform under Settings, Integrations, Webhooks.

**Q: How do I change BMI's address or terms on confirmations?**
A: Press **Confirmation details**. Only administrators can change and save it.

**Q: Where do I set who gets the editorial and production emails for a magazine?**
A: Press **Hand-offs** (administrators only), fill in that magazine's row and press **Save**.

## If something doesn't work
- **I can't see Online forms.** Only administrators and data managers can set up booking forms.
- **I can't see Hand-offs.** Only administrators can see and change the hand-off addresses.
- **I can't see Xero codes.** Only Accounts can, or administrators while "Accounts are away" is on.
- **Confirmation details fields are greyed out.** Only administrators can change them.
- **"Booking N already exists, so the next number has to be higher."** The next booking number must be above the highest number already used.
- **"... doesn't look like an email address."** One of the addresses you typed in Confirmation details or Hand-offs is missing an @. Separate addresses with commas.
- **A booking I share with someone doesn't appear under Only my bookings or the Salesperson filter.** Both filters look at the main salesperson (and, for Only my bookings, who created it), not at shared splits.
- **"No bookings here yet".** Nothing matches your filters. Clear the chips, or start one with **New booking**.
- **Save on an online form is greyed out.** Give the form a name and choose a title.
