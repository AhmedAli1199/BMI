---
title: Contacts
screens: ["/contacts", "/contacts/[id]", "/contacts/import", "/contacts/import/[id]"]
summary: Find, sort and export people, copy their emails, change many at once, import a spreadsheet, and work on one contact's page (details, notes, history, groups, reminders and emails).
sources: ["frontend/src/app/(app)/contacts/page.tsx", "frontend/src/app/(app)/contacts/[id]/page.tsx", "frontend/src/app/(app)/contacts/import/page.tsx", "frontend/src/app/(app)/contacts/import/[id]/page.tsx", "frontend/src/components/interactive-contact-table.tsx", "frontend/src/components/contact-selection-actions.tsx", "frontend/src/components/contact-form-dialog.tsx", "frontend/src/components/contacts/advanced-search.tsx", "frontend/src/components/contacts/bulk-update-dialog.tsx", "frontend/src/components/contacts/copy-emails-button.tsx", "frontend/src/components/contacts/import/import-upload.tsx", "frontend/src/components/contacts/import/import-map-step.tsx", "frontend/src/components/contacts/import/import-review-step.tsx", "frontend/src/components/contacts/import/import-done.tsx", "frontend/src/components/act-subbar.tsx", "frontend/src/components/act-contact-card.tsx", "frontend/src/components/act-tab-workstation.tsx", "frontend/src/components/unified-activity-timeline.tsx", "frontend/src/components/touchpoint-bar.tsx", "frontend/src/components/contact-groups-editor.tsx", "frontend/src/components/reassign-contact-button.tsx", "frontend/src/components/duplicate-contact-dialog.tsx", "frontend/src/components/field-change-history.tsx", "frontend/src/components/remind-me-dialog.tsx", "frontend/src/components/record-reminders.tsx", "frontend/src/components/mail-merge/email-from-template.tsx", "backend/app/api/routes/contacts.py", "backend/app/api/routes/contact_tools.py", "backend/app/api/routes/contact_imports.py", "backend/app/contacts/fields.py", "backend/app/contacts/scope.py", "backend/app/contacts/import_engine.py", "backend/app/services/contact_lookup.py", "backend/app/services/contact_transfer.py"]
---

