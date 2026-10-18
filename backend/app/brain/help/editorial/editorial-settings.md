---
title: Brand settings for the editorial plan
screens: ["/editorial/settings/[brand]"]
summary: A brand's usual deadline rules, regular sections, schedule description, and the audience figures and links that proposals and email templates quote.
sources: ["frontend/src/app/(app)/editorial/settings/[brand]/page.tsx", "frontend/src/components/editorial/brand-settings-form.tsx", "frontend/src/lib/editorial-actions.ts", "backend/app/api/routes/editorial.py", "backend/app/sales/editorial.py", "backend/app/services/mail_merge.py", "backend/app/proposals/blocks.py", "backend/app/sales/brands.py"]
---

## What this screen is for
Each brand (Onboard Hospitality, The Business Travel Magazine, Selling Travel) has one settings page. It tells the Brain how the brand's deadlines usually work, so new issues fill their own deadlines in. It also holds the sections every issue has, a short description of the publishing schedule, and the brand's figures and links (print run, email database, readership, website, media pack and so on). Proposals and email templates quote those figures, so you change them here once and every email and proposal is up to date.

You get here from the editorial plan: click **Deadline rules & sections** on a brand's card, or the "<brand>'s settings" link under Regular sections on an issue page.

## What you see
- **Breadcrumb:** **Editorial plan** > "<brand> settings", and the heading "<brand> settings".
- **Usual deadlines:** one line per rule, reading like a sentence - "<deadline name> is <number> days before publication" or "<deadline name> is the <day> of the month before". Under each is a worked example, for an issue out on Thursday 11 June.
- **Regular sections:** the standing sections, each with a name and an optional "What it is".
- **About the publishing schedule:** a short paragraph, for example "Quarterly magazine, published to coincide with the industry's key trade shows."
- **Figures and links used in emails:** seven boxes, each showing the merge field it fills:
  - **Print run** - {{print_run}}
  - **Email database size** - {{email_database}}
  - **Who reads it** - {{readership}}
  - **Website** - {{website}}
  - **Media pack link** - {{media_pack}}
  - **Video link** - {{video}}
  - **Latest issue link** - {{latest_issue}}
- At the bottom, **Back to the plan** and **Save** for editors, or a "View only" note for everyone else.

## Buttons and controls
### Deadline name
The name of each rule. The three standard ones (**Advertising deadline**, **Editorial deadline**, **Copy & artwork deadline**) can't be renamed. Extra deadlines you add can be named anything, for example "Sponsored content deadline".

### Number of days / Day of the month
The number in each rule. For "days before publication" it's how many days (0 to 365). For "of the month before" it's the day of the month (1 to 31; in short months it uses the last day).

### How it's worked out (Days before / Day of the month before)
Switches a rule between a number of days before publication and a fixed day in the month before publication.

### Remove (bin icon) on a deadline
Takes that rule off. Nothing changes until you click **Save**.

### Advertising deadline / Editorial deadline / Copy & artwork deadline (plus buttons)
Adds a standard deadline the brand doesn't have yet. Each button only shows while that deadline is missing. Advertising and editorial start as 14 days before; copy starts as the 25th of the month before. Change the number to suit.

### Another deadline
Adds an extra rule with a name you type. Extra rules show on each issue as "other key dates". A rule left without a name is dropped when you save.

### Section name / What it is
Type the name of a regular section and, if you like, a short description. These appear on every issue page under "Regular sections in every issue".

### Remove (bin icon) on a section
Takes the section off when you save.

### Add a section
Adds a blank section line. Sections left without a name are dropped when you save.

### About the publishing schedule
Free text about how often and when the brand publishes. It shows on the brand's card on the editorial plan.

### Figures and links used in emails
Type the brand's current figure or link in each box. Leave a box empty if you don't have it.

### Back to the plan
Returns to the editorial plan for this brand without saving.

### Save
Saves everything on the page at once. You'll see "Saved".

