---
title: Automation settings
screens: ["/automations/settings"]
summary: Every switch and number that controls the Brain's automations - what each one changes, what it starts at, and who can change it.
sources: ["frontend/src/app/(app)/automations/settings/page.tsx", "frontend/src/components/automation-setting-field.tsx", "backend/app/automations/settings_registry.py", "backend/app/automations/runtime_settings.py", "backend/app/core/config.py", "backend/app/api/routes/automations.py"]
---

## What this screen is for
Automation settings holds every setting for the background automations: which ones are switched on, which inboxes they read, how far back they look, how many cards they make per run, and the business rules for bookings and reports. Open it from **Scanners & Settings** > **Automation settings**.

## What you see
- A breadcrumb back to **Automations Hub** and **Scanners & Settings**, and **View Brain usage & cost →** on the right.
- On the left, the list of areas (for example "Deliverability & Out-of-Office"), each with how many settings it has, and **All areas** at the bottom. Click an area to see just its settings; **All areas** shows every one on one page.
- One card for the area you picked.
- Each setting has its name, an (i) to hover over for a description, and a **Customized** badge when it differs from its starting value. Then:
  - a tick box saying **Enabled** or **Disabled**, or
  - a number or text box with a **Save** button.
- Administrators can change settings. Data managers see them read-only: "Only administrators can change them - ask one if something needs adjusting."

## Buttons and controls
### The tick box (Enabled / Disabled)
Saves straight away. You'll see "<setting> updated".

### Save
For number and text settings. It becomes clickable once you change the value. Lists of addresses are separated by commas. A number box that is empty or holds something that isn't a usable number can't be saved: a short note under it says what to fix ("Enter a number.", "Enter a whole number.", or the lowest or highest number allowed).

### Reset to default (<value>)
Shown next to a **Customized** setting. It puts the starting value back. The brackets show that value: On or Off for a tick box, the number for a number setting, or the text in quotes.

### View Brain usage & cost →
Opens the Brain usage & cost page.

Below, "Starts at" is the value the Brain ships with. Your server can set a different starting value, so trust the **Reset to default** label if they differ. Times are UTC.

### Xero
| Setting | What it changes | Starts at |
|---|---|---|
| Xero invoice sync | Copies sales invoices from Xero every hour (read-only), so bookings show whether they're paid. | On |
| Xero invoice matching | Every hour, finds the booking each new Xero invoice belongs to. | Off |
| Fill in clear matches automatically | On: a clear match (same client, same amount, sensible timing, no close rival) is linked without asking. Off: every match waits for a person. | On |
| Most invoices sent for review per run | Most "Invoice to booking" cards made in one run. | 60 |

### Reminders & Notifications
| Setting | What it changes | Starts at |
|---|---|---|
| Reminders fire | Every 5 minutes, turns reminders that are due into bell notifications. | On |
| Email notifications | Also emails notifications from the automation mailbox. | On |
| Automation mailbox | The address automatic emails come from, e.g. automation@bmipublishing.co.uk. Sign in as that mailbox under Settings > Email to connect it. Empty means in-app only. | Empty |
| Mail merge sending | Sends queued mail merges from each person's own Outlook. | On |
| Mail merge emails per minute | Per sender, 1 to 30. Microsoft allows 30 a minute, so keep it below that. | 25 |

### Deliverability & Out-of-Office
| Setting | What it changes | Starts at |
|---|---|---|
| Mailbox monitoring active | Switches on the scan for bounces, out-of-office replies and "has left" replies. | Off |
| Monitored inboxes | Which inboxes that scan reads, separated by commas. | Empty |
| Initial scan lookback (minutes) | How far back the first read of a new inbox goes. 1440 = one day. | 1440 |
| Max out-of-office analyses per cycle | Most auto-replies the Brain checks per run. The rest wait for the next run. | 25 |

### Duplicate Resolution
| Setting | What it changes | Starts at |
|---|---|---|
| Duplicate detection active | Switches on the weekly duplicate contact scan. | Off |
| Match sensitivity threshold (0.0–1.0) | How alike two contacts must be before they're suggested. Higher means fewer, surer suggestions. | 0.55 |
| Max duplicate pairs queued per run | Most duplicate cards made per run. | 30 |
| Contacts evaluated per run | How many contacts each run compares. The next run carries on from there. | 500 |

