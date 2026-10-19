---
title: Home dashboard
screens: ["/"]
summary: The home page - contact, company and group totals for the databases you can see, what the automations found or resolved recently, the most recently active contacts and the companies with the most contacts.
sources: ["frontend/src/app/(app)/page.tsx", "frontend/src/components/publication-tile-button.tsx", "frontend/src/components/publication-form-dialog.tsx", "frontend/src/components/contact-form-dialog.tsx", "frontend/src/components/company-form-dialog.tsx", "frontend/src/components/group-form-dialog.tsx", "frontend/src/lib/access.ts", "backend/app/api/routes/dashboard.py", "backend/app/preferences.py", "backend/app/core/visibility.py"]
---

## What this screen is for
The home page (**Home** in the menu, or the BMI name at the top of the menu) gives you a quick picture of the contact database: how many contacts, companies and groups you have, what BMI Brain's automations have found for review, and who has been active recently. It's also a quick place to add a contact, company or group. It only ever counts what you're allowed to see. The sales figures are on the Sales overview, not here.

## What you see
From top to bottom:
- **Header** - the Brain waving and a greeting ("Good morning, <your first name>"), with **Add contact**, **Add company** and **New group** buttons on the right. If your access is limited to one group, a line says "Showing <database> / <group> only".
- **Database tiles** - only when you're looking at all titles. One tile per database you can see (for example OnBoard, Selling Travel, Prospects), each with its description and how many contacts it has. Administrators also get an **Add database** tile.
- When one database is chosen instead, a line says "Showing <database> only", with **Show all titles** if you can see more than one.
- **Three totals** - **Total Contacts**, **Companies** and **Groups**. Each one is a link to that list.
- **BMI Brain · Overnight Activity** - shown when there's anything to show:
  - **New for your review** - the five newest suggestions waiting in the Review Queue, with when each arrived.
  - **Recently resolved** - the five most recently approved or rejected suggestions, labelled "Approved" or "Rejected".
- **Recently Active Contacts** - six contacts, with their job, company and how long ago they were active. The line under the heading says which meaning of "active" you're using.
- **Top Companies** - up to six companies with the most contacts on file, with their industry and a count.

## Buttons and controls
### Add contact
Opens **Add contact**. Choose the database it belongs to, then fill in first name, last name, job title, department, company (search for one), email and phone. You need at least a first or last name. Press **Add contact** to save it.

### Add company
Opens **Add company**: choose the database, then name, industry, category and website. Press **Add company** to save.

### New group
Opens **New group**: choose the database, give it a name and an optional description, and press **Create group**.

### Database tiles
Pressing a tile switches the whole app to that database (the same as the database switcher at the top of the page) and stays on the dashboard. Every list you open afterwards shows only that database until you switch back.

### Show all titles
Switches back to all the databases you can see. It doesn't appear if you can only see one database.

### Add database
Administrators only. Opens **Add a database** to create a new title or list that contacts and companies can be filed under, like OnBoard, Selling Travel and Prospects. Give it a **Name**, check the **Short name** (filled in for you, and it can't be changed later), add a **Description**, and pick a **Color** and **Icon**. Press **Add database**. The new tile appears straight away. Nobody else can see it until they're given access under Team & access.

### Total Contacts / Companies / Groups
Each total opens that list.

### Open review queue
Opens the Review Queue.

### Items under New for your review / Recently resolved
Open the Review Queue filtered to that kind of suggestion (and, for resolved ones, to approved or rejected).

### View all → (Recently Active Contacts / Top Companies)
Opens the full contact list or company list.

### A contact or company in the lists
Opens that contact's or company's page.

## How it works
- Everything is limited to what you can see. Administrators see every database. Everyone else sees only the databases (or the group and its sub-groups) they were given under Team & access. If you have access to one group, the contact total counts only that group's contacts.
- Choosing a database (with a tile or the switcher at the top) narrows every figure to it. Companies are counted per company record, and a company's contact count only counts contacts in the chosen database.
- **Recently Active Contacts** follows your own setting in **Settings** under **Dashboard** (the **Change this in Settings** link under the list's title takes you there):
  - **Last record edit** (the default): the contacts most recently added or edited, including edits made in Act! before the move. Every contact has a date, so the list is never empty.
  - **Last note or call**: the contacts with the latest note or logged call or meeting. Contacts with no notes or history don't appear at all.
- **Top Companies** ranks companies by how many contacts they have on file; companies with none are left out.
- **Overnight Activity** comes from the Review Queue and only includes suggestions you're allowed to see there: your databases, and for a salesperson only the kinds meant for sales (their own renewals, for example). It doesn't show at all if an administrator has hidden the Review Queue for you (Settings > Sections). Each item shows the name of its card type, as in the Review Queue.
- If your account has no database access at all, the page says "No database access yet" instead of showing figures.

## Common questions
**Q: Why does my contact total look smaller than a colleague's?**
A: The dashboard only counts the databases (or group) you have access to, and only the database you've chosen at the top. Press **Show all titles** to include every database you can see. An administrator can change your access under **Settings** > **Team & access**.

**Q: How do I add a contact quickly?**
A: Press **Add contact** at the top right of the dashboard, choose the database, fill in at least a first or last name, and press **Add contact**.

**Q: What does "Recently Active" mean?**
A: It depends on your setting. By default it's the contacts most recently added or edited. To see only contacts with a recent note or call instead, go to **Settings**, find **"Recently Active" sort** under **Dashboard**, and choose **Last note or call**.

**Q: How do I look at just one magazine's contacts?**
A: When you're on all titles, press that magazine's tile. To go back, press **Show all titles**.

**Q: What is "Overnight Activity"?**
A: It's what BMI Brain's automations have suggested recently (for example possible duplicate contacts or bounced emails) and what's been approved or rejected. Press an item, or **Open review queue**, to deal with them.

**Q: How do I add a new database?**
A: Administrators only. On all titles, press the **Add database** tile, fill in the name, description, colour and icon, and press **Add database**. Then give people access to it under **Settings** > **Team & access**.

**Q: Where are the sales figures?**
A: Not on this page. Open **Overview** under Sales in the menu for the sales figures.

## If something doesn't work
- **It says "No database access yet".** Your account hasn't been given any database. Ask an administrator to add one under **Settings** > **Team & access**.
- **There's no Add database tile.** Only administrators can add databases, and the tiles only show when you're looking at all titles.
- **There's no Show all titles link.** You can only see one database, so there's nothing to switch to.
- **Overnight Activity is missing.** It only appears when there's something waiting or recently resolved.
- **Recently Active Contacts is empty.** You've chosen **Last note or call** and nobody in this database has a note or logged call yet. Switch back to **Last record edit** in **Settings**.
- **Add contact is greyed out in the form.** Type a first or last name.
- **A new database isn't showing for someone.** They need access to it under **Settings** > **Team & access**, and it shows the next time they sign in.
