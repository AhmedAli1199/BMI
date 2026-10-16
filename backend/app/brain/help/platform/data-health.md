---
title: Data Health
screens: ["/data-health"]
summary: For administrators and data managers - how complete the contact and company records are (missing emails, phones, industries, unsubscribes) and how many clean-up suggestions are waiting in the Review Queue, with a link to fix each.
sources: ["frontend/src/app/(app)/data-health/page.tsx", "frontend/src/lib/automation-style.tsx", "backend/app/api/routes/dashboard.py", "backend/app/ui_sections.py", "backend/app/brain/access.py"]
---

## What this screen is for
**Data Health** (under BMI Brain in the menu) shows what's dragging down the quality of the contact database in one place: records missing key details, and clean-up suggestions from the automations that are still waiting for someone to decide. Each line has a **Fix** link that takes you to where you can sort it out. It's for administrators and data managers.

## What you see
- **Header** - how many contacts and companies the figures cover.
- **Three summary tiles**
  - **Open issues** - every problem on the page added together.
  - **Metrics clean** - how many of the lines have no problems at all, out of the total (for example 3/10).
  - **Biggest single issue right now** - the line with the most affected, and how many. "Nothing outstanding" and "All clear" when there's nothing.
- **Record completeness** - four lines:
  - **Contacts without an email address**
  - **Contacts without a phone number**
  - **Companies without an industry**
  - **Unsubscribed / hard-bounced contacts**
- **Automation hygiene backlog** - suggestions waiting in the Review Queue:
  - **Ambiguous out-of-office replies**
  - **Unconfirmed departures**
  - **Possible duplicate contacts**
  - **Uncertain bounces**
  - **Unmatched bounces**
  - **Returned copy / undeliverable mail**

Each line shows a short explanation, a bar, the number affected, what share of the total that is ("<percent>% of <total>"), and a badge:
- **Clean** (green) - none at all.
- **Watch** (amber) - some, but under 2% of the total.
- **Needs attention** (red) - 2% of the total or more.

## Buttons and controls
### Fix
Shown on any line with at least one problem.
- On the four **Record completeness** lines it opens the contact list (or, for missing industries, the company list), where you can search and filter to find the records and update them.
- On the **Automation hygiene backlog** lines it opens the Review Queue filtered to that kind of suggestion, so you can approve or reject each one.

### The database switcher (top of the page)
Choosing one database narrows every figure to it. Choose all titles to see everything.

## How it works
- The figures are worked out fresh each time the page opens.
- A contact counts as "without an email address" if it has no email at all, and "without a phone number" if it has no phone at all. A company counts as "without an industry" if the industry is blank.
- **Unsubscribed / hard-bounced contacts** counts contacts marked as unsubscribed. The bounce automation marks a contact this way once a bounce is confirmed, and they're then left out of outreach.
- The backlog lines count suggestions still waiting in the Review Queue. Approving or rejecting one there takes it off this page.
- The percentage on every backlog line is worked out against the total number of contacts, so a backlog line usually shows **Watch** unless it's very large.
- 2% is the bar for "under control" rather than perfect: with tens of thousands of records moved over from Act!, zero isn't realistic.
- Sales users can't open this page. An administrator can also hide it from Data Managers (or one person) under **Settings** > **Sections people see**. When it's hidden for someone, Ask the Brain won't answer questions about it for them either.

## Common questions
**Q: How do I clear the possible duplicate contacts?**
A: 1. On **Data Health**, find **Possible duplicate contacts**. 2. Press **Fix**. 3. In the Review Queue, check each suggested pair and approve or reject it. The count goes down as you go.

**Q: How do I find the contacts with no email address?**
A: Press **Fix** on **Contacts without an email address**. It opens the contact list. Open **Advanced search**, add a rule for the email field set to **is empty**, and you'll have just those contacts to update.

**Q: What's the difference between Watch and Needs attention?**
A: **Watch** means some records are affected but fewer than 2% of the total. **Needs attention** means 2% or more. **Clean** means none.

**Q: Why does "Open issues" seem so high?**
A: It adds up every line on the page, and one contact can count more than once (for example, missing both an email and a phone number).

**Q: Can I see the figures for just one magazine?**
A: Yes. Choose that database in the switcher at the top of the page and the figures update.

**Q: Where do the backlog suggestions come from?**
A: From BMI Brain's clean-up automations: they read bounces and out-of-office replies, spot people who've left, find likely duplicates and log returned post. Anything they're not sure about waits in the Review Queue for a person to decide.

## If something doesn't work
- **It says "Administrators & Data Managers only".** Your role can't open Data Health. Ask an administrator if you need the figures.
- **Data Health isn't in my menu.** You're a Sales user, or an administrator has hidden it for you under **Sections people see**.
- **There's no Fix link on a line.** That line has nothing to fix.
- **Fix opened the whole contact list, not just the missing ones.** That's how it works for now: use the search or advanced search to narrow it down.
- **A number didn't go down after I fixed something.** Reload the page - the figures are worked out each time it opens. Backlog lines only go down once the suggestion is approved or rejected in the Review Queue.
- **Ask the Brain says "You don't have permission to view that."** Data Health is hidden for you or your role can't open it.