## How it works
- **Who can change it:** admins and data managers can change every brand; each brand's publishers can change their own brand. Everyone else sees the page read only, with "View only - ask an admin, a data manager or this brand's publisher to change these."
- **How rules are used:** when someone adds an issue or guide with a publication date, any deadline they didn't type is worked out from these rules. Events and awards don't get rule-based deadlines. The same rules are used by **Use the usual rules** on an issue page, and by the published-plan loader for deadlines the published plan didn't give.
- **Example rules:** "9 days before publication" for an issue out on Thursday 11 June gives Tuesday 2 June. "The 25th of the month before" gives 25 May.
- **Changing a rule doesn't change existing issues.** Issues keep the dates they have. To update one, open it and click **Use the usual rules**, which replaces its deadlines with the new working-out. When an issue's publication date changes, its rule-based deadlines are worked out again from the new date.
- **Extra deadlines** (beyond the three standard ones) are stored on each issue as other key dates under the rule's name. Each one remembers which rule made it, so renaming a rule and using **Use the usual rules** updates that date (and its name) instead of adding a second one.
- **Figures in emails and proposals:** email templates fill {{print_run}}, {{email_database}}, {{readership}}, {{website}}, {{media_pack}}, {{video}} and {{latest_issue}} from these boxes. If **Website** is empty, the brand's own website address is used. Proposals list the brand's audience numbers (print run, email database, who reads it, website) and a link to the media pack from here; if none are saved, the proposal says "No audience numbers saved for this brand yet". A mail merge that uses a figure with nothing to fill it is refused with a plain reason, and the single-email window warns that some details had nothing to fill them.
- **Empty boxes** are not stored, so clearing a box removes that figure.

## Common questions
**Q: How do I set the advertising deadline to 9 days before publication?**
A:
1. If there's no Advertising deadline line, click **Advertising deadline** (with a plus sign).
2. Make sure the dropdown says **Days before**, and type 9 in the number box.
3. Check the example underneath, then click **Save**.

**Q: Our copy deadline is always the 25th of the month before. How do I set that?**
A: Add or find the **Copy & artwork deadline** line, choose **Day of the month before** in the dropdown, type 25 and click **Save**.

**Q: I changed the rules - why haven't my issues moved?**
A: Existing issues keep their dates. Open each issue and click **Use the usual rules** to work its deadlines out again.

**Q: The print run has changed. Where do I update it so emails use the new number?**
A: Type the new figure in **Print run** under **Figures and links used in emails** and click **Save**. Every email template using {{print_run}} and every new proposal picks it up.

**Q: How do I add a "Sponsored content deadline"?**
A: Click **Another deadline**, type "Sponsored content deadline", set the days or day of the month, and click **Save**. New issues will show it in their key dates.

**Q: Where do the regular sections show?**
A: On every issue page of this brand, under "Regular sections in every issue".

**Q: Where does the "About the publishing schedule" text appear?**
A: On the brand's card at the bottom of the editorial plan.

## If something doesn't work
- **Everything is greyed out and there's no Save button.** You can view but not change this brand. Admins, data managers and the brand's publishers can.
- **I can't rename "Advertising deadline".** The three standard deadlines have fixed names so the planner, reminders and emails know which is which. Add an extra deadline if you need another name.
- **"The day of the month must be between 1 and 31."** Fix the number on the "of the month before" rule.
- **"Each deadline is either a number of days before publication, or a day of the month before."** Pick one of the two options in the dropdown for every rule.
- **A rule or section disappeared after saving.** Lines with no name are dropped when you save.
- **My changes vanished.** Nothing is kept until you click **Save** - leaving the page or clicking **Back to the plan** loses unsaved changes.
- **An email still shows an old figure.** Check you clicked **Save**. Emails already sent, or drafts already filled in, keep the figure they had.
- **The page says the brand wasn't found.** The address doesn't match a brand. Go back to the editorial plan and use **Deadline rules & sections** on the brand's card.
