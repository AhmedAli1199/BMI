---
title: Draft invoices in Xero
screens: ["/sales/deals/[id]", "/sales/deals", "/automations/review", "/settings"]
summary: How Accounts make a draft sales invoice in Xero from a booking in one click, fix anything Xero needs first, and set the Xero codes each publication uses.
sources: ["frontend/src/components/deals/xero-invoice-button.tsx", "frontend/src/components/deals/xero-codes-button.tsx", "frontend/src/app/(app)/sales/deals/[id]/page.tsx", "frontend/src/app/(app)/sales/deals/page.tsx", "frontend/src/components/review-item-card.tsx", "frontend/src/components/xero-connection-card.tsx", "frontend/src/components/sales/invoice-match-panel.tsx", "backend/app/services/xero_invoices.py", "backend/app/api/routes/xero_invoicing.py", "backend/app/automations/invoice_due.py", "backend/app/sales/accounts.py"]
---

## What this screen is for
Accounts can make the invoice for a booking straight from the Brain instead of typing it into Xero. One click makes a **draft** sales invoice in Xero with the right customer, lines, prices, agency discount, codes and reference. Nothing is approved or sent to the client: Accounts open it in Xero, check it, and approve and send it from there as usual.

## What you see
- **On a booking page**, in the Schedule heading: **Create the invoice in Xero (N)**, where N is the number of items ready to invoice now.
- **On each item not yet due** (in the Invoice column): a smaller **Invoice it now** button, to invoice that one item early.
- **On a Ready to invoice card** in the Review Queue: **Create the invoice in Xero**, next to the card's other buttons.
- **On Sales Orders > Bookings**: a **Xero codes** button at the top.
- After an invoice is made, the item's Invoice column shows the number and **Draft in Xero** until Xero says it's approved. The booking's details show the **Xero contact** used.

Only Accounts see these buttons (or administrators while **Accounts are away** is on; or administrators and data managers if nobody has the Accounts permission yet). The booking must be confirmed.

## Buttons and controls
### Create the invoice in Xero (N)
Makes one draft invoice for every item on the booking that is due now. If everything is in order, the success dialog opens. If not, the problem dialog opens and nothing is made in Xero yet.

### Invoice it now
On an item that isn't due yet. Makes a draft invoice for just that item, whatever the booking's "when to invoice" says. Use it when the client asks for an invoice early.

### Create the invoice in Xero (Ready to invoice card)
Makes the draft invoice for exactly the items listed on the card. When it's made, the card closes by itself.

### Success dialog: "Draft invoice <number> is in Xero"
Shows the invoice as Xero has it: number, who it's to, date and due date, reference, and every line (Description, Qty, Price, Disc., Account, Tax, Amount), with Subtotal, VAT and Total.
- **Open it in Xero** opens the draft in a new tab, to change, approve and send it.
- **Done** closes the dialog and refreshes the page.
Xero dates the invoice today. If you send it on another day, change the date in Xero so it's the day it goes out.