### Follow-up Engine
| Setting | What it changes | Starts at |
|---|---|---|
| Follow-up queue active | Switches on drafting follow-ups for due and overdue activities. | Off |
| Overdue lookback window (days) | How many days back to look for activities not done yet. | 14 |
| Upcoming lead window (days) | How many days ahead to draft follow-ups early. | 1 |
| Max follow-up drafts per run | Most follow-up cards per run. | 40 |

### Proposal Requests
| Setting | What it changes | Starts at |
|---|---|---|
| Spot proposal requests | Every 10 minutes, reads the inboxes below for emails asking for prices, a media pack or a proposal, and drafts a reply for that salesperson. | Off |
| Inboxes to read | Salespeople's addresses, separated by commas. Each card goes only to the inbox's owner. | Empty |
| First look back (minutes) | How far back the first read of a newly added inbox goes. | 1440 |
| Most emails the Brain checks per run | Cap on how many the Brain checks per run. The rest wait. | 30 |
| Weekly check of example links | Every Monday, checks the links in the proposal examples library and flags broken ones. | On |

### Press Releases
| Setting | What it changes | Starts at |
|---|---|---|
| Read forwarded press releases | Every 15 minutes, reads the inboxes below for press releases the editors forward, finds who to contact and drafts a media kit introduction for the publisher. Nothing is sent until they press Send. | Off |
| Inboxes to read | The addresses the editors forward releases to, separated by commas. | Empty |
| First look back (minutes) | How far back the first read of a newly added inbox goes. | 1440 |
| Most emails the Brain checks per run | Cap on how many the Brain checks per run. The rest wait. | 30 |

### Subscription Changes
| Setting | What it changes | Starts at |
|---|---|---|
| Read the subscriptions inbox | Every 10 minutes, reads the inboxes below for readers unsubscribing, subscribing, changing their address or details, switching title or between print and digital, or asking about their copy. Each becomes a card; nothing changes until someone presses its button. | Off |
| Inboxes to read | Addresses readers write to about their subscription (such as the enquiries inbox), separated by commas. | Empty |
| First look back (minutes) | How far back the first read of a newly added inbox goes. | 1440 |
| Most emails the Brain checks per run | Cap on how many the Brain checks per run. The rest wait. | 40 |

### Email Summaries & Commercial Signals
| Setting | What it changes | Starts at |
|---|---|---|
| Email exchange logging active | Switches on reading sales conversations. It saves a summary note on the contact once a conversation goes quiet, and picks out budgets, renewals, call-backs, personal occasions and "no thanks". | Off |
| Monitored rep inboxes | Salespeople's mailboxes to read, separated by commas. | Empty |
| Max thread participants | Skips emails with more people on them than this (group emails). | 3 |
| Minimum message length | Skips messages shorter than this many characters ("Thanks!"). | 40 |
| Initial lookback window (minutes) | How far back the first read goes. | 1440 |
| Internal BMI email domains | Addresses treated as colleagues, so internal emails are skipped. | bmipublishing.co.uk, onboardhospitality.com, sellingtravel.com |
| Signal confidence threshold (0.0–1.0) | How sure the Brain must be before it keeps a budget, renewal or call-back. | 0.5 |
| Thread quiescence window (hours) | Hours of quiet before a conversation counts as finished and gets its summary note. | 24 |

### Inbound Lead Capture
| Setting | What it changes | Starts at |
|---|---|---|
| Inbound lead capture active | Switches on spotting new people who email the enquiry mailboxes. | Off |
| Enquiry mailboxes (mailbox:database) | Each inbox and which database its leads go to, e.g. enquiries@bmipublishing.co.uk:prospects. Use "*" for a shared inbox. The reviewer then picks the database. | Empty |
| Max thread participants | Skips group emails with more people than this. | 3 |
| Minimum email length | Skips very short messages. | 30 |
| Initial lookback (minutes) | How far back the first read goes. | 1440 |
| Max inquiries analyzed per run | Most emails the Brain checks per run. | 40 |

### Notifications & Alerts
| Setting | What it changes | Starts at |
|---|---|---|
| Microsoft Teams webhook URL | Optional Teams channel address. Business card batch results, behind-last-cycle alerts and the weekly summary are posted there. | Empty |

### Commercial Triggers & Renewals
| Setting | What it changes | Starts at |
|---|---|---|
| Commercial trigger scan active | Switches on turning budgets, renewal dates and promised call-backs from emails into follow-up cards. | Off |
| Opportunity lead time (days) | How many days before the date the card appears. | 14 |
| Undated signal follow-up delay (days) | For one with no date: how many days after it was spotted the card appears. | 3 |
| Max commercial triggers queued per run | Most cards per run. | 25 |

