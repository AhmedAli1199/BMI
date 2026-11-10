# Remaining work (as of 10 Nov 2026)

Start here if you're picking up BMI Brain. Read this, then `docs/HANDOFF.md` (rules, business logic, UI rulebook),
then `CLAUDE.md`. Everything is on branch `ui-polish-revamp`.

**Go-live: Friday 4 December 2026.** BMI's testers (Craig and Sally in sales, Shani in data) start the week of
16 Nov. Everything should be built by **27 Nov** so there's a week to fix what testing finds.

**Where Option Two stands:** 44 of 54 automations built, 2 partly built, 8 not started. The full list with a
note for each is `docs/option2-status/index.html` (and its PDF). The same rows, with planned start and due dates,
are on Cybix's delivery tracker (client "BMI"); update both when something moves.

---

## The 10 automations left

| # | ID | Automation | Status | Blocked on | Due |
|---|---|---|---|---|---|
| 1 | CS-009 | Invite people near an event venue | Partly built | Nothing | 10 Nov |
| 2 | CS-010 | Sort the shared enquiries inbox | Partly built | Only which inbox (a setting) | 11 Nov |
| 3 | SALES-016 | Find the right person at a target company | Not started | BMI's job titles; Apollo key | 16 Nov |
| 4 | SALES-017 | LinkedIn profile to work email | Not started | Apollo key | 17 Nov |
| 5 | SALES-018 | Email checking and traffic-light grade | Not started | Apollo key | 18 Nov |
| 6 | SALES-019 | Load verified contacts into the CRM | Not started | Apollo key | 20 Nov |
| 7 | CS-011 | Sort the editors' inboxes | Not started | BMI asking the editors | 20 Nov |
| 8 | CS-008 | Find new audiences for events | Not started | Apollo key; travel-agent job titles | 25 Nov |
| 9 | SALES-024 | Prospect pipeline per project | Not started (on pause) | BMI's brief | 27 Nov |
| 10 | SALES-025 | Pipeline status and chase lists | Not started (on pause) | Same brief | 27 Nov |

If the pipeline brief hasn't arrived by **16 Nov**, tell Matt that 9 and 10 move to just after go-live.

### 1. CS-009 Invite people near an event venue
- **Already there:** Advanced search picks contacts by town, postcode or country and saves a group.
- **To build:** "Everyone within X of the venue". Look up each contact's postcode (and the venue's) with a free
  postcode service (postcodes.io for UK postcodes, no key), and offer it in Advanced search and as a ready mail merge
  for an event in the editorial plan.
- **Agreed with BMI (5 Nov meeting):** default **50 km**, changeable per event. People travel to events by train.
- Cache postcode lookups; contacts without a postcode are listed, not dropped silently.

### 2. CS-010 Sort the shared enquiries inbox
- **Already there:** the shared inboxes are read for new contacts (SALES-011), sign-ups, subscription changes,
  reader questions, press releases and proposal requests, each its own scanner.
- **To build:** one mixed inbox sorted into all of these, plus invitations, "not for us" (people who think BMI is
  the music company) and anything else, as **Outlook categories** (coloured labels, so the email stays in the inbox;
  see below) and/or cards.
- **Agreed (5 Nov):** emails are **not moved** out of the inbox. Categories are the Outlook way to give "views"
  without moving anything. Needs Graph `Mail.ReadWrite` on that mailbox to set categories; check the app
  registration has it.
- The inbox address is a setting. Ask Clare which one (probably enquiries@).

