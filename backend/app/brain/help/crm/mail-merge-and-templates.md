---
title: Mail merge and email templates
screens: ["/mail-merge", "/mail-merge/[id]", "/mail-merge/history", "/mail-merge/templates", "/mail-merge/templates/new", "/mail-merge/templates/[id]"]
summary: Send one personalised email to many people from your own Outlook, or make Word letters, address labels or a data file; follow a mailing as it sends; and keep the team's email templates.
sources: ["frontend/src/app/(app)/mail-merge/page.tsx", "frontend/src/app/(app)/mail-merge/[id]/page.tsx", "frontend/src/app/(app)/mail-merge/history/page.tsx", "frontend/src/app/(app)/mail-merge/templates/page.tsx", "frontend/src/app/(app)/mail-merge/templates/new/page.tsx", "frontend/src/app/(app)/mail-merge/templates/[id]/page.tsx", "frontend/src/components/mail-merge/mail-merge-wizard.tsx", "frontend/src/components/mail-merge/merge-progress-controls.tsx", "frontend/src/components/mail-merge/templates-library.tsx", "frontend/src/components/mail-merge/load-act-templates-button.tsx", "frontend/src/components/mail-merge/template-editor.tsx", "frontend/src/components/mail-merge/email-from-template.tsx", "frontend/src/components/mail-merge/rich-email-editor.tsx", "backend/app/api/routes/messaging.py", "backend/app/services/mail_merge.py", "backend/app/automations/messaging_jobs.py", "backend/app/core/config.py"]
---

## What this screen is for
Mail merge is Act!'s Write > Mail Merge. You write one message with merge fields (the contact's name, company, the issue you're pitching), and BMI Brain makes a personal copy for each person: emails sent from your own Outlook, Word letters, address labels, or a spreadsheet for Word's own merge or Mailchimp. Email templates keep the team's pitches, follow-ups and invitations so the same words can be reused all year.

## What you see
**Mail merge** (four steps down the left: **Output**, **Contacts**, **Message**, **Options**)
- Header buttons **Email templates** and **Sent mail merges**.
- Each step shows a short summary in the step list (for example "240 contacts"). **Back** and **Next** at the bottom.

**A mailing's progress page** (after sending emails)
- A status badge: **Starting**, **Sending**, **Finished**, **Cancelled** or **Paused**, who it's from and where the contacts came from.
- A progress bar and four counts: **Sent**, **Waiting**, **Failed**, **Skipped**.
- A table of every person: **Contact**, **Email**, **Status** (sent, queued, failed or skipped, with the reason).

**Sent mail merges**: your emails and logged letters, newest first, with "<sent>/<total> sent" or "<n> letters" and the status.

**Email templates**: a filter sidebar, a search box, **New template**, **Load Clare's Act! templates** (administrators and data managers only), and a card per template with its brand, title, what it's for, subject, the start of the message, who wrote it and how often it's been used.

## Buttons and controls

### Step 1, Output: E-mail, Letters (Word), Address labels, Merge data
- **E-mail**: personalised emails from your own Outlook. If Outlook isn't connected you see **Connect Outlook** (or **Reconnect** if it has expired). Once connected it says who you're sending as and how many a minute.
- **Letters (Word)**: one letter per contact, one per page.
- **Address labels**: 21 per A4 sheet (Avery L7160 size).
- **Merge data**: a spreadsheet of names and addresses.

