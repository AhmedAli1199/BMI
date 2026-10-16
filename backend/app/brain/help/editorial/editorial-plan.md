---
title: Editorial plan (year planner)
screens: ["/editorial"]
summary: Every brand's issues, specials, events and awards for the year, with their deadlines and planned features, shown as a wall planner, a deadlines list or a table.
sources: ["frontend/src/app/(app)/editorial/page.tsx", "frontend/src/components/editorial/year-planner.tsx", "frontend/src/components/editorial/issue-list.tsx", "frontend/src/components/editorial/deadlines-list.tsx", "frontend/src/components/editorial/issue-sheet.tsx", "frontend/src/components/editorial/brand-actions.tsx", "frontend/src/components/editorial/print-button.tsx", "frontend/src/components/editorial/editorial-ui.tsx", "frontend/src/lib/editorial-actions.ts", "backend/app/api/routes/editorial.py", "backend/app/sales/editorial.py", "backend/app/sales/editorial_seed.py", "backend/app/automations/editorial_deadlines.py", "backend/app/automations/settings_registry.py", "backend/app/sales/brands.py"]
---

## What this screen is for
The **Editorial plan** (in the menu under Editorial) is the year's schedule for every brand: each magazine issue, guide or special, event and awards night, with its deadlines and the features planned for it. Every issue on the plan is the same thing as an edition in the order register, so its bookings and its plan live in one place. Proposals, renewal emails and email templates read the plan to pitch the right issue with the right dates.

## What you see
- **Header:** the title "Editorial plan", the **Add an issue or event** button (only if you can change at least one brand) and the year buttons (hidden on the Deadlines view).
- **View switch:** **Year planner**, **Deadlines** and **List**.
- **Brand chips:** **All brands** and one chip per brand (for example OBH, TBTM, STM), each with its brand colour.
- On the Deadlines view, a **Show the next** choice: **30 days**, **60 days**, **120 days** or **year**. Otherwise a **Print or save as PDF** button.
- **"Your <year> plan is ready to load"** - a panel that appears only when a brand's published plan is waiting to be loaded (see below).
- **The plan itself**, in the view you picked:
  - **Year planner:** a wall chart running January to December. One band per brand, one row per part of the brand (the magazine, its events, its awards). Each issue is a bar that runs from its first deadline to its publication day. A key above the chart explains the marks: a solid dot is the **Publication / event day** (in the brand colour), an amber diamond is the **Advertising deadline**, other coloured diamonds are the **Editorial deadline**, the **Copy / artwork deadline** and any **Other key date**, and a thin red line is **Today**. Issues already published are faded. A small warning triangle next to an issue's name means some of its dates need checking. Hover over an issue to see all its dates.
  - **Deadlines:** every deadline and key date coming up, soonest first, grouped as **Just gone** (the last three days), **Today**, **This week**, **Next week**, then by month. Each line shows the date, what it is, the brand and issue, its theme, and a countdown ("Tomorrow", "In 5 days", "In 3 weeks"). Countdowns turn red when two days or fewer are left and amber within a week (publication and event days stay plain).
  - **List:** one table per brand, with **What**, **Publishes / on**, **Advertising deadline**, **Editorial deadline**, **Features** (planned, not dropped) and **Booked** (live bookings before VAT; a dash if none). Issues with no date yet appear at the bottom.
- **Brand tools:** a card for each brand with its "about" text, a warning listing any issues "without a date yet", the **Plan <next year>** button and **Deadline rules & sections**.
- **Who can change the plan** - hover the little info icon at the bottom for the rule.

