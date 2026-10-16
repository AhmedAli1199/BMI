---
title: How each automation works
screens: ["/automations/review", "/automations/[workstream]", "/automations/engine"]
summary: One entry per automation - what sets it off, how often it runs, what it reads, which Review Queue card it makes, what each button on that card does, and which setting switches it on.
sources: ["backend/app/automations/workstreams.py", "backend/app/automations/scheduler.py", "backend/app/automations/bounce_handling.py", "backend/app/automations/departure.py", "backend/app/automations/dedupe.py", "backend/app/automations/business_card.py", "backend/app/automations/returned_copy.py", "backend/app/automations/inbound_capture.py", "backend/app/automations/email_summary.py", "backend/app/automations/signal_triggers.py", "backend/app/automations/personal_touchpoints.py", "backend/app/automations/followup_queue.py", "backend/app/automations/proposal_requests.py", "backend/app/automations/call_notes.py", "backend/app/automations/save_the_sale.py", "backend/app/automations/sales_orders.py", "backend/app/automations/xero_matching.py", "backend/app/automations/invoice_due.py", "backend/app/automations/allocations.py", "backend/app/automations/sor_checks.py", "backend/app/automations/order_checks.py", "backend/app/automations/booking_changes.py", "backend/app/automations/booking_forms.py", "backend/app/automations/editorial_deadlines.py", "backend/app/automations/management_reports.py", "backend/app/automations/messaging_jobs.py", "backend/app/automations/calendar_jobs.py", "backend/app/automations/brain_jobs.py", "backend/app/automations/settings_registry.py"]
---

## What this screen is for
This guide explains every automation behind the Review Queue and the Scanners & Settings page. For each one it covers what sets it off, how often it runs (times are UTC), what it reads, which card it makes, what the card's buttons do, and the setting in Automations > Settings that switches it on. The basic rule: automations suggest, and a person decides. The few things that happen without a person are called out below.

## What you see
- Scheduled automations are listed on **Scanners & Settings** under the scanner names used below (for example **Bounce & OOO mailbox scan**).
- Their cards appear in the **Review Queue** under the card names used below (for example **Ambiguous Delivery Bounces**), and in the workstream pages of the Automations Hub.
- Automations that don't make cards (reminders, mail merge and so on) only show on Scanners & Settings.

## Buttons and controls
### Bounce & OOO mailbox scan (CRM Data Hygiene)
- **When**: every 15 minutes. **Switch**: **Mailbox monitoring active**, with the inboxes in **Monitored inboxes**.
- **Reads**: new mail in those inboxes since the last run. Rule checks pick out bounce notices and auto-replies, and the Brain confirms the doubtful ones. At most **Max out-of-office analyses per cycle** auto-replies are checked per run.
- **Makes** one of four cards. There is only one waiting auto-reply card per person at a time.
- **Ambiguous Delivery Bounces** (the address belongs to a contact; marked Hard or Soft bounce):
  - **Confirm & unsubscribe** marks the contact unsubscribed and adds a "Bounce" note.
  - **Not a bounce, ignore** changes nothing.
- **Unmatched Delivery Bounces** (no contact has that address):
  - **Match to a contact** asks you to pick the contact. It then unsubscribes them and adds a note.
  - **Ignore** changes nothing.
- **Out-of-Office & Handover Notes** (a contact is away, with any replacement they named):
  - **Confirm replacement** asks you to pick the replacement, then adds a "Handover" note to both people.
  - **Create as new contact** asks for **Full name** and optional **Email**. It adds the replacement at the same company, with notes on both.
  - **Temporary leave, ignore** changes nothing.
- **Executive Role Departures** (an auto-reply says the person has left):
  - **Confirm successor** uses the researched candidate. After a confirm step, it adds a "Departure" note to every record of the person who left, and one to the successor.
  - **Assign different contact** lets you pick the successor yourself.
  - **Use general company address** asks for **General company email** and notes it as a stand-in on their records.
  - **Dismiss (contact remains)** asks you to confirm, then changes nothing.
  Departures only add notes. They don't change anyone's email or mark them as left.

### Duplicate contact scan (CRM Data Hygiene)
- **When**: Sundays 03:00. **Switch**: **Duplicate detection active**.
- **Reads**: a batch of contacts each week (**Contacts evaluated per run**), comparing names within the same database. Each pair is scored on company, email, phone, postcode and shared activities. A name match alone never scores 100%.
- **Makes**: **Duplicate Contact Resolution** cards scoring above **Match sensitivity threshold (0.0–1.0)**, up to **Max duplicate pairs queued per run**.
- **Merge records**: pick **Which one do you want to keep?**, then confirm. Notes, history, activities, opportunities, emails, phones, addresses and groups move to the one you keep. The other is marked as merged, not deleted. This can't be undone from the screen.
- **Keep as separate contacts** changes nothing.

