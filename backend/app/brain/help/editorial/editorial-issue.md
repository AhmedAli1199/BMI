---
title: Editorial issue page
screens: ["/editorial/issues/[id]"]
summary: One issue, special, event or awards night: its key dates and deadlines, planned features, details, notes, bookings so far, and who to pitch it to.
sources: ["frontend/src/app/(app)/editorial/issues/[id]/page.tsx", "frontend/src/components/editorial/issue-page.tsx", "frontend/src/components/editorial/who-to-pitch.tsx", "frontend/src/components/editorial/editorial-ui.tsx", "frontend/src/components/mail-merge/email-from-template.tsx", "frontend/src/lib/editorial-actions.ts", "backend/app/api/routes/editorial.py", "backend/app/sales/editorial.py", "backend/app/services/mail_merge.py", "backend/app/automations/editorial_deadlines.py"]
---

## What this screen is for
This page holds everything the editorial plan knows about one issue, guide, event or awards night: its dates and deadlines, the features planned for it, its theme and format, notes, how bookings are going, and a ready-made list of companies to pitch. The issue is the same record as the edition in the order register, so the bookings and the plan always match. Proposals and emails that mention this issue take their dates and features from here.

## What you see
- **Breadcrumb:** **Editorial plan** > <brand> > <issue>. Click either to go back to the plan.
- **Title:** "<brand>: <issue>" (a numbered issue shows as "Issue 105"), and a line with the part of the brand, the kind (Issue, Guide / special, Event, Awards), the months it covers and its format.
- **Buttons along the right:** the previous and next issue, **Bookings in the order register** and **Pitch this issue**.
- **"Please check these dates."** - an amber banner when some dates were worked out from the usual rules, estimated from the month, or copied from last year.
- **Key dates:** each date with its countdown. For issues and guides: **Advertising deadline** (last day to book an advert), **Editorial deadline** (copy from the editorial team), **Copy & artwork deadline** (advertisers' artwork due) and **Publication date**. For events it's **Event day**, for awards **Ceremony**. Any other key dates (entries close, voting opens, press day...) are listed too, in date order. The countdown turns red with two days or fewer to go, amber within a week, and says "Done" once the date has passed. Every key date is listed, dated or not; "No date yet" means it hasn't got one (an undated event still shows its **Event day**). Hover the info icon by the heading to see the brand's usual deadline rules.
- **Features:** the numbered list of what the issue will cover, with a status (**Planned**, **Confirmed** in green, **Dropped** in red and struck through) and an **Open to sponsors** badge where a client can sponsor it. The heading line counts planned, confirmed and open-to-sponsors features.
- **Who should we pitch?** - suggestions from the order register, in three tabs (see below).
- **Regular sections in every issue (<number>)** - a fold-out list of the brand's standing sections, if any are set, with a link to the brand's settings.
- **Right-hand column:**
  - **Details:** **Theme**, **Handed out at** (or **Venue** for events and awards), **Months it covers** and **Format**.
  - **Bookings so far:** the value of live bookings before VAT and how many, plus "Last year's equivalent (<name>)" with its final total and number of bookings.
  - **Notes:** free text, shared with the edition in the order register.
  - **Delete from the plan** - only when it can be deleted.

## Buttons and controls
### Previous / next issue (arrow buttons with the issue name)
Labelled like the issue's title, for example "Issue 104". Step to the issue before or after this one in the same part of the brand, by date (across years). Only shown when this issue has a date and there is one either side.

### Bookings in the order register
Opens this issue's edition page in the order register, with every booking, costs and invoicing.

### Pitch this issue
Starts a new proposal with this issue already chosen.

### The dates are right
In the amber banner, for people who can change this brand. Removes the "please check" warning once you've confirmed the dates. Changing any date yourself also removes it.

### Use the usual rules
In Key dates. Works out the advertising, editorial and copy deadlines again from the publication date and the brand's usual rules, replacing what's there, and refreshes any extra rule-based key dates (found by the rule, so a renamed rule updates its date rather than adding a second one). Key dates you added yourself stay. It also removes the "please check" warning. Only shown for issues and guides that have a publication date, when the brand has rules set, to people who can change the brand.

### Change dates
Opens the date fields for editing: the three deadlines and the publication date (issues and guides), or just the **Event day** / **Ceremony** for events and awards. Under **Other key dates**:
- **Add a key date** adds a line - type what it is (for example "Entries close") and pick the date. The bin beside a line (**Remove this date**) takes it off.
- The cross removes a line.

Click **Save dates** to keep the changes, or **Cancel**. Lines with no name or no date are left out. Changing the publication date moves the deadlines that came from the usual rules with it, worked out again from the new date. Deadlines you typed yourself stay as they are; use **Use the usual rules** if you want those worked out again too. Moving the date into another year moves the issue to that year's plan.

### Features: Add
Type a feature in the box and press Enter or click **Add**. You can paste a whole list - one per line, or separated by semicolons - and each becomes its own feature. Shift+Enter starts a new line without adding. New features start as Planned.

### Features: click a feature's name
For people who can change the brand, opens the feature to edit:
- Its title and a description ("A line or two on what it covers (optional)").
- **Status**: **Planned**, **Confirmed** or **Dropped**.
- **Open to sponsors** - tick if a client can sponsor it or write sponsored content for it. Proposals mention these.
- **Save**, **Cancel**, or **Delete** (asks you to confirm).

### Move up / move down (arrows)
Appear when you hover over a feature (for editors). Change the order features are listed in - proposals and emails use this order.

### Change details (pencil in Details)
Edit the **Name**, **Theme**, **Handed out at** / **Venue**, **Months it covers** and **Format**. Click **Save** or **Cancel**.

### Notes
Type in the box and click away - the notes save on their own and you'll see "Notes saved". Read only if you can't change this brand.

### Who should we pitch? tabs
- **Haven't rebooked (<number>)** - companies that booked last year's equivalent issue but nothing in this one yet.
- **Booked the last issue (<number>)** - companies in the issue before this one who haven't booked this one.
- **Fit a feature (<number>)** - past advertisers in this title (last three years) whose name, industry, category or description shares words with a planned feature. A starting point - check before you call.

Each line shows the company, why it's suggested, what they last booked (size, value, date) and the salesperson. Click a company name to open it in a new tab, so you keep your place. Names marked "(not linked to a CRM company yet)" can't be opened.

### Email
On a suggested company, while the issue is still open for adverts. Opens **Email from a template**: choose the **Template**, **Who to** (the company's people), **Which issue or event** (this one is chosen) and **The feature you're pitching** (filled in for feature matches). The email is filled with the brand's figures and this issue's dates and features. Change anything, then **Send from Outlook** (needs Outlook connected in Settings), **Copy**, or **Close**.

### Draft a proposal
On a suggested company, while the issue is still open. Opens a new proposal for that company and this issue in a new tab.

### Regular sections in every issue
Click to fold the list open or closed. The **<brand>'s settings** link takes you to where they're changed.

### Last year's equivalent link
In Bookings so far. Opens last year's matching issue.

### Delete from the plan
Asks you to confirm, then removes the issue and its features and returns you to the plan. Only shown to editors, and only for issues with no bookings that weren't brought in from an order register workbook.

## How it works
- **Who can change it:** admins and data managers can change every brand; each brand's publishers can change their own brand. Everyone else sees the page read only (no edit buttons, notes greyed out).
- **Open for adverts:** an issue is open until its advertising deadline has passed, or if it has none, its publication date. Once closed, "Advertising has closed for this issue." shows in Who should we pitch? and the **Email** and **Draft a proposal** buttons disappear.
- **Who should we pitch?** leaves off anyone who has already booked this issue (the count is in the info icon). A company only appears in one tab - the first that applies. Up to 50 are shown in each of the first two tabs and 25 feature matches. Dropped features aren't used for matching, and common words like "travel", "guide" or "news" are ignored.
- **Last year's equivalent** is the issue in the same part of the brand, a year earlier, whose date is closest to a year before this one.
- **Bookings so far** counts live bookings in the order register, before VAT.
- **Dates and "please check":** setting any date by hand clears the warning. **Use the usual rules** and **The dates are right** clear it too.
- **What uses this page:** proposals and request replies quote the publication date, advertising deadline, theme, where it's handed out and up to 12 features (sponsorable ones highlighted). Email templates fill issue fields like the issue name, issue date, advertising and copy deadlines, theme and features from it.
- **Reminders:** if advertising deadline reminders are turned on, publishers and recent sellers of the title get a notification before the advertising deadline that links here.
- Changes to the name, dates, theme, where it's handed out, months and format are recorded in the change history.

## Common questions
**Q: How do I add a list of features from the features list?**
A: Copy the list, paste it into the box under **Features** (one per line) and press Enter. Each line becomes a feature.

**Q: How do I mark a feature as one a client can sponsor?**
A: Click the feature's name, tick **Open to sponsors** and click **Save**.

**Q: The publication date has moved. How do I update the deadlines?**
A:
1. Click **Change dates**, set the new publication date and click **Save dates**. Deadlines that came from the usual rules move with it.
2. If you had typed any deadline yourself and want it worked out from the rules too, click **Use the usual rules**.

**Q: How do I find companies to chase for this issue?**
A: Look at **Who should we pitch?** Start with **Haven't rebooked**, then **Booked the last issue** and **Fit a feature**. Click a name to open the company in a new tab, or use **Email** or **Draft a proposal**.

**Q: How do I add an awards "entries close" date?**
A: Click **Change dates**, then **Add a key date**, type "Entries close", pick the date and click **Save dates**.

**Q: How do I see the bookings for this issue?**
A: Click **Bookings in the order register**.

**Q: How do I get rid of the "Please check these dates" banner?**
A: Check the dates, change any that are wrong, then click **The dates are right**.

**Q: What's the difference between Dropped and deleting a feature?**
A: A dropped feature stays on the list (struck through) so you can see what changed, but proposals, emails and pitch matching ignore it, and it isn't copied to next year. Delete removes it completely.

## If something doesn't work
- **No edit buttons or the notes are greyed out.** You can view this brand's plan but not change it. Admins, data managers and the brand's publishers can.
- **No Use the usual rules button.** It needs a publication date, a brand with usual deadlines set (in the brand's settings), and an issue or guide (not an event).
- **"Set the publication date first."** Add the publication date with **Change dates**, then try again.
- **"This brand has no deadline rules yet - add them in the brand's settings."** Open the brand's settings from the plan and add its usual deadlines.
- **No Delete from the plan button / "This issue has bookings in the order register, so it can't be deleted."** Issues with bookings, or that came from an imported order register workbook, can't be deleted.
- **No Email or Draft a proposal buttons.** Advertising has closed for this issue, or the company isn't linked to a company in the CRM yet.
- **Haven't rebooked says there's no one to compare with.** Last year's equivalent issue isn't on the plan (it needs a date and the same kind).
- **"There's already "<name>" in <title> <year>."** Another issue in the same part of the brand and year has that name.
- **Send from Outlook is greyed out.** Connect Outlook in Settings, fill in **To**, and fill anything still in curly brackets.
