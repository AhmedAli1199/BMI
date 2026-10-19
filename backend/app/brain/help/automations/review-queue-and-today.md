---
title: Review Queue and Today
screens: ["/automations/review", "/automations/today"]
summary: Where every suggestion the Brain makes waits for a person - filter, sort, act on one card or many, check past decisions, and see your own ranked list for today.
sources: ["frontend/src/app/(app)/automations/review/page.tsx", "frontend/src/app/(app)/automations/today/page.tsx", "frontend/src/components/review-item-card.tsx", "frontend/src/components/bulk-review-actions.tsx", "frontend/src/components/reopen-review-item-button.tsx", "frontend/src/components/draft-review-dialog.tsx", "backend/app/api/routes/review_queue.py", "backend/app/api/routes/automations.py", "backend/app/automations/registry.py", "backend/app/automations/morning_queue.py", "backend/app/sales/accounts.py"]
---

## What this screen is for
The **Review Queue** (sidebar > Review Queue) holds every suggestion the Brain's automations have made: a bounce to confirm, a duplicate to merge, a follow-up email to send, a booking to check, and so on. Nothing is changed, merged or sent until someone presses a button on the card. **Today** (sidebar > Today) is your own short list for the day: follow-ups, budget windows, promised call-backs, personal touchpoints and renewals, most urgent first.

## What you see
**Review Queue**
- The title shows the chosen automation's name, or "Review Queue", plus how many cards the list holds with your filters, search and Queue Insights group applied.
- Tabs: **Pending** (the working queue), **Approved**, **Rejected** and **Snoozed** (what was decided, read-only).
- A row of chips: **All**, then one chip per kind of card, each with its waiting count. Kinds with nothing waiting are greyed and sit at the end.
- The sort buttons on the right.
- When one kind is chosen, you may also see:
  - **Filter by:** drop-downs for that kind (for example Salesperson, Title, Bounce type, Mailbox, Database), with a count beside each option. Chosen filters show as removable chips. Every kind has filters. A card queued before its kind had filters shows under "Not set" until that automation next runs and fills it in.
  - **Queue Insights:** quick groups for duplicates (High confidence (≥90%), Medium confidence (70–89%), Low confidence (<70%)), bounces (Hard bounce, Soft bounce) and out-of-office replies (Has a named replacement, Absence only, no replacement named).
  - **Bulk action (<number>)** on the Pending tab.
- A search box: "Search by contact or company...".
- The cards, 50 at a time. When there are more, "Showing 1–50 of <number>" and **Previous** / **Next** move through the rest.

**Each pending card**
- The kind of card in capitals. Some cards also show "<number>% confidence": green at 75% or more, amber from 45%, red below. Then how long ago it arrived.
- A one-line summary, and **View contact record** or **View company record** if it's about one. On a follow-up card this opens the contact (or company) the calendar activity is for.
- The details. Blue values are links to every record the card mentions (the contact, their company, the booking, a suggested replacement and so on).
- **Every record this affects (<number>)**: every contact or company it would touch.
- **Researched candidate:** for a departure, the suggested successor.
- Fold-outs: **Original message** (the email or label it came from), **Drafted note** or **Draft email** (what the Brain wrote for you), and **Original email excerpt**.
- The action buttons. Every link on a card opens in a new tab, so you keep your place.
- When you act, the card turns green with the button's name and "Recorded on the CRM. Moving to the next item…", then disappears.

**Approved, Rejected and Snoozed rows** show what was pressed (with a tick for approved and a cross for rejected), by whom ("· no reviewer recorded" if nobody was signed in), when, and any note. They also show **Open contact record** / **Open company record**, the person's name, company, email and phone, the details and the **Original message**. Every link opens in a new tab.

**Today**
- The title "Today", with a count. On the Everyone view the line starts "Everyone's list."
- Administrators and data managers get **My list** and **Everyone** switches. Everyone groups the cards by salesperson, with Unassigned last.
- The same cards as in the Review Queue, best first.

## Buttons and controls
### Pending / Approved / Rejected / Snoozed
These tabs switch between the cards still waiting and the ones already decided. Every button counts as an approval, a rejection or a snooze. "Dismiss" and "Skip" style buttons count as rejected. "Remind me on…", "Not yet - next week" and other "ask me again later" buttons count as snoozed: the card closes for now and a new one comes back on the day, and the automation figures don't count it as rejected.