### Step 2, Contacts: Current lookup, Ticked contacts, Suggested by the Brain, A group, A company, Specific contacts
Where the contacts come from. Mail merge opens with this already set from wherever you started (a contact's **Write**, a company's or group's **Mail merge**, the Contacts lookup, or ticked contacts). From **Open as a mail merge** on a News campaigns or Mail merge follow-ups card in the Review Queue, it opens as **Suggested by the Brain**, with the people the card found and its drafted email already in step 3, all changeable before you send. **A group** and **A company** let you search for one; **Specific contacts** lets you add people one by one. The table shows everyone, with warnings such as "No email", "Unsubscribed", "Bounced" or "No address".
- Untick anyone to leave them out of this mailing only (they stay in the group). **include all** puts everyone back.
- **Filter this list…** narrows the table; **Untick all** / **Tick all** (or **Untick these** / **Tick these** when filtered) changes many at once.

### Step 3, Message: Template, Update template, Save as new template
- **Template**: start from a saved template, or **— Start from blank —**.
- **Update template** (only on your own templates) saves your new subject and message over it. Its brand, what it's for and note stay as they were.
- **Save as new template**: give it a **Template name**, choose **Share with the team**, and press **Save template**.

### Brand, Title, The issue or event it's about, The feature you're pitching
Appear when the message uses brand figures (print run, email database, readership, website, media pack, video, latest issue) or issue details (issue, date, ad deadline, copy deadline, theme, feature). Choose the brand and the issue, and type the feature. Anything still empty is listed under "Still to fill in".

### Subject and Message
Write the email. Click a merge field button under "Insert into subject" or "Insert into message" to drop it in where your cursor is. {{first_name|there}} means "use 'there' if the contact has no first name". The formatting bar has **Bold**, **Italic**, **Underline**, yellow, green and blue highlights, red, blue and green text, **Bullet list**, **Numbered list**, **Add a link** and **Clear formatting**. Letters are plain text. (The table and picture buttons - **Insert a table**, **Add a row**, **Add a column** and **Insert a picture** - only appear in the proposal editor; see the Proposals guide.)

### Preview, Previous contact, Next contact
The preview shows the email exactly as one person will get it. Step through people with **Previous contact** and **Next contact**. Unknown merge fields are flagged so you can fix the spelling.

### Step 4, Options
- **Record history** (email): **Subject and message**, **Subject only**, or **Don't record**. For letters: **Record a "Letter Sent"** with a **Regarding** line, or **Don't record**.
- **Copies**: **Cc (on every email)** and **Bcc (on every email)**.
- **Attachments**: **Attach a file**, up to 3 MB in total. The X removes one.
- **Contacts who can't be emailed**: **Skip them**, or **Make Word letters for them** (downloads straight after the emails are queued).
- **Include unsubscribed and bounced contacts**: off by default. Only for essential, non-marketing messages, such as an invoice query.
- **File type** (merge data): **Excel (.xlsx) - for Word's own mail merge** or CSV for Mailchimp.
- A summary says how many people it's for and roughly how long it takes to send.

### Send a test to myself
Sends one copy (as the person in the preview) to your own mailbox, with "[TEST]" in front of the subject.

### Send <n> emails, Send now
**Send <n> emails** asks you to confirm ("Send <n> emails?"); **Send now** queues them and opens the progress page. **Not yet** goes back.

### Create <n> letters, Create labels, Download merge data
Makes and downloads the Word file or spreadsheet straight away.

### See earlier mail merges
Opens Sent mail merges.

### Cancel the rest, Cancel - don't send to the other <n>, Resume sending, Retry <n> failed
On the progress page. **Cancel the rest** stops anything not yet sent. On a paused mailing the same button reads **Cancel - don't send to the other <n>**: use it when you've decided not to resume, so the people still waiting are never emailed. **Resume sending** restarts a paused mailing (after you reconnect Outlook). **Retry <n> failed** tries the failed ones again.

### Letters for the <n> without email
On the progress page: a Word file of the same message as letters for everyone skipped for having no email address.

### Sent mail merges, Mail merge, New mail merge
Links back to Sent mail merges and Mail merge, and to a new mail merge.

### Email templates: search and filters
Search by name, words in the email or who wrote it. Filter by **Brand**, **What it's for**, **Needs a check** and **Whose** (**Only mine**). A yellow note says how many templates were brought over from Act! and still need reading through.

### Email someone
Opens "Email from a template" for one person: choose **Who to**, pick **Which issue or event** and **The feature you're pitching** if the template uses them, check **To**, **Copy to (optional)**, **Subject** and the message, then **Send from Outlook** (noted on their history) or **Copy**.

### Load Clare's Act! templates
Administrators and data managers only. Adds the Selling Travel sales emails Clare sent from Act! to the library, shared with the team and marked "needs a check" so someone reads each one before it's used. It asks you to confirm first (**Yes - load the templates** or **Not now**), then says how many it added. Templates already in the library are skipped, so pressing it again adds nothing twice and changes nothing. It also fills in any blank Selling Travel figures (print run, email database, readership, video, media pack) in the editorial plan.

### Change, Copy, New template
**Change** (only if you wrote it, or you're an administrator or data manager) opens the template to edit. **Copy** starts a new template from it, named "<name> (my copy)" and private to you. **New template** starts from blank.

### The template page: Name, Brand, Title (optional), What it's for, Everyone can use it, Note for the team (optional), Subject, Message
Fill in the details, write the email and insert merge fields from three groups: The contact, The brand (from its settings) and The issue (chosen when you send). "How it will look" previews it; choose a title and issue to see real dates and features. **Save** saves and goes back to the list. **Cancel** asks first if you have unsaved changes. **Delete** (existing templates) asks to confirm.

## How it works
- Emails go from your own connected Outlook account, a few at a time (25 a minute by default), and appear in your Sent Items. You can leave the page; you get a notification when it's finished, or if it pauses.
- A mailing pauses ("Paused") if your Outlook connection stops working. Reconnect in Settings > Email, then press **Resume sending**.
- One mailing can go to at most 5,000 contacts. For bigger mailings, use **Merge data** and Mailchimp.
- People with no email, who unsubscribed or whose email bounced are skipped and listed as "Skipped" with the reason, unless you ticked **Include unsubscribed and bounced contacts** (then only people with no email are skipped). Labels leave out anyone without an address.
- With **Record history** on, each sent email adds an "E-mail Sent" entry to that person's history; letters add "Letter Sent". Labels and merge data are not recorded.
- Brand figures come from each brand's settings in the editorial plan; issue details come from the issue you choose. A mailing that uses them with nothing to fill them is refused with a plain reason.
- Templates you don't share are only visible to you. Shared ones can be used by everyone, but only the person who wrote them (or an administrator or data manager) can change or delete them. Saving a template in the template library marks it as checked (updating it from a mail merge doesn't). Each send records that the template was used.
- Sent mail merges lists only your own mailings.

## Common questions
**Q: How do I email everyone in a group?**
A: Open the group and press **Mail merge**. Choose **E-mail**, press **Next**, untick anyone to leave out, **Next**, pick a template or write the email, **Next**, check the options, press **Send a test to myself**, then **Send <n> emails** > **Send now**.

**Q: How do I personalise the greeting?**
A: In the message, click the salutation or first name field button. Add a fallback like {{first_name|there}} for people with no first name.

**Q: Can I stop a mailing once it's started?**
A: Yes. Open it from **Sent mail merges** and press **Cancel the rest** (on a paused mailing: **Cancel - don't send to the other <n>**). Anything already sent stays sent.

**Q: Some people have no email address. Can I still reach them?**
A: In step 4 choose **Make Word letters for them**, or afterwards press **Letters for the <n> without email** on the progress page.

**Q: How do I attach the media pack?**
A: In step 4 press **Attach a file**. Files must add up to 3 MB or less; for a bigger media kit, put a link in the message.

**Q: How do I print address labels?**
A: Choose **Address labels**, pick the contacts, skip to step 4 and press **Create labels**. Print the Word file on Avery L7160 sheets.

**Q: How do I make a template the whole team can use?**
A: Email templates > **New template**, fill it in, keep **Everyone can use it** ticked, and press **Save**.

**Q: Someone else's template needs a change. Can I edit it?**
A: Only its author, administrators and data managers can. Press **Copy** to make your own version instead.

## If something doesn't work
- **Send <n> emails is greyed out**: connect Outlook first (Settings > Email), and make sure at least one person can be emailed.
- **Next is greyed out on Message**: an email needs a subject and a message, and every merge field must be one we know (check the spelling of anything flagged).
- **"This email uses details that aren't filled in yet"**: choose the brand and the issue, type the feature, or add the figures to the brand's settings in the editorial plan.
- **"A mail merge can go to at most 5,000 contacts"**: narrow the list, or use **Merge data** and Mailchimp.
- **"Attachments add up to more than 3 MB"**: remove a file or use a link.
- **The mailing says Paused**: your Outlook connection expired. Reconnect it in Settings > Email, then press **Resume sending**.
- **"Only the template's owner (or an admin) can change it - save a copy instead."**: press **Copy** on the template.
- **Update template isn't there**: you can only update templates you wrote. Use **Save as new template**.
- **Only the first 1,000 people show in step 2**: they're all included; use **Filter this list…** to find someone.
