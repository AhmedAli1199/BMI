---
title: New booking and change booking form
screens: ["/sales/deals/new", "/sales/deals/[id]/edit"]
summary: The form for making a new booking or changing one - client, items and the issues they run in, prices and discounts, confirmation wording, when to invoice and who each item is handed to.
sources: ["frontend/src/app/(app)/sales/deals/new/page.tsx", "frontend/src/app/(app)/sales/deals/[id]/edit/page.tsx", "frontend/src/app/(app)/sales/deals/_data.ts", "frontend/src/components/deals/deal-form.tsx", "frontend/src/components/deals/line-handoff.tsx", "frontend/src/lib/deals-types.ts", "frontend/src/lib/handoffs.ts", "frontend/src/components/commission/booking-new-business.tsx", "backend/app/api/routes/deals.py", "backend/app/sales/deals.py", "backend/app/sales/invoicing.py", "backend/app/sales/accounts.py", "backend/app/automations/order_checks.py", "backend/app/sales/handoffs.py"]
---

## What this screen is for
This form records everything the client has agreed in one place. Each item you add goes into its own issue, month or event, counts in that issue's figures and earns commission when it runs. The confirmation is printed from what you type here. The same form is used to change an existing booking ("Change booking <number>"), or to ask Accounts for a change once they have checked it ("Request a change to booking <number>").

## What you see
The form has four cards down the left and a **Booking total** panel on the right that stays in view as you scroll.

1. **Client**: who the booking is for and who sold it.
2. **What they've booked**: one card per item (product), with the issues it runs in.
3. **Price**: per-item prices or one package price, discounts and agency.
4. **Confirmation**: what prints on the confirmation, invoicing details, copy and production contacts, and notes.

The **Booking total** panel shows the sums as you type, worked out the same way they are saved: **At rate card**, **Given free**, **Before discount**, **Discount N%**, **Total**, **Agency N%** and **To invoice**. All figures are before VAT. If the booking is more than 5% below rate card (counting anything given free), an amber note says so. The save buttons are at the bottom of this panel.

If you started from a proposal, the description says so and the items, prices and discounts are filled in from the option the client chose. If you started from a company or contact, their details are filled in.

## Buttons and controls

### Client company
Search the CRM for the client's company. Choosing one fills in **Client name as booked**, the confirmation address (from the company's main address), and the invoice details and agency from their last booking. A note then says "Invoice details filled in from their last booking, booking <number>" with a link (opens in a new tab). Check they still apply.

### Their contact
Search for the contact. Choosing one fills in **Contact name** and **Contact email**.

### Client name as booked
How the client appears on the items and the confirmation. Usually the company name, but it can differ (for example "Brunswick - Delice de France").

### Contact name and Contact email
Who the confirmation is addressed to. The email is used as the "To" address when you email the confirmation.

### Salesperson
Who earns the commission. Choose a person, or **House account (no commission)**. You must choose one of these (or set up a split) before saving. On a new booking it starts as you, if you are a salesperson.

### Booking date
The day the client agreed. Items added to the booking later are dated the day they're added, so only what was on the first deal counts as new business.

### Shared with another salesperson?
Opens **Split of the credit (for commission)**. Choose each salesperson and their %. **Add a salesperson** adds a row; the X removes one. The total must add up to 100% ("Adds up to N%" turns red if not). **Not shared** removes the split.

### Add an item
Adds another item card, using the same title as the last one.

### Title (on each item)
The magazine or event the item is for. Changing it clears the rate card choice and the issues.

### From the rate card
Pick a product from this year's, last year's or next year's rate card for that title. It fills in the description, **Rate card price** and **Price each**. If the title has nothing on the rate card, type the item yourself.

### What it is, as it should read on the confirmation
The wording printed on the confirmation, for example "Full page advert" or "Solus html email".

### Size code
The order register's shorthand (FP, DPS, 1/2). It counts the pages in the issue.

### Each time
How many of it in each issue or month, for example 4 weekly banners in a month.

### Price each (£) and % off this item
Shown when each item has its own price. The price is per insertion. The % comes off this item only. An amber "N% below rate card" appears when the price is under the rate card price.

### This line's share of the package (£)
Shown only with a package price shared by "I'll type each line's share".

### Rate card price (£)
Optional. Used to show how far below rate card the booking is, to share a package by value, and to print "usual rate" or "normally £X" on the confirmation.

### Free - added value
Tick for an item given free. It is a £0 item and prints as "Added value - normally £X each" if it has a rate card price. The card gets a dashed border.

### Extra wording
Optional text printed under the line on the confirmation.