### All and the kind chips
Click a chip to show only that kind of card. **All** shows every kind. Changing kind clears the filters, the Queue Insights group and any date sort.

### Sort buttons
- Kinds with a date (for example a booking date or a call date): **Latest <date> first** (the starting order), **Oldest <date> first** and **Recently added**.
- Other kinds and **All**: **Most recent**, **Confidence: low → high** and **Confidence: high → low**. Cards with no confidence go last.

### Filter by: <filter name>
Open a drop-down and tick one or more options. Ticked options are read out as "(selected)" by screen readers. The count beside each option says how many cards it would leave, counted with your other filters applied. Click a chip ("Salesperson: Sally ×", read out as "remove this filter") to remove it, or **Clear all filters**.

### Queue Insights chips
Click one to show only that group, for example only Hard bounce. Click it again, or **Clear**, to remove it.

### Search by contact or company...
Type a name and press Enter. It searches the card headlines (and email subjects). **Clear** removes the search.

### Bulk action (<number>) > <action> all (<number>)
Only on the Pending tab, once one kind is chosen. It applies one button to every waiting card of that kind that matches your **Filter by:** choices, search and **Queue Insights** group - exactly the cards the list is counting. Only buttons that need nothing typed or picked per card are offered. "Assign different contact", "Merge records", "Create contact" and "Record invoice" don't appear, for example.
- A window says how many cards it will change. A button that needs a note asks for one **Note (added to every card)** here. Press **Confirm** to go ahead, or **Cancel**.
- Big selections are done 500 at a time, with "Done <number> of <number>…" while it works. Keep the window open until it finishes.
- Afterwards a message says how many worked and how many couldn't be done, and why.

### Previous / Next
Move to the next or previous 50 cards. Changing a filter, the sort, the tab or the kind goes back to the first page. If the cards on a page have all been dealt with since you opened it, "Nothing left on this page." shows with **Go to the first page**.

### Action buttons on a card
Each kind has its own buttons. The main one comes first. Some cards lead with a different button: a soft bounce leads with **Keep - it was temporary**, because a temporary failure is no reason to unsubscribe anyone. See the "How each automation works" guide and the Sales Orders "Review cards" guide. In general:
- A button that needs nothing more works straight away.
- A button that needs more opens a small form under the card. The form may ask for a **Note** ("Why, or any context worth keeping on the record…"), a **Contact** search, **Which one do you want to keep?** (for a merge), or typed fields. Press **Confirm <action>**, or **Cancel**.
- A risky button (for example **Confirm successor** or **Dismiss (contact remains)**) shows a warning with **Cancel** and **Confirm**.

### Review the draft (for drafted emails and notes)
On follow-ups, commercial signals, personal touchpoints, renewals, save-the-sale and proposal requests, the main button opens **Review the draft**:
- **Send to** (only where the email can be sent): the address, pre-filled where the Brain knows one.
- The draft itself, which you can edit.
- **Ask for a revision (optional)**, for example "make it shorter", then **Regenerate** to have it rewritten. You can do this as often as you like.
- **Cancel**, then the card's log-only button (for example **Log to CRM only** or **I'll reply myself**), then the main button.
For follow-ups, commercial signals and touchpoints, the main button **Approve & log to CRM** saves the text as a note on the record. It does not send anything. Copy it into your own email or call. For renewals, save-the-sale and proposal requests, the main button sends the email from your own Outlook.

### View contact record / View company record / record links
These open the record in a new tab.

### Reopen for review
On **Rejected** rows whose button changed nothing (for example **Keep as separate contacts**, **Dismiss** or **Not a lead, ignore**). It puts the card back in Pending for another look. There's no reopen for approved or snoozed cards, or for rejected buttons that did something (for example **No invoice needed** adds a note and **Needs a fix** tells the salesperson), because pressing the button again would do it twice. Make any further change on the record itself.

### View every automation →
On an empty filtered list, it goes back to every kind.

### My list / Everyone
On Today, for administrators and data managers. **My list** shows cards that belong to you. **Everyone** shows the whole team, grouped by person.

