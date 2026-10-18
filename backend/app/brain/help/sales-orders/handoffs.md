---
title: Hand-offs to editorial and production
screens: ["/sales/deals/[id]", "/sales/deals/new", "/sales/deals/[id]/edit", "/sales/deals"]
summary: How each sold item is passed by email to editorial or production once the booking is confirmed and checked, how to choose the team and addresses, and how to see or resend what went.
sources: ["frontend/src/components/deals/line-handoff.tsx", "frontend/src/components/deals/deal-handoffs.tsx", "frontend/src/components/deals/handoff-routes-button.tsx", "frontend/src/components/deals/deal-settings.tsx", "frontend/src/lib/handoffs.ts", "frontend/src/app/(app)/sales/deals/page.tsx", "backend/app/sales/handoffs.py", "backend/app/api/routes/deals.py", "backend/app/automations/order_checks.py"]
---

## What this screen is for
Once a booking is confirmed and Accounts have checked it, each item is passed to the team that makes it happen, so nothing gets lost in chats. Sponsored content and social media go to the magazine's editor. Adverts, banners and HTML emails go to production. Each team gets one email per booking with everything they need, including a ready-written email asking the client for their copy or artwork.

## What you see
- **On the booking form**, under each item, a fold-out line **After it's sold: <team>**, with "(suggested)" if you haven't chosen. It opens by itself for items that look sponsored, or where you've already chosen a team or added activities.
- **On the booking page**, a panel **Hand-offs to editorial and production**. It lists each item that goes to a team, with its format and where else it appears. For each team it shows who it goes to and where it's up to:
  - **Sent** (green, with the date)
  - **Didn't go** (red, with the reason)
  - **No address yet** (amber)
  - **Waiting for the format** (grey)
  - **Goes after the accounts check** (grey)
  - **Ready to send** (amber)

  The panel is hidden for cancelled bookings and when no item goes to anyone.
- **On Sales Orders > Bookings**, administrators see a **Hand-offs** button at the top for the routing table.

## Buttons and controls
### After it's sold (booking form, per item)
Click to open the item's hand-off settings.