### Runs in
The list of issues, months or events this item runs in. Each one becomes its own item on the order register. The bin beside a row (**Remove this one**) takes that issue off; an item always keeps at least one.
- The drop-down lists the title's issues from three months ago onwards, with their date and "book by" deadline. "deadline passed" shows when the advertising deadline has gone.
- The first date box is the exact day it runs, if not the issue's date (for example an email on 13 May).
- The second date box is when copy or artwork is due. Hover to see the issue's own copy deadline.
- The value of each one shows on the right.
- **Every open issue**: adds every issue still open for booking (not months).
- **Another**: adds a blank row.
- **To be allocated**: sold now, issue decided later (part of a package). You can also pick "To be allocated (issue not decided yet)" in the drop-down.
- The X removes a row (you must keep at least one).

### Decide the issues by
Appears when an item has rows still to be allocated. Set the date the issues should be chosen by. Those rows count in the booking total and print as "date to be confirmed", but go on the order register only once you choose their issues.

### After it's sold
A fold-out on each item showing who works on it once it's sold, for example "After it's sold: Production (suggested)". It opens by itself for sponsored items. Once accounts have checked the booking, each team gets an email with the item, its dates and the client's copy contact, plus a ready-written email asking the client for their copy or artwork.
- **Hand off to**: **Suggested: <team>**, **Editorial**, **Production**, **Editorial and production** or **Nobody**. The suggestion is editorial for sponsored content and social media, and production for adverts, banners and HTML emails. Sponsored content for Caribbean and Visit USA goes to production.
- **Editorial email(s)** and **Production email(s)**: the addresses from the Hand-offs settings show greyed out. Type over them to send elsewhere. "Nobody is set..." in amber means no address is set up, so type one.
- **Format or style** (editorial): for example "How to sell" or "Q&A". If the client hasn't decided, write TBC. Editorial are told once you fill it in.
- **Also appears**: press **Online, newsletter, social...** to add where else it runs (Online, Newsletter, Social media, Banner, HTML email, In print, At the event, Other), with a date and a note.

### Move up, Move down, Copy this item, Remove this item
The arrow, copy and bin buttons at the bottom of each item card. Copy puts a duplicate straight below. You can't remove the only item.

### Each item has its price / One package price
How the booking is priced.
- **Each item has its price**: every item uses its own price and %.
- **One package price**: enter **Package price (£)**, the **Name on the confirmation** (defaults to "Package for <client>"), and how to **Share it across the items**: **In proportion to their rate card value** (dearer items get a bigger share), **Evenly**, or **I'll type each line's share**. Each item still needs its own value so the issue it runs in gets its revenue.

### % off the whole booking
A discount on the whole booking, taken after item prices or the package price.

### Booked through an agency and Agency commission (%)
The agency is invoiced and keeps its commission. It comes off what's invoiced and off the salesperson's commissionable revenue.

### Document
**Order confirmation (invoice to follow)** or **Schedule of works (a campaign over several months)**.

### Publication heading
The heading printed on the confirmation. On a new booking it follows the titles on the items until you type your own.

### Confirmation address and Invoice to
The two address boxes on the confirmation. **Same as confirmation** copies the confirmation address into Invoice to.

### Client's order or PO number
Printed as "your ref" next to the order number, and used as the reference on the Xero invoice.

### Email the invoice to
If not the contact. It prints as "Please email the invoice to...".

### When to invoice
What you agreed with the client. Accounts get a reminder on the day, and can change it.
- **As soon as allowed**: straight away if it runs this quarter, otherwise at the start of the quarter it runs in. This is the default.
- **When it runs**: the day the issue comes out or the event happens.
- **After it has run**: for clients who pay once they've had the tear sheet or link (a few days after it runs).
- **On a date agreed with the client**: pick the date in **Invoice on**, which appears below.
- **The quarter after it runs**: no budget left this quarter.
- **The financial year after it runs**: no budget left this financial year.

### Invoice in
**Pounds (GBP)**, **Euros (EUR)** or **US dollars (USD)**. Prices here stay in pounds; accounts invoice in this currency.

### Invoice instructions for accounts (never printed)
For example "Only invoice once they've seen the printed copy; PO to follow".

### Insertions booked
Leave blank and it is filled in from the items (for example "April, June, September"). Type your own to override it.

### Special instructions, Copy and artwork, Production contact
Printed on the confirmation. On a new booking these start with the standard wording from Confirmation details.

### Client's copy and artwork contact and Their email
Who sends the copy, if not the contact above (for example their creative agency). Hand-off emails use it.

### Print the artwork specification
Ticked by default. Prints BMI's artwork specification on the confirmation.

### Notes for the team (never printed)
Internal notes, shown on the booking page.

### Confirm the booking
New bookings only. Saves it as confirmed: the client has said yes. It counts in sales figures and commission straight away.

### Pencil it in
New bookings only. Saves it as pencilled. Pencilled bookings hold the space but don't count in sales figures or commission until they're confirmed.