## What this screen is for
Contacts is BMI's address book: every person in every title's database. Use the list to look people up (Act!'s "Lookup"), sort them, export them to Excel, copy their email addresses, change a field for many people at once, or start a mail merge. Open a person to see and edit their details, notes, history, groups and reminders. **Import** adds people from an Excel sheet, CSV or PDF.

## What you see
**The list (Contacts)**
- Header with the number of contacts that match, and buttons: **Import**, **Copy emails**, **Bulk update**, **Export**, **Mail merge** and **Add contact**. If your access is limited to one group, a line says "Showing <group> only".
- The lookup box: a search box plus **Company**, **City / town**, **Country** and **Job title** boxes, the **Look up** button, and **Advanced search** underneath.
- Title chips (**All Titles** and one per database). This is the same title filter as the switcher at the top of the app, so it also applies to Companies, Groups and the Dashboard until you change it back.
- The table: tick box, **Contact & Title**, **Company**, **Location**, **Email** and **Publication** (a coloured badge for the database the person belongs to). 50 a page, with **← Previous** and **Next →** at the bottom.

**A contact's page**
- A ribbon with **Contacts**, **Companies** and **Groups**, a **List** / Detail switch, and arrows to step through the list you came from ("12 of 340").
- **Back to Contacts**, then **Remind me**, **Write**, **Email from a template** and **Duplicate**.
- An amber strip with your own open reminders about this person (red once overdue).
- The record card in three columns: Business Card (company, title, department, phone, mobile, e-mail), Address & Web, and Status & Activity (ID/Status, Referred By, Birthdate, and the dates of the last meeting, reach, attempt and letter).
- **History of changes** (closed until you click it).
- Tabs: **Activities (<n>)**, **Notes (<n>)**, **History (<n>)**, **Groups (<n>)**, **Magazine & Issues** and **User Fields (<n>)**, with one search box that searches the first three at once.

## Buttons and controls

### Search box ("Name, email, phone, address, company…")
Type several words in any order. Every word must appear somewhere: name, job title, department, category, company, email, phone (digits alone work, so "020 7946" finds "+44 (0)20 7946..."), any address line or postcode, or a custom field. Only the first six words count. Notes are not searched here; use **Advanced search** for that.

### Company, City / town, Country, Job title
Each one narrows the list further ("contains"). Press **Look up** to run the search. The small X next to **Look up** (**Clear lookup**) clears the whole lookup.

### Advanced search
Opens rules of the form field / how / value, for example Postcode **starts with** SW1. **Add a rule** adds another; the bin (**Remove this rule**) takes one away. With two or more rules, choose **all of these rules** or **any one of these rules**. Press **Look up** to apply. Active rules show as chips; the X on a chip removes that rule. You can search names, job details, company, any email, phone or address, notes, the group someone is in, status flags (unsubscribed, bounced, private), dates (added, last emailed, last met, birthday) and every Act! custom field.

### Column headings (Contact & Title, Company, Location, Email)
Click to sort, click again to reverse. Location sorts by town. **Publication** does not sort.

### Title chips (All Titles and each title)
Show one database, or all of the ones you can see. **All Titles** only appears if you have more than one.

### Tick boxes and the selection bar
Tick people (or the top box for the whole page). A bar appears with "<n> contacts selected" and:
- **Select all <n> matching**: shown when you have ticked a whole page and more match. Ticks everyone in the lookup.
- **Add to group**: pick a group and press **Add to group**. People already in it are left as they are.
- **New group**: type a **Group name** and optional **Description (optional)**, then **Create group**. Handy for a one-off mailing.
- **Export**, **Copy emails**, **Bulk update** and **Mail merge** work on just the ticked people.
- The X (**Clear selection**) unticks everyone.

### Import
Opens Import contacts (see below).

### Copy emails
Hovering over it says "Copy these contacts' email addresses, ready to paste into Outlook's Bcc box". Copies the email addresses of everyone in the lookup (or the ticked people), separated by semicolons, ready to paste into Outlook's Bcc box. People who unsubscribed, opted out or whose email bounced are left out, as are people with no email and repeated addresses; the message says how many. Over 5,000 contacts is too many to copy: narrow the search or use **Export**. Above 500 it reminds you Outlook only sends to about 500 at once.

### Bulk update
Opens "Change many contacts at once" for the whole lookup (or the ticked people).
1. On **Make a change**, pick **Which field?** Names, job details, category, referred by, last results, the status flags (Unsubscribed, Opted out of email, Private) and the Act! custom fields can be changed. Email, phone and address can't; edit those on each contact.
2. Choose **Set it to…** (type the **New value**, or Yes/No), **Clear it**, or **Find and replace** (**Find** and **Replace with**; leave Replace with empty to remove the text). Yes/no fields can't use find and replace.
3. Press **See what will change**. It shows "<n> of <total> contacts will change", how many already match, and up to eight before → after examples.
4. Press **Change <n> contacts**. Nothing is saved before this.
Afterwards the message has an **Undo** button. **Recent changes** lists the last 30 bulk changes with who did them and an **Undo** button on each.

### Export
Downloads the lookup as an Excel sheet, in the same order as the screen (up to 50,000 rows). It has names, salutation, job, company, email, phones, address, database, groups, unsubscribed and bounced, plus a column for every custom field that has a value. From the selection bar it exports just the ticked people.

### Mail merge
Opens Mail merge with this lookup (including any advanced search) already chosen as the contacts.

### Add contact
Opens a form: choose the **Database**, then **First name**, **Last name**, **Job title**, **Department**, **Company** (search for it), **Email** and **Phone**. You need at least a first or last name. **Add contact** saves it and opens the new record.

### The record arrows (First Record, Previous Record, Next Record, Last Record)
Step through the same list, in the same order, that you opened the contact from.

### Remind me
Pick **Tomorrow**, **In 3 days**, **1 week**, **2 weeks**, **1 month**, **3 months**, **6 months** or **1 year** (quick picks land at 9am), or type a date and time. Add **What about? (optional)** and untick **Email me as well** if you only want the bell. **Set reminder** saves it. It shows on this page and in My reminders.

### Write
Opens Mail merge with just this person chosen.

### Email from a template
Opens "Email from a template". Choose the **Template** (ones marked "(needs a check)" were brought over from Act! and haven't been read through). If it mentions an issue, pick **Which issue or event** and type **The feature you're pitching**. The email fills in; change **To**, **Copy to (optional)**, **Subject** and **Message** as you like. **Send from Outlook** sends it from your own Outlook and notes it on their history. **Copy** copies the subject and text for your own email (nothing is noted). Sending is blocked while something in {{curly brackets}} is still unfilled, and needs Outlook connected (the **Settings** link).

### Duplicate
Act!'s "duplicate contact": a new person at the same company. Type **First name**, **Last name**, **Email**, **Job title** and **Direct phone**; keep **Put them in the same groups** ticked to copy the groups. **Create contact** copies the company, database, owner, business address and office phones (never mobiles, home addresses or the email) and opens the new person.

### Edit Record, Save Changes, Cancel
**Edit Record** makes the card editable: names, company, title, department, phone, mobile, e-mail, address, ID/Status (the category), Referred By and Birthdate. **Save Changes** saves; **Cancel** throws the edits away. The copy icon next to a phone or email copies it.

### Mark as departed
For someone who has left. Search for who replaced them and press **Move notes and history**. Every note and history entry moves to that person, and both records get a short "Departure" note. The old record itself stays. Scheduled activities don't move.

### Company Profile
Opens the person's company.

### History of changes
Shows who changed which field, from what to what, and when (newest first).

### Activities, Notes, History, Groups, Magazine & Issues, User Fields (tabs)
- **Activities**: everything in one timeline (notes, history and scheduled items), newest first, with filters **All Activity**, **Calls**, **Meetings**, **Notes**, **Emails** and **Tasks**. Scheduled items say Scheduled (amber) or Done (green).
- **Notes**: date, type, the note and where it came from.
- **History**: what happened (calls, emails, meetings, letters).
- **Groups**: the groups they're in. The X on a group takes them out; **Add to group** lets you search for one to add.
- **Magazine & Issues**: custom fields whose names look like issue or advertising details.
- **User Fields**: every Act! custom field on this person.

### Search this contact's notes & history...
Narrows and highlights matches in Activities, Notes and History at once; the tab counts show "x of y".

### Quick Touchpoint ... Log or schedule →
The bar above Activities and Notes. Opens the Log or schedule dialog for this person (see the "Calendar and reminders" guide).

### The bin on a note, history entry or activity
Deletes it after you confirm. It can't be undone.

### Done and All my reminders → (reminder strip)
**Done** closes that reminder. **All my reminders →** opens My reminders.

### Import contacts: Choose a file, Download an example sheet
Drop a file or press **Choose a file**: Excel (.xlsx, .xls), CSV or PDF, up to 15 MB and 20,000 rows. **Download an example sheet** gives you a sheet with the usual headings. **Recent imports** lists your finished imports (administrators and data managers see everyone's); click one to open it.

### Import step 2 (Match columns)
Each column of your file is shown with examples and the contact field it will go into. Labels: **Matched**, **Check this** (we weren't sure), **Your choice**, **Not imported** or **Empty**.
- Change any field in its dropdown, choose **Don't import this column**, or **＋ Import as a new custom field…** and name it.
- "Maybe:" buttons (**Use <field>**) apply a suggestion.
- **Keep them all as custom fields** keeps every column we couldn't place.
- **Match again** redoes the automatic matching (your changes are lost). **File settings**: pick the **Sheet**, untick **The file has a heading row**, or choose **Which line has the headings?**.
- **Which database do they belong to?** is required. Duplicates are only looked for in that database.
- **Add everyone to a group (optional)**: **No group**, **A new group** (named after the file, which you can change) or **An existing group**.
- **If someone is already in the CRM**: **Fill in what's missing** (the default), **Leave them alone**, **Update with the file** or **Add them again anyway**.
- **Create companies that aren't in the CRM yet**: companies already there are linked even if spelled "Ltd" or "Limited".
- "How your first rows will look" previews three rows. **Discard** throws the import away. **Review <n> rows** moves on.

### Import step 3 (Review)
Tiles count what will happen; click one to show only those rows (**Show all rows** clears it): **Will be added**, **Will be updated**, **Already in the CRM**, **Repeated in the file**, **Possible duplicates**, **Need a look**, **Can't import**, **Left out**. Search the rows, untick a row to leave it out, and use the "Already in the CRM as…" or "Possibly the same as…" links (they open the existing contact in a new tab). **Download as Excel** gives the row-by-row report. **Back to matching** goes back. **Import <n> contacts**, then **Import them** to confirm (**Not yet** to stop).

### Import step 4 (Done)
Shows Added, Updated, Left out and Already complete. **See the contacts** opens the list with the newest first. **Import another file**, **Download the report**, and **Undo this import**.

## How it works
- What you see is limited to the databases (or the group) you've been given in Settings > Users. This applies to the list, export, copy emails, bulk update and mail merge. Opening a contact outside your access shows "not found". Administrators see everything.
- The same lookup (search, boxes, advanced rules and sort) is used by the list, the record arrows, export, copy emails, bulk update and mail merge, so they all mean the same people in the same order. Export, bulk update and copy emails handle up to 50,000 contacts; copy emails stops at 5,000.
- Every edit to a contact's own fields (by hand, by bulk update or by an import) is recorded in **History of changes** with who made it.
- Bulk update **Undo** puts back the old value only for people whose value is still the one the update set. Anyone changed again since is left alone, and the message says how many.
- Import recognises people already in the CRM by email address, or by name plus company. It tidies names, emails, phone numbers and postcodes, splits full names, and flags bad emails, missing names and repeats. Rows with no name and no email are skipped. PDFs with a table are read as a table; otherwise the text is read for you and flagged for checking.
- Import **Undo** removes the people it added, except anyone someone has worked on since (an edit, a history entry, an activity or a note), and puts updated people back as they were.
- The Act! custom fields show under their stored names (for example "User3") until BMI tells us what they mean; then the real name appears everywhere.

## Common questions
**Q: How do I find every travel counsellor in London?**
A: Type "counsellor" in **Job title** and "London" in **City / town**, then press **Look up**.

**Q: How do I search by postcode or something in their notes?**
A: Press **Advanced search**, pick Postcode (or Notes (text)) in the first box, choose how to compare, type the value and press **Look up**.

**Q: How do I get these people into Excel?**
A: Run your lookup and press **Export**. To export only some, tick them and press **Export** in the selection bar.

**Q: How do I paste a list of addresses into Outlook?**
A: Run the lookup (or tick people), press **Copy emails**, then paste into the Bcc box. Send in batches of about 500.

**Q: How do I set the same value on hundreds of contacts?**
A: Run the lookup, press **Bulk update**, choose the field and **Set it to…**, type the value, press **See what will change**, check the examples, then **Change <n> contacts**.

**Q: I made a bulk change by mistake. Can I undo it?**
A: Yes. Press **Undo** on the message straight away, or open **Bulk update** > **Recent changes** and press **Undo** next to it.

**Q: How do I make a small mailing group from a big lookup?**
A: Tick the people (or **Select all <n> matching**), press **New group**, name it and press **Create group**.

**Q: How do I add a colleague of an existing contact?**
A: Open the existing contact and press **Duplicate**, or open the company and use **Add contact here**.

**Q: Someone has left and a new person replaced them. What do I do?**
A: Add the new person first. Then open the old contact, press **Mark as departed**, pick the new person and press **Move notes and history**.

**Q: How do I import a list from an exhibition?**
A: Contacts > **Import** > **Choose a file**. Check the matched columns, choose the database (and a group to find them later), press **Review <n> rows**, check the flagged rows, then **Import <n> contacts** > **Import them**.

**Q: Who changed this person's job title?**
A: Open them and click **History of changes**.

## If something doesn't work
- **"No contacts match this lookup"**: one of the boxes or rules is too narrow. Press the X next to **Look up** to start again, and check the title chips aren't set to one database.
- **I can't find someone I know is there**: they may be in a database or group you haven't been given. Ask an administrator.
- **Bulk update doesn't list email, phone or address**: those can't be changed in bulk. Edit them on each contact.
- **"Change <n> contacts" is greyed out**: the preview found nothing to change ("already match"). If you change any choice after the preview, press **See what will change** again.
- **"That's more than 50,000 contacts - narrow the search first."**: bulk tools stop at 50,000. Copy emails stops at 5,000.
- **Add contact (or Create contact) is greyed out**: type a first or last name.
- **Review <n> rows is greyed out** in an import: the red message beside it says why, usually "Choose which database these contacts belong to.", "Match at least a name column (First name, Last name or Full name) or an Email column.", or two columns set to the same field.
- **"You can't import into that database."**: you don't have access to it.
- **Some people weren't removed when I undid an import**: anyone worked on since the import is kept on purpose.
- **Send from Outlook is greyed out**: connect Outlook in Settings, fill the **To** box, and fill anything still in {{curly brackets}}.
- **The record arrows are greyed out**: you opened the contact directly rather than from the list, so there is no list to step through.