### Business card and returned-copy uploads (Business Cards & Photos)
- **When**: someone uses **Upload business card(s)** or **Upload returned copy label(s)**. There is no schedule, and it needs the Brain to read photos.
- **New Business Card Leads** (nobody matches):
  - **Create contact** (optional **Groups to add (comma-separated)**) adds the person with their email, phone and company, joins them to the groups (only approved group names), and notes "Card collected at <show>".
  - **Skip** changes nothing.
- **Business Card Contact Updates** (matches someone already in the CRM):
  - **Apply updated details** saves only the fields that changed (job title, email, phone, company) and notes which.
  - **Log event meeting (keep existing)** only adds a note.
  - **Skip** changes nothing.
- **Returned Print Copies** (a label matched to a contact or company):
  - **Update address** writes the address read from the label onto the record.
  - **Retire (moved/closed)** (optional **Reason**) marks the record retired.
  - **Dismiss (no match)** changes nothing.

### Inbound contact capture scan (Lead & Contact Capture)
- **When**: every 30 minutes. **Switch**: **Inbound lead capture active**, with **Enquiry mailboxes (mailbox:database)**.
- **Reads**: new emails from senders who aren't in the CRM. It skips group emails, bounces, auto-replies, newsletters, very short emails and BMI colleagues. The Brain decides whether it's a real new enquiry and reads the signature.
- **Makes**: **Inbound Lead Capture**, one per sender at a time, with a guessed company and suggested groups.
- **Create contact** asks for **Full name**, and optionally **Job title**, **Company**, **Phone**, **Mobile**, **Groups to add (comma-separated)** and **Subscribe to newsletter**. A shared inbox also asks **Which BMI title does this belong to?**. It adds the contact (and the company if new), the groups, and an "Inbound enquiry" note with the email.
- **Not a lead, ignore** changes nothing.

### Email exchange summary scan (feeds Sales & Follow-ups)
- **When**: every 4 hours. **Switch**: **Email exchange logging active**, with **Monitored rep inboxes**.
- **Reads**: one-to-one conversations between a salesperson and a known contact. The Brain picks out budgets, renewal dates, promised call-backs, personal occasions, and "no thanks" with the reason.
- **Makes**: no cards itself. Once a conversation has been quiet for **Thread quiescence window (hours)**, it writes an "Email exchange summary" note on the contact by itself, without review. What it picks out feeds the next four automations.

### Budget window / renewal trigger scan (Sales & Follow-ups)
- **When**: daily 06:00. **Switch**: **Commercial trigger scan active**.
- **Makes**: a **Commercial Signals** card per budget, renewal date or promised call-back. It appears **Opportunity lead time (days)** before its date, or **Undated signal follow-up delay (days)** after it was spotted if it has no date. Each comes with a drafted follow-up. These also show on **Today**.
- **Approve & log to CRM** opens **Review the draft**, then saves it as a "Follow-up needed" note. Nothing is sent.
- **Dismiss signal** closes it for good.

### Personal touchpoint reminder scan (Sales & Follow-ups)
- **When**: daily 06:00. **Switch**: **Personal touchpoints active**.
- **Makes**: **Personal Touchpoint Reminders** for light personal occasions (back from leave, birthdays, anniversaries), with a warm, no-sales draft. Bereavement and illness are never picked up. These also show on **Today**.
- **Approve & log to CRM** saves the draft as a "Personal touchpoint" note.
- **Skip this occasion** closes it for good.

