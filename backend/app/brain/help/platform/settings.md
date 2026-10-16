---
title: Settings, team and sections
screens: ["/settings", "/settings/users", "/settings/sections"]
summary: Your own settings (theme, Outlook, notifications, dashboard and meeting recording), the Xero link, and for administrators the team accounts, roles, database access, the Accounts permission and which sections each role sees.
sources: ["frontend/src/app/(app)/settings/page.tsx", "frontend/src/app/(app)/settings/users/page.tsx", "frontend/src/app/(app)/settings/sections/page.tsx", "frontend/src/components/theme-switcher.tsx", "frontend/src/components/outlook-connection-card.tsx", "frontend/src/components/xero-connection-card.tsx", "frontend/src/components/preference-group.tsx", "frontend/src/components/team-roster.tsx", "frontend/src/components/user-form-dialog.tsx", "frontend/src/components/sections-editor.tsx", "backend/app/api/routes/settings.py", "backend/app/api/routes/users.py", "backend/app/api/routes/integrations.py", "backend/app/preferences.py", "backend/app/roles.py", "backend/app/ui_sections.py", "backend/app/brain/access.py", "backend/app/sales/accounts.py"]
---

## What this screen is for
**Settings** (the cog button at the bottom of the menu, next to your name) holds the choices that are personal to you: how the app looks, your Outlook connection, notification emails, what the dashboard counts as "recently active" and whether the notetaker records your meetings. Administrators and data managers also see the **Xero** link here. Administrators get two more pages: **Team & access** (accounts, roles, database access and the Accounts permission) and **Sections people see** (tidying the menu for each role or person).

## What you see
### Settings
From top to bottom:
- **Team & access** card - administrators only. Opens the team page.
- **Sections people see** card - administrators only. Opens the sections page.
- **Appearance** - the **Theme** picker.
- **Email** - the **Your Outlook mailbox** card. It shows whether you're connected (green tick, or an amber warning if it needs reconnecting), the sending limit for mail merges, and where the app's automatic emails come from.
- **Integrations** - the **Xero** card. Only administrators and data managers see this section. When connected it shows the organisation name, how many invoices have been copied, how many bookings are matched to an invoice, and when it last synced.
- **Dashboard**, **Notifications** and **Call notes** - one card per personal setting, each with two or three tiles to choose from. The tile with the tick is your current choice.

If you aren't signed in, an amber box says your changes can't be saved.

### Team & access - administrators only
- **Add team member** button at the top right.
- Three role cards explaining each role: **Administrator** (sees everything and manages the team), **Data Manager** (full access to their assigned databases) and **Sales** (their own contacts, tasks and queue only).
- The list of accounts. Each row shows the name, a role badge, the email and, for anyone who isn't an administrator, the databases or groups they can see. Extra badges:
  - **Disabled** (red) - the account can't sign in.
  - **You** - your own account.
  - **Accounts** - this person has the Accounts permission.
  - **Salesperson <initials>** - linked to their initials in the order register.
  - "No database access - can't see anything" (red) - a non-administrator with no grants.
- On each row, a pencil button (**Edit**) and a power button (**Disable account** or **Re-enable account**). You don't get a power button on your own row.

### Sections people see - administrators only
A table with one row per section of the app, grouped like the menu: **Everyday**, **Clients**, **Sales**, **Editorial**, **Outreach** and **The Brain**. There's a column for **Sales** and one for **Data Manager**, plus a column for each person who has their own choice (marked "just them"). Each cell is a tick box that reads **Shown** or **Hidden**. Automations Hub and Data Health say **Not available** in the Sales column, because Sales users can't open them anyway.

## Buttons and controls
### Theme (Morning, Evening, Night)
Changes how the app looks: **Morning** (bright and warm), **Evening** (dusk and dimmed) or **Night** (dark and quiet). It changes straight away and is remembered on this browser.

### Connect Outlook / Reconnect
Takes you to Microsoft to sign in, then back to Settings with a message saying which address your mail merges will now send from. Once connected, mail merges go from your own mailbox: they appear in your Sent Items and replies come back to you. **Reconnect** appears when the connection has expired; the reason shows in an amber box underneath. If neither button shows and you see "Not available yet", the server hasn't been set up for Outlook yet - ask an administrator.

### Disconnect (Outlook)
Forgets your Outlook connection. Mail merges can't send from your mailbox until you connect again.