### Personal Touchpoints
| Setting | What it changes | Starts at |
|---|---|---|
| Personal touchpoints active | Switches on reminders for personal occasions (back from leave, birthdays, anniversaries). | Off |
| Advance notice window (days) | Days before the occasion the card appears. 0 = on the day. | 0 |
| Undated touchpoint delay (days) | For one with no date: days after it was mentioned. | 1 |
| Max touchpoints queued per run | Most cards per run. | 25 |

### Morning Queue Prioritization
| Setting | What it changes | Starts at |
|---|---|---|
| Urgency ranking weight (0.0–1.0) | How much being due or overdue counts when ordering Today. | 0.85 |
| Deal value ranking weight (0.0–1.0) | How much a linked opportunity's value counts. | 0.15 |
| Maximum deal value threshold (£) | Opportunities worth this or more count as top value. | 10,000 |

### Brain usage & cost
| Setting | What it changes | Starts at |
|---|---|---|
| Max retries per call | How many times a request to the Brain is retried after a temporary error. 0 = no retries. | 3 |
| Retry base delay (seconds) | Wait before the first retry. It doubles each time. | 2 |
| Min delay between calls in one scan (seconds) | A gap between requests to the Brain, so the provider doesn't refuse a burst. | 1.1 |
| Gemini input cost ($ / 1M tokens), Gemini output cost ($ / 1M tokens) | Prices used for the cost page only. They never change what the automations do. | 0.75 / 3.75 |
| OpenAI input cost ($ / 1M tokens), OpenAI output cost ($ / 1M tokens) | The same, for OpenAI. | 0.15 / 0.60 |
| Per-model cost overrides (JSON) | An exact price per named model, checked before the prices above. Leave the format as it is. | One Gemini model at 0.75 / 3.75 |

### Sales Order Register
| Setting | What it changes | Starts at |
|---|---|---|
| Client matching active | Daily, links order register clients to CRM companies. Exact names are linked by themselves; close ones are sent for review. | Off |
| Max match suggestions per run | Most "same company?" cards per run. | 50 |
| Uninvoiced booking scan active | Weekdays, flags booked items with no invoice number once the issue is out or the event has run. | Off |
| Grace period after publication (days) | Days after publication before flagging. | 7 |
| 'Remind me later' delay (days) | How long **Not yet - remind me later** hides a booking. | 7 |
| Max uninvoiced bookings flagged per run | Most cards per run. | 50 |
| Save the sale active | Every 30 minutes, drafts a reply when a client says no by email. Needs email exchange logging. | Off |
| Most save-the-sale drafts per run | Most cards per run. | 25 |
| Publishers can change their own prices | Off: only administrators and data managers edit the rate card. On: each brand's publishers can edit their brand's prices. | Off |
| Accounts check on confirmed bookings | A confirmed booking goes to Accounts to check before it's invoiced. A checked booking that changes is checked again. | On |
| Confirmation waits for the check | On: the confirmation can't be sent until Accounts say **Looks right**. Off: salespeople send it themselves. | Off |
| Only accounts can change checked bookings | After the check, salespeople request changes instead of editing. Only works once someone has the Accounts permission. | On |
| Accounts are away | While Accounts are on holiday, administrators can pass checks, approve changes and unlock bookings, and get Accounts' notifications. Switch it off on their return. | Off |
| Ready to invoice reminders | Accounts get a Ready to invoice card when items reach their invoice date. | On |
| Days after it runs, for "after it has run" | For clients invoiced after the item runs: days after. | 3 |
| Tell accounts about every new booking | Accounts get a bell note for each new booking, and the confirmation is emailed to the Accounts addresses from the automation mailbox. | On |
| Reminders for items still to be allocated | Salespeople get a card when a booking has items with no issue and the decide-by date (or next booking deadline) is close. | Off |
| Allocation reminder lead time (days) | How many days before that date. | 14 |
| Order register check when an issue goes to press | Accounts get one card per issue listing anything in its register worth a look. | Off |
| Days after the copy deadline | When that card appears. | 2 |
| Renewal outreach active | Weekdays, drafts renewal emails for last year's advertisers who haven't rebooked. | Off |
| Renewal lead time (days) | Days before the anniversary of last year's booking. | 60 |
| Max renewals drafted per run | Most renewal cards per run. | 25 |