### Follow-up due scan (Sales & Follow-ups)
- **When**: hourly 07:00–18:00, Monday to Friday. **Switch**: **Follow-up queue active**.
- **Reads**: activities that aren't done yet, linked to a contact or company, due in the last **Overdue lookback window (days)** or the next **Upcoming lead window (days)**.
- **Makes**: **Overdue Follow-ups** with a drafted email. These also show on **Today**.
- **Approve & log to CRM** saves the draft to the record's history and marks the activity done.
- **Defer to next working day** moves the activity to tomorrow (Monday if it's Friday).
- **Dismiss** leaves the activity as it is.

### Proposal requests (Sales & Follow-ups)
- **When**: every 10 minutes. **Switch**: **Spot proposal requests**, with **Inboxes to read**.
- **Reads**: emails that mention prices, rates, a media pack or a proposal. The Brain checks they really are requests, up to **Most emails the Brain checks per run**. Prices come from the rate card and issues from the editorial plan, never from the Brain.
- **Makes**: **Proposal requests**, only for the inbox's owner.
- **Send reply from my Outlook** opens **Review the draft**. It replies in the same thread from your Outlook and notes it on the client.
- **I'll reply myself** closes the card.
- **Make a full proposal** opens the proposal builder with the client (added if new), products and examples ready.
- **Not a proposal request** closes it.

### Call notes (Sales & Follow-ups)
- **When**: the notetaker finishes a recorded call. There is no schedule.
- **Save to history** writes the notes onto the contact's history, plus a reminder for each "to do". The call must be linked to a contact.
- **Not needed** closes it. The notes stay on the call page.

### Revenue & Orders automations (see the Sales Orders "Review cards" guide for their buttons)
| Scanner / trigger | When | Card | Switch |
|---|---|---|---|
| Ready to invoice | Weekdays 07:05 | Ready to invoice (Accounts) | Ready to invoice reminders (on) |
| Items to allocate | Weekdays 07:15 | Items to allocate | Reminders for items still to be allocated |
| Issue gone to press check | Weekdays 06:45 | Issue gone to press (Accounts) | Order register check when an issue goes to press |
| Renewal outreach scan | Weekdays 06:30 | Renewal Outreach | Renewal outreach active |
| Uninvoiced booking scan | Weekdays 07:00 | Uninvoiced Bookings | Uninvoiced booking scan active |
| Order register client matching | Daily 05:30 (exact names link by themselves) | Order Register Client Matching | Client matching active |
| Xero invoice matching | Hourly at :40 (clear matches link by themselves) | Invoice to booking | Xero invoice matching |
| Save the sale | Every 30 minutes, from "no thanks" emails | Save the sale | Save the sale active |
| A booking is confirmed or changed | At once | Booking check (Accounts) | Accounts check on confirmed bookings |
| A salesperson presses Request a change | At once | Booking change (Accounts) | Only accounts can change checked bookings |
| An online booking form is sent in | At once | Online bookings | Set up in Bookings settings |

### Jobs that don't make cards
- **Reminders**: every 5 minutes, turns due reminders into bell notifications. **Reminders fire**.
- **Notification emails**: every 2 minutes, emails notifications from the automation mailbox. **Email notifications**.
- **Mail merge sender**: every minute, sends queued mail merges from each sender's Outlook. **Mail merge sending**.
- **Xero invoice sync**: hourly at :20, copies invoices from Xero. Read-only. **Xero invoice sync**.
- **Shared calendar**: every 3 minutes, reads calendars and books the notetaker. **Shared calendar and automatic notetaker**.
- **Brain search index**: every 15 minutes, updates what Ask the Brain can search. **Brain search index**.
- **Advertising deadline reminders**: daily 07:15, sends bell notes to publishers and salespeople. **Advertising deadline reminders**.
- **Behind-last-cycle alerts**: weekdays 07:15. **Weekly management summary**: Mondays 07:00. Both go to the recipients in Management Reporting.
- **Proposal example links**: Mondays 06:30, flags broken example links. **Weekly check of example links**.

## How it works
- Most scanners are off until an administrator switches them on. **Run now** works even when one is off.
- Card limits per run stop a first run flooding the queue. The rest come on later runs.
- Things done without a person: the email summary note, exact client-name links, clear Xero invoice links (if **Fill in clear matches automatically** is on), notifications and reminders.
- The Brain never supplies prices, dates or figures in drafts. Those come from the rate card, the editorial plan or the order register.

## Common questions
**Q: Why didn't the Brain notice a client's budget email?**
A: **Email exchange logging active** and **Commercial trigger scan active** must both be on, and the salesperson's inbox must be in **Monitored rep inboxes**. The card appears 14 days before the date, or 3 days after an undated mention.

**Q: Does approving a follow-up send the email?**
A: No. **Approve & log to CRM** saves it as a note or in history. Only renewals, save-the-sale and proposal requests send, from your Outlook.

**Q: What happens if I merge the wrong two contacts?**
A: The merge can't be undone from the screen. Check both records with the links before pressing **Merge records**.

**Q: Does unsubscribing a bounce delete the contact?**
A: No. **Confirm & unsubscribe** only marks them unsubscribed and adds a note.

**Q: What does Defer to next working day do?**
A: It moves the activity to the next weekday, and the card comes back then.

**Q: Why do I see the same out-of-office person only once?**
A: The scan keeps one waiting card per person, however many auto-replies arrive.

## If something doesn't work
- **"That contact no longer exists"**: it was merged or deleted after the card was made. Dismiss the card.
- **"No researched candidate is attached to this item"**: use **Assign different contact** instead of **Confirm successor**.
- **"This call isn't linked to a contact yet."**: link it on the call's page, then press **Save to history**.
- **"Connect your Outlook first"**: connect it in Settings > Email, or use **I'll reply myself**.
- **A dismissed duplicate or follow-up came back**: the scans only skip pairs and activities that already have a waiting card. A dismissed duplicate pair can be suggested again on a later sweep. A dismissed follow-up comes back while its activity is still not done. Mark the activity done, or move its date.
- **Unmatched returned-copy label**: there's no way to pick a contact on these cards. Fix the address on the record by hand, then press **Dismiss (no match)**.
