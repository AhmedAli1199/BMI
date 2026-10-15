# Sales Orders: things that looked confusing or possibly buggy

Found while writing the assistant's help guides (15 Oct), by reading the code. Not fixed yet - check each before acting.


## Bookings and the booking page
- Rebook for next year: no permission check; shows for everyone, even cancelled bookings.
- "Confirmation waits for the check" on + pencilled booking shows "Waiting for the accounts check" but pencilled never gets a check card.
- Reopen on a cancelled booking turns every item back to pencilled, incl. items kept booked because run/invoiced.
- "Only my bookings"/Salesperson filters ignore shared split reps.
- Search placeholder says "contact" but only matches contact name, not email.
- Single-item panel: client/value/salesperson look editable but saving is refused for booking items; admins can delete an item there (line may point at missing item).
- Online forms panel says entries "ready to become a booking" but they now create confirmed bookings.
- Cancel dialog: "Cancel the booking" vs "Keep the booking" near-identical.

## Proposals, rate card, costs and commission
- Rate card hint says publishers can edit own prices; backend only if setting on (off by default).
- Rate card price cell: clicking away cancels the edit (only Enter saves).
- Rate card Changes: Put back shows for people who can't edit.
- Proposal editor: Delete draft has no error handling.
- "make the booking" vs "make the order" wording inconsistent.
- Server doesn't stop editing a sent proposal (only the screen does).
- New booking from proposal: no check the person may see that proposal.
- How you write: several actions show no error on failure.
- Proposal requests report: picking one person hides other buttons; name link to queue isn't filtered.
- Commission plans: look-back box jumps back to 24 when cleared.
- Commission by calendar year vs FY elsewhere.
- Salespeople settle own "Needs a decision" new business (HANDOFF says manager).
- Proposals list only newest 200, no paging.

## Overview, editions, all items, renewals
- Edition Export .xlsx likely fails for editions with a pencilled item (no "pencilled" in export status lookup).
- All items Status filter / item panel don't offer "Pencilled".
- Weekly summary Run now toast shows internal job name.
- "Advert with no booking" lists salespeople with no login -> fails.
- Salespeople see costs add/edit/remove but server refuses unless profit share.
- FY mode: "All editions" card opens the calendar year the FY ends in.
- Dashboard team-activity links lack the 30-day date filter.
- Renewals hint: "filled in from their last booking" - only company+edition for company-linked clients.
- All items table total counts every status; footer counts live only.
- "Awaiting invoice" includes editions not out yet.
- Anyone can create/close/reopen an edition (no role check).

## Invoicing, Xero, hand-offs, review cards
- Accounts check off -> hand-off Send button never appears (page only shows once checked).
- Send on one item re-sends to every team on it incl. already-sent.
- Edited handed-off item isn't re-sent automatically; fingerprint stored but unused.
- Locked booking: only format box editable in hand-off settings.
- Booking page shows "Ready to invoice" on "No invoice needed" items and pencilled bookings.
- "Put back" says matched again within the hour but matching is off by default.
- Settings Xero card says "Nothing is ever written to Xero" (no longer true); Reconnect only on error.
- Remembered Xero contact can't be changed/cleared in app.
- Advert with no booking: salesperson without login -> unhelpful error.
- Uninvoiced Bookings + Order Register Client Matching cards: no filters, no booking links (breaks rule).
- Ready to invoice: snoozes count as rejected.
- Payment (Xero) filter lacks "Draft in Xero".
- Xero errors shown as "Xero said: <Xero's message>".
- Hand-off routes save error message mismatched.
