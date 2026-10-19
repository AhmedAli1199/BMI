---
title: Data Health
screens: ["/data-health"]
summary: For administrators and data managers - how complete the contact and company records are (missing emails, phones, industries, unsubscribes and bounces) and how many clean-up suggestions are waiting in the Review Queue, with a link to fix each.
sources: ["frontend/src/app/(app)/data-health/page.tsx", "frontend/src/lib/automation-style.tsx", "backend/app/api/routes/dashboard.py", "backend/app/api/routes/companies.py", "frontend/src/app/(app)/companies/page.tsx", "backend/app/ui_sections.py", "backend/app/brain/access.py"]
---

## What this screen is for
**Data Health** (under The Brain in the menu) shows what's dragging down the quality of the contact database in one place: records missing key details, and clean-up suggestions from the automations that are still waiting for someone to decide. Each line has a **Fix** link that takes you to where you can sort it out. It's for administrators and data managers.

## What you see
- **Header** - how many contacts and companies the figures cover.
- **Three summary tiles**
  - **Open issues** - every problem on the page added together (missing details plus items waiting for review).
  - **Checks clear** - how many of the lines have no problems at all, out of the total (for example 3/10).
  - **Biggest single issue right now** - the line with the most affected, and how many. "Nothing outstanding" and "All clear" when there's nothing.
- **Record completeness** - four lines:
  - **Contacts without an email address** - measured against all contacts.
  - **Contacts without a phone number** - measured against all contacts.
  - **Companies without an industry** - measured against all companies.
  - **Unsubscribed or bounced contacts** - measured against contacts who have an email address.
- **Waiting for review** - suggestions waiting in the Review Queue:
  - **Ambiguous out-of-office replies**
  - **Unconfirmed departures**
  - **Possible duplicate contacts**
  - **Uncertain bounces**
  - **Unmatched bounces**
  - **Returned copy / undeliverable mail**

Each **Record completeness** line shows a short explanation, a bar, the number affected, what share that is of the records it's measured against ("<percent>% of <total> contacts with an email address", for example), and a badge:
- **Clean** (green) - none at all.
- **Watch** (amber) - some, but under 2% of the records it's measured against.
- **Needs attention** (red) - 2% or more.

Each **Waiting for review** line shows how many are waiting ("waiting for review") - a count, not a percentage - and the badge **Clean** when there are none or **To review** when there are some.

## Buttons and controls
### Fix
Shown on any line with at least one problem. It opens the list already filtered to the records with that problem, so you can work through them:
- **Contacts without an email address** - the contact list with an advanced search for "Email (any) is empty".
- **Contacts without a phone number** - the contact list with an advanced search for "Phone (any) is empty".
- **Companies without an industry** - the company list showing only companies without an industry (press **Show all companies** to go back to the full list).
- **Unsubscribed or bounced contacts** - the contact list with an advanced search for contacts marked Unsubscribed or Email bounced.
- On the **Waiting for review** lines it opens the Review Queue filtered to that kind of suggestion, so you can approve or reject each one.

### The database switcher (top of the page)
Choosing one database narrows every figure to it. Choose all titles to see everything. The lists that **Fix** opens follow the same choice.

## How it works
- The figures are worked out fresh each time the page opens.
- A contact counts as "without an email address" if it has no email at all, and "without a phone number" if it has no phone at all. A company counts as "without an industry" if the industry is blank.
- **Unsubscribed or bounced contacts** counts contacts marked as unsubscribed or whose email has bounced. A contact with both is counted once. They're left out of mailings.
- The **Waiting for review** lines count suggestions still waiting in the Review Queue. Approving or rejecting one there takes it off this page.
- 2% is the bar for "under control" rather than perfect: with tens of thousands of records moved over from Act!, zero isn't realistic.
- Sales users can't open this page. An administrator can also hide it from Data Managers (or one person) under **Settings** > **Sections people see**. When it's hidden for someone, Ask the Brain won't answer questions about it for them either.

## Common questions
**Q: How do I clear the possible duplicate contacts?**
A: 1. On **Data Health**, find **Possible duplicate contacts**. 2. Press **Fix**. 3. In the Review Queue, check each suggested pair and approve or reject it. The count goes down as you go.

**Q: How do I find the contacts with no email address?**
A: Press **Fix** on **Contacts without an email address**. It opens the contact list showing just those contacts, ready to update.

**Q: What's the difference between Watch and Needs attention?**
A: **Watch** means some records are affected but fewer than 2% of the records that line is measured against. **Needs attention** means 2% or more. **Clean** means none.

**Q: Why is the bounce line measured against contacts with an email address?**
A: Only contacts with an email address can unsubscribe or bounce, so that's the fairest comparison.

**Q: Why does "Open issues" seem so high?**
A: It adds up every line on the page, and one contact can count more than once (for example, missing both an email and a phone number).

**Q: Can I see the figures for just one magazine?**
A: Yes. Choose that database in the switcher at the top of the page and the figures update.

**Q: Where do the review suggestions come from?**
A: From the Brain's clean-up automations: they read bounces and out-of-office replies, spot people who've left, find likely duplicates and log returned post. Anything they're not sure about waits in the Review Queue for a person to decide.

## If something doesn't work
- **It says "Administrators & Data Managers only".** Your role can't open Data Health. Ask an administrator if you need the figures.
- **Data Health isn't in my menu.** You're a Sales user, or an administrator has hidden it for you under **Sections people see**.
- **There's no Fix link on a line.** That line has nothing to fix.
- **A number didn't go down after I fixed something.** Reload the page - the figures are worked out each time it opens. Review lines only go down once the suggestion is approved or rejected in the Review Queue.
- **Ask the Brain says "You don't have permission to view that."** Data Health is hidden for you or your role can't open it.