## How it works
- **Who sees which cards.** Administrators and data managers see every kind. Salespeople see only sales cards: proposal requests, follow-ups, commercial signals, personal touchpoints, call notes, new leads, renewals, save-the-sale, items to allocate, invoice-to-booking and online bookings. Of those, renewals, items to allocate and proposal requests show only to the salesperson they belong to. Everyone only sees cards about contacts, companies and databases they have access to.
- **Accounts cards** (Booking check, Ready to invoice, Booking change, Issue gone to press) go only to people with the Accounts permission once anyone has it. Until then, administrators and data managers get them. Administrators get them as well while **Accounts are away** is switched on.
- **Two people at once**: if someone has already handled a card, you're told "someone else may have just handled this" and nothing is done twice.
- **Today** gathers waiting cards of four kinds: Commercial Signals, Overdue Follow-ups, Personal Touchpoint Reminders and Renewal Outreach. Each card belongs to a person, checked in this order:
  1. For a renewal, the salesperson who sold it last time (once their login is linked in Settings > Users).
  2. Otherwise, whoever the automation says.
  3. Otherwise, the contact's owner.
  4. Otherwise, the owner of the contact's company.
  Cards nobody owns are "Unassigned". Salespeople only ever see their own list, so Unassigned cards don't show to them.
- **Order on Today**: each card gets a score. 85% of it is urgency: due today or overdue scores highest, fading to nothing two weeks out, and undated cards sit in the middle. 15% is the value of an opportunity linked to the contact, counted up to £10,000. Both weights and the cap are in Automations > Settings > Morning Queue Prioritization.

## Common questions
**Q: How do I deal with just one kind of card?**
A: Click its chip, for example **Overdue Follow-ups**. Use **Filter by:** and the sort buttons to narrow it down.

**Q: How do I dismiss 200 soft bounces at once?**
A:
1. Click the **Ambiguous Delivery Bounces** chip.
2. Click **Soft bounce** under **Queue Insights** to check them.
3. Press **Bulk action (<number>)** > **Keep - it was temporary all (<number>)**, check the number in the window and press **Confirm**.
Only the soft bounces are touched: bulk actions follow the Queue Insights chip, **Filter by:** and search.

**Q: How do I send a renewal email?**
A: Press **Send from my Outlook** on the card. Check **Send to**, edit the draft, then press the send button. It goes from your mailbox and is logged on the company.

**Q: I dismissed something by mistake. Can I undo it?**
A: Open the **Rejected** tab, find the row and press **Reopen for review**. If the row has no such button, what you pressed has already changed something - change it on the record itself.

**Q: Who approved this merge?**
A: Open the **Approved** tab and choose the kind. Each row says who pressed which button and when.

**Q: Why is Today empty when the Review Queue has cards?**
A: Today only shows follow-ups, commercial signals, touchpoints and renewals that belong to you. Other kinds stay in the Review Queue.

**Q: Can a manager see everyone's list?**
A: Yes. Administrators and data managers press **Everyone** on Today.

**Q: The Brain's draft is too long. How do I change it?**
A: In **Review the draft**, type "make it shorter" in **Ask for a revision (optional)** and press **Regenerate**. You can also edit the text yourself.

## If something doesn't work
- **No Bulk action button**: choose one kind chip first, and be on the Pending tab. If the kind's buttons all need something typed or picked per card, there's nothing to apply in bulk.
- **A bulk action touched more cards than expected**: it applies to every waiting card of that kind matching your **Filter by:** choices, search and **Queue Insights** chip - the number in the window - not only the 50 on the page.
- **"… more cards are still waiting. Run it again to do the rest."**: a very large selection stopped part-way. Press the bulk action again to carry on.
- **"Already resolved … someone else may have just handled this."**: a colleague got there first. Refresh the page.
- **"Confirm …" is greyed out**: fill in the required fields. That might be the **Note**, a **Contact**, **Which one do you want to keep?** or a starred field.
- **"Connect your Outlook first"** when sending: connect your mailbox in Settings > Email, or use the log-only button and send it yourself.
- **"The draft is empty"** / **"Enter the email address to send this to."**: write something, or fill in **Send to**.
- **I can't see a kind my colleague sees**: kinds depend on your role and the Accounts permission (see How it works).
- **Only 50 cards show**: use **Next** at the bottom, or filters and search, to reach the rest.
- **"This card can't be reopened, because what was decided on it has already been carried out."**: the button pressed on it has already changed something (or the card was closed automatically). Make any further change on the record itself.