### Problem dialog
Titled **A few things to sort before the invoice is made**, or **The invoice can't be made yet** when it can't be fixed here. It lists each problem in plain words, then the fields to fix it:
- **Who it goes to in Xero**: what the booking says to invoice to (and any agency), the possible Xero contacts to choose from, and a search box (**Search Xero contacts by name or email**, then **Search**; type at least two letters). Once one is chosen it says "Using <name>. It's remembered for this booking and client."
- **Lines**: for each item, the **Description**, **Amount** (in the invoice currency, "less N%" if there's agency commission), **Account**, **Item (optional)** and any tracking categories Xero has. Codes you pick are remembered for that publication.
- **Reference**, and the booking's **Invoice instructions** if there are any.

### Make the draft invoice
Tries again with your choices. It stays greyed out until a contact is chosen, every line has an account (or an item), and, for a non-pound invoice, every line has an amount.

### Cancel / Close
Closes the problem dialog. Nothing has been made in Xero.

### Xero codes
On the Bookings list, for Accounts. Opens **Xero codes for invoices**: the account, item and tracking each publication's invoice lines use. There's a row for **Every publication** and one for each publication. Leave a publication's account on **Same as every publication** to use the general one. **Reload the codes from Xero** fetches new accounts or items you've just added in Xero. **Save** keeps your choices; **Cancel** closes without saving. Up to two tracking categories are used.

### Reconnect / Connect Xero (Settings > Integrations)
Administrators only, on the Xero card. **Reconnect** appears when the connection has a problem. **Sync now** fetches recent invoice changes; **Re-read all invoices** reads every invoice again; **Disconnect** removes the link.

## How it works
- **What goes on the invoice**:
  - One line per item: "What it is - Publication and issue" (plus the item's own date if it has one), quantity 1, our price.
  - Any agency commission becomes Xero's discount on each line.
  - The account, item and tracking come from **Xero codes**, the publication's own row first, then **Every publication**.
  - VAT is left to Xero, which uses the contact and the account.
  - The date is today.
  - The reference is the client's PO number if there is one, otherwise the publication and month, e.g. "The Business Travel Magazine Nov 2026".
  - The currency is the booking's **Invoice in** currency. Prices are in pounds, so euro or dollar invoices ask you for each line's amount.
- **How the Xero contact is found**, in order:
  1. The contact already linked to this booking.
  2. The contact linked to the client's company (not for agency bookings, which are invoiced to the agency).
  3. The customer on the client's last matched Xero invoice.
  4. A Xero search by the first line of **Invoice to** (skipping words like "Accounts Payable"), then the agency, then the client name, then the CRM company name. An email address that matches the booking's invoice or contact email counts strongly.

  The first name with exactly one certain match wins. Otherwise you're told "We couldn't find the right Xero contact..." or "We found more than one Xero contact...", and you choose.
- **Your choices are remembered**: the contact is saved on the booking and on the client's company (not for agency bookings), and codes you pick are saved for that publication.
- **After it's made**:
  - The draft is stored like any synced Xero invoice and the items are linked to it. Our own pound figures are kept as the invoiced amount, with today's date.
  - The booking locks, because it's now invoiced.
  - The Ready to invoice card closes.
  - The item shows **Draft in Xero** until the hourly Xero sync sees it approved. It then shows Awaiting payment, Paid and so on.
- **Double clicks** don't make two invoices: Xero is told it's the same request.
- **Xero permission**: the Brain needs permission to create invoices, and to read contacts and settings. If the connection was made before this was added, an administrator must connect Xero again. If the card shows no **Reconnect** button because the connection otherwise works, press **Disconnect** and then **Connect Xero**. If Xero is connected through BMI's n8n workflow, the n8n Xero app needs the same permissions.

## Common questions
**Q: Does this send the invoice to the client?**
A: No. It only makes a draft in Xero. Open it with **Open it in Xero**, check it, then approve and send it from Xero.

**Q: How do I invoice just one item early?**
A: On the booking, find the item in the schedule and press **Invoice it now** in its Invoice column.

**Q: It says it couldn't find the Xero contact. What do I do?**
A: In the problem dialog, pick the right contact from the list, or type part of the name or email in **Search Xero contacts by name or email** and press **Search**. Then press **Make the draft invoice**. If the client isn't in Xero at all, add them in Xero first, then search again.

**Q: It says there's no Xero account code for a publication.**
A: Choose the **Account** for each line in the dialog; it's remembered for that publication. To set it once for all publications, use **Xero codes** on the Bookings list.

**Q: The booking is in euros. Why does it ask for amounts?**
A: Prices are kept in pounds. Type each line's amount in euros in the **Amount** box, then **Make the draft invoice**.

**Q: I made the invoice but need to change a line.**
A: Change it in Xero (use **Open it in Xero**). The draft is a normal Xero draft.

**Q: The wrong contact was remembered for a client.**
A: A remembered contact is used without asking, and there's no button in the Brain to change it yet. Correct the contact on the draft in Xero, and tell an administrator if it keeps happening.

**Q: Where do I see which Xero contact a booking uses?**
A: In the booking's details, under **Xero contact**.

## If something doesn't work
- **I can't see Create the invoice in Xero.** You need the Accounts permission (or be an administrator while Accounts are away). The booking must be confirmed, and an item must be ready to invoice. For other items, use **Invoice it now**. Items that are free, cancelled, already invoiced or still to be allocated can't be invoiced.
- **"There's nothing on this booking left to invoice: everything is invoiced, free, or not due yet."** Nothing is due. Use **Invoice it now** on a specific item instead.
- **The dialog only has Close.** The problem can't be fixed in the dialog: Xero isn't connected, or there's nothing to invoice. Sort that first.
- **"Xero isn't set up yet" / "Xero isn't connected yet."** An administrator connects Xero in Settings > Integrations.
- **"The Xero connection needs renewing."** or **"Xero didn't let BMI Brain do this..."** An administrator reconnects Xero (see above).
- **"Xero is busy" / "Xero didn't answer just now" / "Xero had a problem on its side."** Close the dialog, wait a minute and press the invoice button again.
- **"Xero said: ..."** Xero refused something, usually an account or tracking code. Change it in the dialog and try again.
- **"Xero didn't say whether the invoice was made."** Look in Xero before trying again, so you don't make two.
- **"Only a confirmed booking can be invoiced."** Confirm the booking first.
- **Xero codes shows "Couldn't load the codes from Xero."** Check Xero is connected in Settings > Integrations.
- **Make the draft invoice is greyed out.** Choose a contact, give every line an account or item, and fill in every amount for a non-pound invoice.