### Connect Xero / Reconnect (Xero)
Administrators only. Signs in to BMI's Xero (read-only - nothing is ever written to Xero). After connecting, the invoices are synced straight away and then every hour. **Reconnect** appears if the connection has a problem. These buttons don't appear when Xero is linked through BMI's n8n workflow.

### Sync now
Administrators and data managers. Fetches the latest invoices from Xero straight away instead of waiting for the hourly sync. A message says how many invoices changed.

### Re-read all invoices
Administrators and data managers. Reads every invoice again from the start. It's needed once so the invoice matcher can see what each invoice is for, and takes a minute or two.

### Disconnect (Xero)
Administrators only. Forgets the Xero connection. Invoices already copied stay in the app. Not available when Xero is linked through the n8n workflow (it has to be removed on the server).

### "Recently Active" sort
Decides what the dashboard's **Recently Active Contacts** list counts as active:
- **Last record edit** (the default) - a contact shows as soon as any of its details change.
- **Last note or call** - a contact shows only once a note, call or meeting has been logged.

### Email me notifications
**On** (the default) emails you each notification from the automation mailbox as well as showing it under the bell. **Off** keeps them in the app only. Some notifications, such as feedback updates, only ever appear under the bell.

### Record my meetings
What the notetaker does with meetings on your connected calendar that have a Meet or Teams link:
- **Join automatically** (the default) - BMI Notetaker joins and takes notes; you can still skip any meeting.
- **Just remind me** - a reminder before each meeting, with a button to send the notetaker.
- **Off** - nothing happens unless you send the notetaker yourself.

### Team & access (card) / Sections people see (card)
Open the administrator pages. **Settings** in the breadcrumb above the title, or **Back to Settings**, returns you.

### Add team member
Opens **Add a team member**, which creates a real login. Fill in:
1. **Name** and **Email**.
2. **Temporary password** (at least 8 characters). The shuffle button (**Generate a random password**) makes an easy-to-read one, and the copy button (**Copy to clipboard**) copies it. Share it securely, never over chat.
3. **Role** - **Administrator**, **Data Manager** or **Sales**.
4. **Their initials in the order register** - links the login to a salesperson, or **Not a salesperson**. If a salesperson has exactly the same name and no login yet, they're picked for you (it says so underneath). Initials already linked to another login are greyed out.
5. **Accounts** tick box - see below.
6. **Database access** (not shown for administrators, who see everything) - press **Add database**, choose a database, then leave **Whole database** or pick one group (that group and its sub-groups). Add as many rows as needed; the bin button (**Remove this grant**) removes one.
7. Press **Create account**.

### Edit (pencil)
Opens **Edit <name>** with the same fields. The email can't be changed. Type in **Reset password** only to give them a new password (leave it blank to keep theirs). Press **Save changes**. The database list you save replaces the old one completely.

### Disable account / Re-enable account (power button)
Disabling stops the person signing in; re-enabling lets them back in. Nothing they did is deleted. You can't disable yourself.

### Accounts (tick box)
Gives someone the Accounts permission: they check every new booking before its confirmation goes out, and approve any change to a booking once it's checked. Once anyone has this, only they can do it - salespeople send a change request instead. Until nobody has it, administrators and data managers do the checks.