### Hand off to
Choose **Suggested: <team>** (the Brain's suggestion, the default), **Editorial**, **Production**, **Editorial and production** or **Nobody**. **Nobody** means no email goes for this item.

### Editorial email(s) / Production email(s)
Who gets the email. Leave them blank to use the routing table, which shows as the grey suggestion in the box. Type addresses to override it for this item, separated by commas. If neither you nor the routing table has an address, you see "Nobody is set for this magazine yet - type the address." (or "Nobody is set yet - type the address." for production).

### Format or style
For editorial items: the sponsored format the client chose, e.g. "How to sell" or "Q&A". If the client hasn't decided, write **TBC**. Editorial are told once you fill it in.

### Also appears
Where else the item runs: choose **Online**, **Newsletter**, **Social media**, **Banner**, **HTML email**, **In print**, **At the event** or **Other**, add a date and a note (e.g. "Selling Travel Weekly"). Add a row with **+ Online, newsletter, social…**, remove one with the cross. These go in the hand-off email with their dates.

### Save and tell editorial (booking page)
Appears under an item that's **Waiting for the format**. Type the format in the box and press it. Editorial get the email straight away. This works even when the booking is locked, because it doesn't change the invoice. The salesperson on the booking, whoever made it, Accounts or a manager can do it.

### Send / Send again (booking page)
Next to each team under an item, once hand-offs can go: the booking is confirmed and Accounts have checked it (or, if the accounts check is switched off, as soon as it's confirmed). **Send** sends that item to that team now (for example after an address was added or an email didn't go). **Send again** shows once it has gone to that team, and re-sends it to that team only. Other items, and other teams on the same item, aren't sent anything. The salesperson on the booking, whoever made it, Accounts or a manager can press it. The message afterwards says how many teams it went to, or "Nothing to send: no team or address for these items."

### Hand-offs (Bookings list)
Administrators only. Opens **Who gets the hand-offs**: a row for **Every magazine** (used when a magazine has no row of its own) and one for each magazine, each with an **Editorial** and a **Production** address box. Separate several addresses with commas. **Save** keeps them; **Cancel** closes. Everyone else can't change these addresses.

## How it works
- **Who the Brain suggests**, from the item's description, details, size and rate card product:
  - Sponsored editorial, sponsored content or social media words (sponsor, advertorial, feature, spotlight, interview, Q&A, profile, article, content, news story and similar) go to **editorial**.
  - Everything else (display adverts, banners, HTML or solus emails, covers, inserts) goes to **production**.
  - Sponsored content for **Caribbean** or **Visit USA** titles goes to **production**, because it's built from fillable forms.
  - A sponsored package that also has a banner, MPU, HTML or solus email goes to **both**.

  The salesperson can always change it with **Hand off to**.
- **Which address is used**, in order:
  1. The address typed on the item.
  2. The magazine's own row in the routing table.
  3. The **Every magazine** row.
  4. For production only, the "Production - always copied on confirmations" addresses in **Confirmation details**.

  The routing table is blank until an administrator fills it in.
- **When the emails go**:
  - When Accounts press **Looks right** on the booking check.
  - If the accounts check is switched off, as soon as the booking is confirmed and saved.
  - Nothing goes for pencilled or cancelled bookings, or before the check.
- **Waiting for the format**: an editorial item that looks sponsored, with no format or "TBC" (also TBD, "to be decided", "not decided" or "?"), waits. Production's half of the same item doesn't wait.
- **One email per team per booking**, sent from the automation mailbox. It has:
  - the client, the client's copy and artwork contact (or the main contact), and the salesperson with their email;
  - each item with its format, details, issue, run date and copy due date, plus its other activities and dates;
  - the copy and artwork notes and a link to the booking;
  - a ready-written email for the team to copy and send to the client. For editorial it asks for their brief, copy, images and logo by the copy date. For production it asks for their artwork.
- **Each item goes once.** Later saves send only new items, or items that have just become ready (an address or format added).
- **Changes are passed on once.** If an item that has already gone changes (its description or details, issue, run or copy due date, format, or where else it appears), the team gets one more email, titled "Change to a booking for ...", with the changed items marked. A new address on its own doesn't count as a change; use **Send** or **Send again** for that.
- **Sending never blocks the booking.** If the email fails, the item shows **Didn't go** with the reason, and you can press **Send**.

## Common questions
**Q: How do I make sure the editor gets my sponsored article?**
A: On the booking form, open **After it's sold** under the item, check **Hand off to** says Editorial, and fill in **Editorial email(s)** if no suggestion shows. Add the **Format or style**, or write TBC. Save. It goes once Accounts have checked the booking.

**Q: The client has just picked the format. How do I tell editorial?**
A: On the booking page, in **Hand-offs to editorial and production**, type the format in the box under the item and press **Save and tell editorial**.

**Q: Production never got the email. Can I send it again?**
A: Yes. On the booking page, press **Send** (or **Send again**) next to production under the item. Only production get it. If it shows **No address yet**, add an address on the booking first.

**Q: How do I set up who gets each magazine's hand-offs?**
A: An administrator goes to Sales Orders > Bookings, presses **Hand-offs**, fills in the editorial and production addresses for each magazine (or **Every magazine**) and presses **Save**.

**Q: An item doesn't need to go to anyone.**
A: Set **Hand off to** to **Nobody**.

**Q: Why does it say "Goes after the accounts check"?**
A: Hand-offs only go once the booking is confirmed and Accounts have passed the check, so nobody starts work on a booking that might change.

**Q: The item runs online and in the newsletter too. Where do I put that?**
A: Under **Also appears**, press **+ Online, newsletter, social…**, choose where, add the date and save.

## If something doesn't work
- **"Hand-offs go once the booking is confirmed and accounts have checked it."** Confirm the booking and wait for the accounts check.
- **No Send button.** It shows only once the booking is confirmed and checked by Accounts (or just confirmed, if the accounts check is switched off), and only for teams that have an address and aren't waiting for the format.
- **"The automation mailbox isn't set up yet, so the email couldn't go."** An administrator needs to set up the automation mailbox. Then press **Send**.
- **"The email didn't go. Try Send again in a minute."** A one-off sending problem. Press **Send** again shortly.
- **"Only the salesperson on this booking, accounts or a manager can send this."** (or "...can change this.") Ask the salesperson or Accounts.
- **"That item isn't on this booking any more."** The item was removed. Refresh the page.
- **I can't open the Hand-offs routing table.** Only administrators can see and change it.
- **"... doesn't look like an email address."** An address in the routing table is mistyped. Fix it and save.
- **I can't change the team or addresses on a locked booking.** The booking form is locked once Accounts have checked it. Only the format box works there. Ask Accounts to unlock it, or use **Request a change**.
