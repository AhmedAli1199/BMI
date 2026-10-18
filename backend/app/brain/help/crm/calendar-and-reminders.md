---
title: Calendar and reminders
screens: ["/activities", "/reminders"]
summary: Calendar & Reminders - the Calendar & tasks tab (every scheduled call, meeting and to-do) and the Reminders tab (My reminders), and the "Log or schedule" button at the top of every page for logging a call or planning the next one.
sources: ["frontend/src/app/(app)/activities/page.tsx", "frontend/src/app/(app)/reminders/page.tsx", "frontend/src/app/(app)/layout.tsx", "frontend/src/components/log-interaction-dialog.tsx", "frontend/src/components/interactive-activity-table.tsx", "frontend/src/components/activity-detail-dialog.tsx", "frontend/src/components/activity-done-toggle.tsx", "frontend/src/components/reminder-row-actions.tsx", "frontend/src/components/remind-me-dialog.tsx", "frontend/src/components/record-reminders.tsx", "backend/app/api/routes/activities.py", "backend/app/api/routes/messaging.py", "backend/app/services/reminders.py", "backend/app/automations/messaging_jobs.py"]
---

## What this screen is for
Three related tools for keeping on top of your clients:
- **Log or schedule** (top of every page): write down a call, email, meeting or letter that has happened, add a note, or plan a call, meeting or to-do.
- **Calendar & tasks** (first tab of **Calendar & Reminders** in the menu): a grid of every scheduled call, meeting and to-do, brought over from Act! or added here, so you can see what's open, what's overdue and what's done.
- **My reminders** (the **Reminders** tab): the "Remind me" nudges you've set on contacts and companies.