### Save changes
When changing a booking. Saves straight to the items. It keeps the booking's current status.

### Why it needs changing and Send to accounts
Shown instead of Save changes when Accounts have checked the booking and you are not in Accounts. Type the reason (for example "Client wants the half page in June instead") and press **Send to accounts**. Nothing changes until they approve it.

### Cancel
Goes back without saving.

## How it works
- Each row under "Runs in" becomes one item on the order register in that issue. Commission is earned item by item, when each one runs.
- Pricing order: item price times "Each time", less the item's % off (or the package price shared out); then the % off the whole booking; then the agency's commission. Pennies are put on the biggest item so the items always add up exactly to the total.
- With "I'll type each line's share", if the shares don't add up to the package price they are scaled to fit and a warning says so.
- Changing a booking: an item that's already invoiced and is taken off is marked cancelled, not deleted. You'll see a note saying so.
- Saving a new booking tells Accounts (a note on their bell, and the confirmation emailed to the Accounts addresses), if that setting is on.
- Confirmed bookings go to Accounts to check, if the accounts check is on. If a checked booking's client, contact, addresses, PO or agency change, it goes back to be checked again.
- Once Accounts have checked a booking, or any item is invoiced, it is locked. Only Accounts can change it; everyone else uses **Send to accounts**. If Accounts unlock it for you, it locks again and goes back to be checked when you save.
- Quarters for invoicing follow BMI's financial year, which starts on 1 July. Choosing a date a quarter before the first item runs gives a gentle warning on the booking page.
- **New business** for commission is not on this form. It is a tick box on each item's own panel (open an item from the booking's Schedule, under Commission). The salesperson credited on the item, or a manager, can tick it. Tick it if the client hasn't spent with BMI in the last 24 months; a manager checks the ticks each month.

## Common questions
**Q: How do I book the same advert in four issues?**
A: Add the item, then under **Runs in** pick the first issue and press **Another** for each extra issue. Or press **Every open issue** to add every issue still open.

**Q: How do I record a package price?**
A: In **Price**, press **One package price**, type the **Package price (£)**, and choose how to **Share it across the items**.

**Q: The client bought six insertions but hasn't chosen the issues. What do I do?**
A: Under **Runs in**, press **To be allocated** for each one and set **Decide the issues by**. Later, open the booking and press **Choose the issues**.

**Q: Should I confirm or pencil it in?**
A: Press **Confirm the booking** when the client has said yes. Press **Pencil it in** to hold the space while they decide. You can confirm it later from the booking page.

**Q: How do I give something free?**
A: Tick **Free - added value** on that item. Fill in **Rate card price** so the confirmation shows what it's normally worth.

**Q: How do I invoice in euros?**
A: Set **Invoice in** to **Euros (EUR)**. Keep prices in pounds; Accounts invoice in euros.

**Q: The client wants the invoice in the next quarter.**
A: Set **When to invoice** to **The quarter after it runs**.

**Q: How do I share the commission with a colleague?**
A: Press **Shared with another salesperson?**, choose each person and their %, and make it add up to 100%.

**Q: How do I make sure the editor gets the sponsored article?**
A: Open **After it's sold** on that item, set **Hand off to** to **Editorial**, check the editorial email, and fill in **Format or style** (or TBC).

**Q: How do I mark a booking as new business?**
A: Save the booking, open it, and in the Schedule click the item's name. On its panel, under Commission, tick **New business**.

## If something doesn't work
- **"Choose the client first"**: pick a company or type the client name.
- **"Choose the salesperson, so the right person earns the commission"**: pick someone in **Salesperson**, or House account.
- **"Say what each item is"**: every item needs a description or a size code.
- **"Choose the issue, month or event for every item, or mark it as to be allocated"**: a row under Runs in is still blank.
- **"Give every item a price, or tick it as free"**: an item has no **Price each**.
- **"Enter the package price"**: you chose One package price but left it blank.
- **"A package needs at least one item that isn't free."**
- **"The split between salespeople needs to add up to 100%."**
- **"Choose the date to invoice on, or pick another option for when to invoice."**: fill in **Invoice on**.
- **"The copy and artwork contact's email doesn't look right."**
- **"Say why the change is needed - accounts will see it"**: fill in **Why it needs changing**.
- **The issue drop-down says "Choose the title first"**: pick the item's Title. "Loading..." means its issues are still coming.
- **I can't find an older issue**: the list only goes back three months.
- **"Accounts has checked this booking, so changes go to them for approval."**: the booking is locked. Use the request version of the form.
- **"This booking is cancelled. Reopen it first to change it."**: use **Reopen** on the booking page.
- **"Only the salesperson on this booking or a manager can change it."**: you're not the salesperson, in the split, the creator, a manager or Accounts.
- **No Confirm or Pencil buttons**: those are only on a new booking. Change the status from the booking page.