### 3–6. SALES-016 to 019 Finding the right people (one feature in four parts)
- **What BMI wants (5 Nov):** in BMI Brain, a salesperson searches by **company, industry and job title**
  (Craig's example: buy-on-board / retail companies, "head of retail"), sees the people, presses one button to add
  them as contacts (or a group). Emails only, **no phone numbers** (Clare's decision).
- **Data service: Apollo.** BMI agreed one month on the Basic plan (one shared seat). Pricing as of Nov 2026:
  Basic $49/seat/month yearly or about $65 monthly, about 30,000 credits per seat per year. A work email costs 1
  credit; searching is free; a mobile costs 8 (don't use).
- **Not yet confirmed:** whether Apollo's API works on the Basic plan (its docs say API access "depends on your
  plan"). Test with the trial key first: `POST https://api.apollo.io/api/v1/mixed_people/api_search`
  (free, no emails, params `person_titles[]`, `q_organization_domains_list[]`, `organization_locations[]`...) and
  `POST https://api.apollo.io/api/v1/people/match` (1 credit, returns `email` and `email_status`). Header
  `x-api-key`. The account should be in BMI's name; the key goes in an env var on the server (never on a screen).
- **The four parts:**
  1. SALES-016 search: company/industry/title/location filters → list of people (free search).
  2. SALES-017 email: reveal the work email for the people chosen (1 credit each), or from a LinkedIn URL.
  3. SALES-018 grade: traffic light from Apollo's `email_status` (verified = green, guessed = amber, none = red),
     plus our own free checks (`app/services/email_check.py`).
  4. SALES-019 load: on approval, create the contact (and company if new) with a note saying where it came from,
     never duplicating someone already in the CRM (reuse `contact_match` / dedupe logic).
- **Job titles:** Matt and Clare are collecting 2–3 per magazine from the salespeople, in order of usefulness.
  Make them a setting per magazine.
- **Data protection (agreed by Clare: legitimate interest):** the first email to someone found this way must say
  where their details came from and offer an opt-out (UK GDPR Article 14; PECR for sole traders, many of whom are
  travel agents). Record the source on the contact.
- Craig tests this part, so build the screen inside BMI Brain, not just cards.

### 7. CS-011 Sort the editors' inboxes
- **Waiting on BMI:** Matt and Clare are asking the editors (Steve, Bev, April...) whether they want it and which
  folders/categories. Clare expects some resistance.
- **Agreed approach if yes:** categories, not moving emails (same as CS-010); possibly by destination or region
  (Clare's idea); press releases, event invitations, reader letters, personal. The editorial@ shared mailbox may be
  closed down, so it may only be personal inboxes.
- Needs the editors' and IT's OK for the Brain to read those mailboxes.

### 8. CS-008 Find new audiences for events
- **Agreed (5 Nov):** in scope (Matt: "a simple addition if you're in Apollo"). For Selling Travel events
  (travel-agent "client connect" events, e.g. Norwich, Guildford): find travel agents near the venue who aren't in the
  CRM. Job titles: travel agent, travel advisor and similar (BMI to confirm). Many are self-employed (Gmail
  addresses).
- Build on SALES-016 (same search, plus a location radius around the venue, default 50 km) and CS-009.
- Matt's context: a Guildford event had 12 sign-ups until a freelancer spent hours finding agents online; it reached
  60-70. This replaces that work.

### 9–10. SALES-024 and SALES-025 Prospect pipeline
- **On pause until BMI's brief.** Spec text is in `docs/build-spec.txt` (search SALES-024).
- What Matt has said so far (26 Oct): a project has a name, description and type; people come from a previous project,
  last year's advertisers, a group or individuals, with duplicates removed; an option to work only with people who
  replied (Sally's way); an issue's general list, where "revisit in spring" moves someone to a later issue; stages,
  timestamps and history; a subject keyword to link emails. Only Sally keeps a spreadsheet today.
- Reuse: mail merge, `merge_followups.py` (reply detection), `campaign_replies.py` (reply triage),
  `issue_campaigns.py` (who to pitch per issue).

---

## Other open work (not part of the 54)

| What | Notes |
|---|---|
| SOR import 2021–2027 | Clare sent a zip of every year's SOR sheets. Do a trial import locally first (`backend/scripts/refresh_sor.py --source <zip> --dry-run`, then a real run on a test DB), report skipped files, warnings and total mismatches, fix the importer for older layouts, then give Ahmed the live command. The zip must contain one folder per year (`2021/` ... `2027/`). The script stops if anyone has edited bookings in the app (`--force` overrides; only before testers start). The final refresh happens just before go-live. |
| Feedback approval step | From the 26 Oct meeting: suggestions on the feedback board are approved by Matt/Clare before we build them. |
| Help Centre articles and videos | Promised to BMI. Plan in `docs/help-centre-plan.md`. |
| Stova extras | Stova invoice number on a booking, "paid in Stova", no confirmation reminder for bookings made through a form. |
| Delivery tracking (SALES-027) | Shown as built (hand-offs follow each sold item). Discuss with BMI whether that's enough or they want stages, owners and ages per item. |
| Print subscriptions | How BMI records who gets print isn't known, so "unsubscribe" can't stop print copies yet. Ask Clare. |
| Paid email checking | Optional. BMI deciding after asking salespeople about bounce rates. MillionVerifier: 10,000 for $39, 50,000 for $89, credits never expire. |
| Brevo | `BREVO_API_KEY` returns 401 on the server: either the key type (must be an API key `xkeysib-`) or Brevo's IP allow-list. Then set `brevo_title_lists` and delete the temporary Brevo lists page (`backend/app/api/routes/brevo_lists.py`, its line in `main.py`, `frontend/src/app/(app)/automations/brevo-lists/`, its help mention). |
| WordPress sign-up form | Onboard Hospitality digital: its Form Maker form must email sign-ups to the inbox the Brain reads (shown on the Lead & Contact Capture page). Check Clare's web developer did it. |
| Hand-off names | BMI to say which named people get editorial and production hand-offs (Settings in Bookings). |

## Before go-live (4 Dec)
1. Final SOR refresh (2021–2027), then the spreadsheets stop being updated.
2. Fresh Act! migration.
3. Switch on the automations that start off (Automations > Settings): mail merge replies, website stories, issue
   pitch campaigns, and the ones from late October (see `docs/HANDOFF.md` §4.3h3 onwards).
4. Connect the automation mailbox (notes emails and notifications need it).
5. Redeploy (the backend image includes LibreOffice for PDF confirmations).