### Give one person their own choice (Choose a person…)
On **Sections people see**. Adds a column for one Sales or Data Manager user, starting from their role's choice, so you can show or hide sections just for them. Their own choice then replaces their role's. The **X** next to their name (**Use their role's choice again**) removes the column.

### Shown / Hidden tick boxes
Untick to hide that section from the menu for that role or person; tick to show it again. Nothing changes until you press **Save**.

### Save (sections)
Saves the table. "You have unsaved changes" shows until you do. People see the change the next time a page loads.

## How it works
- Your personal settings are saved to your account, so they follow you to any computer. The theme is the exception: it's remembered by the browser.
- A role decides what someone can do. Database access decides which data they can see. A role on its own never grants any data: a Data Manager or Sales user with no grants sees nothing. Administrators see every database without grants.
- A group grant lets someone see the contacts in that group and its sub-groups, and those contacts' companies.
- Removing database access applies straight away. A new grant, or a change of role, fully applies the next time that person signs in (until then their database switcher and menu still show the old set).
- One login per salesperson: linking initials to a login moves that salesperson's waiting renewals and follow-ups onto that person's Today list straight away.
- The Accounts permission: once at least one active person has it, only they can pass booking checks and approve changes to checked bookings. While **Accounts are away** is switched on (Automations Hub settings, under Sales Order Register), administrators can stand in and also get Accounts' notifications.
- Sections: hiding a section takes it out of that person's menu. Administrators always see everything. It doesn't stop someone opening a page from a link, and their role and database access still decide what they can see and do.
- Sections also limit **Ask the Brain**: if a section is hidden for someone, the Brain won't look it up, explain it or answer questions about it for them. It replies "You don't have permission to view that." The same happens for areas their role can't open (for example the team page and section settings for anyone who isn't an administrator, and Xero for Sales users).
- Xero is read-only. Invoices sync every hour and each booking shows whether its invoice is paid, unpaid or overdue.
- Automatic emails (reminders, alerts, new bookings to Accounts) come from the automation mailbox. Until that mailbox is connected, they appear under the bell only.

## Common questions
**Q: How do I send mail merges from my own Outlook?**
A: 1. Open **Settings** (the cog at the bottom of the menu). 2. Under **Email**, press **Connect Outlook**. 3. Sign in with your Microsoft account. You'll come back to Settings with a message saying which address mail merges will send from.

**Q: How do I add a new member of staff?**
A: Administrators only. 1. In **Settings**, open **Team & access**. 2. Press **Add team member**. 3. Fill in their name, email and a temporary password (use the shuffle button to make one). 4. Pick their role and, for a salesperson, their initials in the order register. 5. Press **Add database** and choose what they can see (not needed for administrators). 6. Press **Create account**, then share the password with them securely.

**Q: How do I give Samantha the Accounts permission?**
A: 1. Open **Settings** > **Team & access**. 2. Press the pencil on her row. 3. Tick **Accounts**. 4. Press **Save changes**. An **Accounts** badge appears on her row.

**Q: Someone has left - how do I stop them signing in?**
A: In **Team & access**, press the power button (**Disable account**) on their row. They get a red **Disabled** badge and can't sign in. Nothing they did is deleted, and you can press **Re-enable account** later.

**Q: How do I hide sections a salesperson doesn't need?**
A: Administrators only. 1. In **Settings**, open **Sections people see**. 2. Untick the sections in the **Sales** column. 3. Press **Save**. To do it for just one person, choose them from **Choose a person…** first and untick in their column.

**Q: I've reset someone's password - what do I tell them?**
A: Press the pencil on their row, type a new password in **Reset password** (or press the shuffle button), copy it with the copy button, press **Save changes**, then give it to them securely, not over chat.

**Q: How do I stop the notetaker joining my meetings?**
A: In **Settings**, under **Call notes**, pick **Just remind me** (you get a reminder with a button to send it) or **Off**.

**Q: Why aren't my Xero invoice statuses up to date?**
A: They sync every hour. An administrator or data manager can press **Sync now** in **Settings** under **Integrations** to fetch them straight away.

**Q: How do I switch the app to dark mode?**
A: In **Settings**, under **Appearance**, open the **Theme** picker and choose **Night**.

## If something doesn't work
- **I can't see Team & access or Sections people see.** They're for administrators only. Other people who open those pages see "Administrators only".
- **I can't see the Integrations section.** Xero is shown to administrators and data managers only.
- **There's no Connect Xero or Disconnect button.** Only administrators can connect or disconnect Xero. If Xero is linked through BMI's n8n workflow, those buttons never show.
- **Connect Outlook isn't there and it says "Not available yet".** The Microsoft sign-in hasn't been set up on the server. Ask an administrator.
- **Create account is greyed out.** Fill in name, email and a temporary password, pick a role, and give at least one database grant (unless they're an administrator).
- **It won't save the password.** Passwords need at least 8 characters.
- **It says the email already exists.** There's already an account with that address. Find it in the list and edit it instead (re-enable it if it's disabled).
- **Their initials are greyed out ("linked to another login").** Those initials are already linked to someone else. Edit that person, set them to **Not a salesperson**, save, then try again.
- **A new role hasn't taken effect.** Role changes apply the next time they sign in. Ask them to sign out and back in.
- **Someone still sees a hidden section.** They see the change the next time a page loads. Administrators always see everything, and a person with their own column follows that column, not their role's.
- **Ask the Brain says "You don't have permission to view that."** That section is hidden for you, or your role can't open it. Ask an administrator if you need it.
- **A setting won't save.** Check you're signed in. If it still fails, the message on screen will say so - try again in a moment.