### The Brain
| Setting | What it changes | Starts at |
|---|---|---|
| Brain search index | Every 15 minutes, adds new notes, history, activities and call notes to what Ask the Brain can search. It only reads. | On |

### Call notes
| Setting | What it changes | Starts at |
|---|---|---|
| Shared calendar and automatic notetaker | Every 3 minutes, reads connected calendars into the shared calendar and sends BMI Notetaker into meetings that should be recorded. | On |
| Record internal meetings | Also record meetings with only BMI people. | On |
| Record meetings marked private | Whether the notetaker joins private meetings. They're always hidden from others on the calendar. | Off |
| Join this many minutes early | 0 to 10. | 1 |

### Editorial Plan
| Setting | What it changes | Starts at |
|---|---|---|
| Advertising deadline reminders | Each morning, tells a brand's publishers and salespeople an advertising deadline is coming, with how many of last year's advertisers haven't rebooked. | Off |
| Remind this many days before | Separated by commas. One reminder at each point. | 14, 7, 1 |

### Management Reporting
| Setting | What it changes | Starts at |
|---|---|---|
| Behind-last-cycle alerts active | Weekdays, alerts leadership when an issue or event has booked far less than its equivalent last cycle. | Off |
| Weekly management summary active | Monday mornings, writes the one-page brief. | Off |
| Show sales by financial year | Sales overview and dashboard open on the financial year. You can still switch on the page. | On |
| Financial year starts in month (1-12) | 7 = July, so the year runs July to June. | 7 |
| Behind / ahead threshold (0.0-1.0) | How far behind or ahead counts. 0.25 = 25%. | 0.25 |
| Minimum comparison value (£) | Only compare when last cycle had at least this much booked at the same point. | 2,000 |
| Minimum comparison bookings | ...and at least this many bookings. | 3 |
| Alert & summary recipients | Login emails, separated by commas. Empty = every active administrator. | Empty |
| Alert cooldown (days) | The same issue isn't alerted again within this time. | 14 |

## How it works
- A change applies on the setting's next use: a scanner's next scheduled run or **Run now**. No restart is needed.
- Switching a scanner off stops its timetable only. **Run now** still works on a switched-off scanner.
- Only administrators can change settings. Data managers see them read-only. Salespeople can't open this page.
- **Reset to default** removes your change, and the setting goes back to the server's starting value.

## Common questions
**Q: How do I switch on bounce scanning?**
A:
1. Type the inbox addresses in **Monitored inboxes** and press **Save**.
2. Tick **Mailbox monitoring active**.
3. On Scanners & Settings, press **Run now** on **Bounce & OOO mailbox scan** to try it.

**Q: How do I start reading a salesperson's inbox for proposal requests?**
A: Add their address to **Inboxes to read** and press **Save**, then tick **Spot proposal requests**.

**Q: Samantha is on holiday. Who checks bookings?**
A: Tick **Accounts are away**. Administrators can then pass checks and approve changes. Untick it when she's back.

**Q: Too many duplicate suggestions are wrong.**
A: Raise **Match sensitivity threshold (0.0–1.0)**, for example to 0.7, and press **Save**.

**Q: Where do automatic emails come from?**
A: The **Automation mailbox**. Sign in to Settings > Email as that mailbox to connect it.

**Q: How do I stop the first run flooding the queue?**
A: Lower the "Max … per run" setting for that automation. The rest follow on later runs.

**Q: Our financial year starts in April.**
A: Set **Financial year starts in month (1-12)** to 4 and press **Save**.

## If something doesn't work
- **The tick boxes are greyed and there's no Save**: you're a data manager. Ask an administrator.
- **"Only administrators can change automation settings."**: the same reason.
- **Save stays greyed**: you haven't changed the value yet.
- **"<setting> must be at least …" / "must be at most …"**: the number is outside the allowed range. For example, **Mail merge emails per minute** must be 1 to 30, and **Financial year starts in month (1-12)** must be 1 to 12. Don't leave a number box empty.
- **Text settings aren't checked**: a mistyped address list or cost override is saved as typed. Check commas, and the format of **Per-model cost overrides (JSON)**, carefully.
- **I switched a scanner on but nothing happened**: it waits for its next scheduled run. Press **Run now** on Scanners & Settings to run it now.
- **Email settings on but nothing read**: the inboxes must be ones the Brain has permission to read. Check the scanner's last run on Scanners & Settings for an error.