## Buttons and controls
### Add an issue or event
Opens a side panel to put something new on the plan. Fill in:
- **Brand** and **Part of the brand** (which part of the order register its bookings go into - the magazine, the events, the awards).
- **What is it?** - **Issue**, **Guide / special**, **Event** or **Awards**.
- **Name** - for example "109", "Spring issue", "Dinner Club - March" or "People Awards 2027". A plain number shows as "Issue 109".
- **Publication date** (or **Date** for events and awards) and, for issues and guides, **Format** (**Print and digital**, **Print only**, **Digital only**) and **Months it covers (optional)**.
- **Theme (optional)** and **Shows it's handed out at (optional)** - or **Venue (optional)** for events and awards.

Click **Add and open it** to create it and go straight to its issue page. **Cancel** closes the panel. For issues and guides with a publication date, the deadlines are filled in from the brand's usual rules. Only shown to people who can change at least one brand, and the Brand list only offers the brands you can change.

### Year buttons
Show another year's plan. You can pick from two years back up to next year, plus any year the order register already has.

### Year planner / Deadlines / List
Switch between the wall chart, the list of what's due, and the table. Your brand and year choice is kept.

### All brands / brand chips
Show every brand, or just one. This also narrows the Deadlines view and the brand tools cards.

### Show the next: 30 days / 60 days / 120 days / year
On the Deadlines view only. How far ahead to look. It starts at 60 days. Things from the last three days always show under "Just gone".

### An issue on the planner, list or deadlines
Click any issue's bar, name or line to open its issue page.

### Print or save as PDF
Opens your browser's print window for the planner or list. The buttons and tool cards are left off the printout. Choose "Save as PDF" in the print window for a file.

### Load <brand>'s <year> plan (<number>)
In the "Your <year> plan is ready to load" panel. Fills the brand's plan from its published features list and media kit in one go: dates, deadlines, themes, where it's handed out and the features. If the order register already has the issue (same name, or for issues the same month), it fills in that issue's empty fields rather than making a new one. It also sets the brand's usual deadlines and regular sections if none were set. Dates only known to the month go on the 1st and are marked "please check", as is any deadline worked out from the usual rules. A message confirms how many issues and features were loaded. The panel only appears for the published plan's year, for brands you can change, and only while that brand has nothing planned yet for the year.

### Plan <next year>
On each brand's card, for people who can change that brand, when the brand has dated issues this year. Opens **Start <brand>'s <next year> plan from <this year>**:
- A table of what will be copied: this year's issue, what it **Becomes** and its **New date**. Untick any you don't want.
- **Copy the features too, as a starting point** - on by default. Dropped features are left behind; the rest come over as Planned.
- **Copy <number> to <next year>** makes them and takes you to next year's plan for that brand. **Cancel** closes it.

If everything is already there you'll see "Everything from <this year> is already in <next year>."

### Deadline rules & sections
Opens the brand's settings page, where its usual deadlines, regular sections, schedule text and the figures used in emails are kept. Everyone can open it; only editors can change it.

## How it works
- **Who can change what:** admins and data managers can change every brand. Each brand's publishers can change their own brand's plan. Everyone else can view it. The editorial plan is not limited by contact groups.
- **Kinds:** issues, guides / specials, events and awards appear on the plan. Monthly online and newsletter periods in the order register are sales buckets, not editorial issues, so they don't show here.
- **Deadlines from rules:** each brand has usual deadlines (for example, advertising 9 days before publication, or copy on the 25th of the month before). When you add an issue or guide with a publication date, any deadline you didn't type is worked out from these rules. Extra rules beyond the three standard deadlines become "other key dates".
- **Plan next year:** each issue is copied a year on to the same day of the week (whichever of 52 or 53 weeks lands closer to the same date). Dates that were only known to the month (on the 1st) stay on the 1st. All deadlines and key dates move by the same amount. Numbered issues carry on the numbering (if a title had issues 105-108, they become 109-112), as long as every issue in that title is numbered. Otherwise the year in the name is moved on (for example "Awards 2026" becomes "Awards 2027"). Name, kind, format, months covered and where it's handed out are copied; theme and notes are not. Everything copied is marked "please check".
- **"Please check":** dates estimated from a month, worked out from the rules, or copied from last year carry a warning triangle until someone confirms them on the issue page.
- **Booked figures** are live bookings in the order register, before VAT.
- **Advertising deadline reminders:** an automation (off until an admin turns it on in Automations settings, under "Advertising deadline reminders") runs each morning at 07:15. When an issue's advertising deadline is a set number of days away (14, 7 and 1 by default, set in "Remind this many days before"), the brand's publishers and anyone who sold that title in the last year get an in-app notification: the deadline, how many bookings so far and their value, and how many of last year's advertisers haven't rebooked. It links to the issue page. Each reminder goes once per issue per reminder day. Salespeople only get it if their sales record is linked to their login.