## What you see
**Calendar & tasks**
- The title "Calendar & Reminders", the tabs **Calendar & tasks** and **Reminders**, a search box ("Search regarding, details, names...") and **Log or schedule**.
- A filter bar: **Open**, **Overdue** (with a red count), **Done** and **All**; **Type**: all, call, meeting, **To-do**; **Priority**: all, high, normal, low; and **Mine only**.
- The grid: **Done** tick box, **Type**, **Date** (red with "Overdue" when the date has passed and it isn't done), **Time**, **Priority**, **Regarding / Details**, **Contact**, **Company**, **Duration**, **Location**, a paperclip if it has attachments, and **Scheduled For** (who organised it). Done items are faded; overdue ones have a red tint.
- "Showing <n> activities" at the bottom, and "Times in London / BST".

**My reminders**
- The same heading and tabs, then **Upcoming**, **Done** and **All**.
- **Due now (<n>)** in red for open reminders whose time has passed, then **Later**.
- Each row: the date and time, whether you've been notified ("Scheduled", "Notified" or "Done", and "email too" or "in-app only"), what it's about (click to open the contact or company) and your note.

## Buttons and controls

### Log or schedule (top bar, and on Calendar & tasks)
Opens the dialog. First pick the **Contact or company** (search both). From a contact's or company's own page the dialog is already pinned to them, so there's no picker. Then choose a tab:
- **Log** (something that already happened): **Type** (Call, Meeting, Email, Letter) and **Result** (for a call: Call Attempted, Call Completed, Call Received or Call Left Message; Meeting Held; E-mail Sent or E-mail Not Sent; Letter Sent), **Title**, **Duration** (5 to 60 minutes), **Date / time** (now, unless you change it) and **Details**. **Save** adds it to their History.
- **Schedule** (something coming up): **Type** (Call, Meeting, To-do), **Repeats** (Never, Daily, Weekly, Monthly: when you mark it as done, the next one is added on the next date in the pattern after today; to stop it repeating, delete the next one instead of marking it done), **Title**, **Location** (meetings only), **Start**, **End**, **Timeless (no specific time, just a date)** (to-dos only) and **Details**. **Schedule** adds it to Calendar & tasks and the person's Activities.
- **Note**: type the **Note** and press **Save**. It goes on their Notes (or the company's Notes).
Every tab has **Make this private**. **Cancel** closes without saving.

### Search regarding, details, names...
Searches the title and details of activities. Press Enter. It keeps your other filters.

### Open, Overdue, Done, All
- **Open**: not yet done (the default).
- **Overdue**: not done, and the date was before today.
- **Done**: ticked off.
- **All**: everything.

### Type (all, call, meeting, To-do) and Priority (all, high, normal, low)
Narrow the grid. Things scheduled with **Log or schedule** are "normal" priority.

### Mine only / Showing mine only
Shows only activities you scheduled here, or that Act! records as organised by you (matched on your name). For salespeople it starts switched on; click it to see everyone's.

### Which title (the switcher at the top of the app)
To see one database's activities, or all you can see, use the **All Titles** switcher at the top of the app.

### Column headings
Click **Type**, **Date**, **Priority**, **Regarding / Details**, **Contact**, **Company** or **Duration** to sort what's on screen; click again to reverse.

### Done tick box
Marks the activity done (or not done again) straight away.

### Clicking a subject or row
Opens the activity's details: type, priority, Done, Attachment, Private and how often it repeats; when and how long; location; the contact and company (click to open them); the details; who organised it; and a tick box to **Mark as done**.

### Upcoming, Done, All (My reminders)
Switch between your open reminders, finished ones (newest first) and everything.

### Done
Closes the reminder. It moves to the **Done** tab.

### Snooze
Moves the reminder to **1 hour** from now, **Tomorrow morning** (9am), **1 week** or **1 month**. It will notify you again at the new time.

### Reopen
On a done reminder: makes it open again.

### Delete reminder (the bin)
Deletes the reminder straight away. There's no confirmation and no undo.

### Remind me (on a contact or company)
Sets a reminder: a quick pick (**Tomorrow**, **In 3 days**, **1 week**, **2 weeks**, **1 month**, **3 months**, **6 months**, **1 year**, all at 9am) or your own date and time, **What about? (optional)**, and **Email me as well**. **Set reminder** saves it. Your open reminders also show in an amber strip on that contact's or company's page, with **Done** and **All my reminders →**.

## How it works
- A **Log** entry is history: it's dated when it happened and appears on the person's History and Activities tabs. A **Schedule** entry is an activity: it appears on Calendar & tasks and on the person's Activities tab as "Scheduled" until it's ticked done.
- An activity is linked to either a contact or a company, never both.
- Calendar & tasks shows the activities of the contacts and companies you can see. By default it shows everyone's in those databases (as Act! did), newest first, up to 100 at a time.
- Reminders are personal: only you see yours. Every five minutes, reminders that have come due turn into a notification under the bell, and an email too if you ticked **Email me as well**. Snoozing or changing the time re-arms the reminder so you're notified again.
- Some reminders are set for you: saving call notes adds one per agreed action, due at 9am on the day agreed in the call ("by Friday", "next week", "14 Nov"), or the next working day if no day was mentioned, and sending a proposal sets a follow-up.

## Common questions
**Q: I've just had a call with a client. How do I record it?**
A: Press **Log or schedule** at the top, find the person, stay on **Log**, choose **Call** and a **Result** (for example Call Completed), add a **Title** and **Details**, and press **Save**.

**Q: How do I book a follow-up call for next week?**
A: **Log or schedule** > find the person > **Schedule** > **Type** Call > set **Start** > **Schedule**. It appears on Calendar & tasks.

**Q: What's the difference between a scheduled call and a reminder?**
A: A scheduled call is shared: it sits on Calendar & tasks and the contact's record for everyone to see. A reminder is just for you and pops up under the bell (and by email) at the time you chose.

**Q: How do I see only what's late?**
A: On Calendar & tasks, click **Overdue**. Add **Mine only** to see just yours.

**Q: How do I tick something off?**
A: Tick the **Done** box on its row, or open it and tick **Mark as done**.

**Q: How do I push a reminder back?**
A: On My reminders, press **Snooze** and pick when.

**Q: How do I set a reminder about a company?**
A: Open the company and press **Remind me** at the top.

**Q: Can I keep a note private?**
A: Tick **Make this private** before saving.

## If something doesn't work
- **Save or Schedule is greyed out**: pick a contact or company first. On the **Note** tab, type the note. On **Schedule**, a start date and time is needed.
- **"Couldn't save that - try again"**: something went wrong saving. Try again; if you picked a contact and then cleared it, pick them again.
- **Mine only shows nothing**: activities brought over from Act! only count as yours if the organiser's name matches your name in BMI Brain exactly.
- **Something I scheduled isn't on Calendar & tasks**: check the filters (**Open** hides done items) and the **All Titles** switcher at the top of the app. The grid shows up to 100 activities at a time, newest first; use the search box or filters to find older ones.
- **I can't see next week's repeat yet**: only the next one is on the calendar. It's added when you mark the current one as done.
- **I didn't get a reminder email**: check **Email me as well** was ticked (the row says "email too"). The in-app notification under the bell always comes.
- **I can't see a colleague's reminders**: reminders are personal. Ask them, or schedule a shared activity instead.