## Common questions
**Q: How do I add a new issue?**
A:
1. Click **Add an issue or event** at the top.
2. Choose the **Brand** and **Part of the brand**, pick **Issue**, and type the **Name** (for example "109").
3. Set the **Publication date** and anything else you know.
4. Click **Add and open it**. The deadlines are filled in from the brand's rules - check them on the issue page.

**Q: How do I see what's due this week?**
A: Click **Deadlines**. The "This week" and "Next week" groups are at the top. Pick a brand chip to see only one brand.

**Q: How do I set up next year's plan?**
A:
1. Make sure you're on this year.
2. On the brand's card at the bottom, click **Plan <next year>**.
3. Untick anything you don't want, and choose whether to **Copy the features too, as a starting point**.
4. Click **Copy <number> to <next year>**. Then open each new issue and confirm its dates.

**Q: What do the diamonds and dots mean on the planner?**
A: The solid dot is the publication or event day. Diamonds are deadlines: amber for advertising, and other colours for editorial, copy / artwork and other key dates. The key above the chart shows each colour. The red line is today.

**Q: Why does an issue have a little warning triangle?**
A: Some of its dates were estimated, worked out from the usual rules, or copied from last year. Open it and click **The dates are right** once you've checked them, or change them.

**Q: Can I print the plan for the wall?**
A: Yes. Pick **Year planner** or **List**, choose the brand and year, then click **Print or save as PDF**.

**Q: How do I get reminders before advertising deadlines?**
A: An admin turns on "Advertising deadline reminders" in Automations settings. Publishers of the brand, and salespeople who sold that title in the last year, then get an in-app notification 14, 7 and 1 days before (by default).

**Q: Where do I see an issue that has no date yet?**
A: It isn't on the planner. Its brand card says "<number> without a date yet" and names a few. The **List** view shows them at the bottom of the brand's table.

**Q: How do I change a brand's usual deadlines?**
A: Click **Deadline rules & sections** on that brand's card.

## If something doesn't work
- **"I can't see Add an issue or event."** You can only add issues for brands you can change. Admins and data managers can change all brands; publishers only their own. Ask an admin if you should have access.
- **"There's no Plan <next year> button."** It only shows for people who can change that brand, and only when the brand has issues with dates in the year you're looking at.
- **"The 'ready to load' panel has gone."** It only appears for the year the published plan was prepared for, and only while the brand has nothing planned yet. Once anything is planned (a deadline, a theme or a feature), it disappears so it can't overwrite your work. Selling Travel has no published plan loaded yet.
- **"My issue isn't on the planner."** It needs a date in the year you're viewing. Undated issues show on the brand card and in **List**. If you moved an issue's date into a different year on its page, it stays filed under its original year, so it may drop off both years' charts - add it again in the right year instead.
- **"Nothing due in this period."** No issue has a deadline or date in that window. Try **120 days** or **year**, or check the brand chip.
- **"There's already "<name>" in <title> <year>."** Each part of a brand can only have one issue of that name in a year. Use a different name, or open the existing one.
- **"Only admins, data managers and <brand>'s publishers can change this plan."** You can view the plan but not change that brand.
- **The Editorial plan isn't in my sidebar.** Your account doesn't have access to it. Ask an admin.
