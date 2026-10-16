# UI audit - 16 Oct 2026

Every page opened as an administrator at 1440 x 900 on the demo data (51 pages: 44 lists and screens plus one of each
detail page). Screenshots: `audit/sheet_00.jpg` … `sheet_12.jpg` (four pages each, labelled with the address).
**Round 1 done (17 Oct):** rename, Brain character, sidebar, Calendar & Reminders, Sales overview tabs, empty states, the small fixes. Left for round 2: one page header everywhere (big five #3), company and contact pages (#2), Automation settings split, Contacts header buttons, duplicate title filters, tips/tour/celebrations.

## The big five

1. **The sidebar is too long and mixed.** 30 links in four groups. "Platform" mixes daily work (Contacts, Calendar)
   with admin things (Feedback). Sales Orders alone opens to 13 links. "BMI Brain" holds Today, Review Queue, Ask AI,
   Automations Hub and Data Health - mostly admin pages. A salesperson has to scan past things they never use.
2. **Two different looks.** The company and contact pages are still in the old style (a key/value grid full of "—",
   tabs and a record pager across the top, raw labels like "onboardhospitality"), while Sales Orders, Editorial and
   the Brain pages use the newer cards and headers. These are among the pages clients and staff open most.
3. **Pages don't share one header.** Some have a small coloured label above the title ("CALENDAR & TASK LIST",
   "AUTOMATIONS · SETTINGS"), some don't. Some have breadcrumbs, some a "← back" link, some nothing. Titles swap
   between names ("Companies", "Invoicing") and sentences ("Tune every scan", "Everything waiting on you", "What the AI
   calls are costing", "Keep the screens simple"). Width changes too: Automations pages and Settings sit in a narrow
   column, the rest use the full width.
4. **Things that repeat each other.** Sales Orders "Overview" and "Dashboard" both open with Booked / Invoiced / ... for
   the same year. "All items" and "Bookings" sound like the same thing. "Today", "Calendar & Tasks" and "Reminders" are
   three places for "what do I need to do". The "All Titles" switcher in the top bar and the title chips on Contacts,
   Companies, Groups and Calendar filter the same thing twice.
5. **Technical words on screen.** "AI" (29 places), "Gemini/OpenAI", "LLM usage", "tokens", "Scanners", "SALES-012/013",
   "Email signals (temporary viewer) … throwaway page", "add the Gemini key" on the chat page, and raw database names
   ("onboardhospitality") on Companies. CLAUDE.md says no system names on screen.

## Page by page

| Area | What I saw | Suggested fix |
|---|---|---|
| Home (/) | Title "Sales & Editorial Brain" under "BMI PUBLISHING INTELLIGENCE"; three database cards + "Add database"; counts; overnight activity | Becomes the Brain's home: greeting + "3 things for today", then the counts and overnight activity. Database cards move to Settings |
| Contacts | Six buttons in the header (Import, Copy emails, Bulk update, Export, Mail merge, Add contact); a long help paragraph under the search | Keep "Add contact" and "Import"; the rest in a "More" menu or as actions on ticked rows; help paragraph into an InfoHint |
| Companies | Gate Gourmet listed twice (data), Source column shows "onboardhospitality" next to "OnBoard Hospitality" | Show the database's display name everywhere; same header as Contacts |
| Company / contact page | Old layout (see big five #2); "2 issues" warning from a button that isn't a real button | Rebuild in the new card style; fix the warning |
| Calendar & Tasks, Reminders, Today | Three separate pages, three empty states | One "My day" with tabs (To do · Calendar · Reminders), or at least one shared header and empty state |
| Call notes | Two tabs; long "Your calendars" block on top | Fine; tidy the header |
| Mail merge, Email templates | Good; "Act!'s Output to" in the step text | Remove the old Act! reference |
| Sales Orders | 13 links | Main: Overview, Bookings, Proposals, Rate card, Editions, Invoicing, Commissions. Under "More": All items, Renewals, Weekly summary, Costs & profit, Compare, Dashboard (or merge it into Overview) |
| Bookings | "1 issue" warning: the page asks for the Xero invoice codes, which only Accounts may read (403) | Don't ask unless the person is Accounts |
| All items | 79 buttons, 3,600 px tall; the floating Ask/Feedback buttons sit over the Status column | Floating buttons need a safe area (see below) |
| Rate card (brand) | 183 buttons ("Looks right" on every row) | Fine for now - it's a working screen; "I've checked them all" already exists |
| Proposal page | 3,800 px tall | Fine; it's an editor |
| Automations Hub | Clear | Admin-only group in the sidebar |
| Scanners & Settings | Jargon ("Scanners", "AI usage & cost") | "Automations" and "Brain usage" |
| Automation settings | 10,700 px, 168 buttons, one long column | Split by area with a side index (Xero, Reminders, Sales Orders, …), or tabs |
| LLM usage | "What the AI calls are costing", "Gemini/OpenAI", "tokens" | "Brain usage", plain words, admin only |
| Email signals | "temporary viewer … throwaway page" | Hide from the menu, or remove |
| Ask AI (/brain) | "Ask AI"; shows "add the Gemini key" | "Chat with the Brain"; "The Brain isn't switched on yet - an administrator can turn it on in Settings." |
| Settings | "How the app behaves for you"; Team & access and Sections at the top for everyone | Personal settings first; admin settings in their own group |
| Feedback | Fine | Move to the bottom of the sidebar (next to Settings) |
| Empty states | Plain one-line text ("No groups yet — create one…", "No reminders.") in different styles | One empty-state pattern with the Brain and one action button |

## Small things everywhere

- The floating "Ask AI" and "Feedback" buttons cover the bottom-right of tables and lists. Proposal: one floating
  Brain button; Feedback moves into its menu (or the sidebar footer), and pages get bottom padding so nothing hides
  behind it.
- The user menu at the bottom of the sidebar overlaps the last links when the list is long.
- Notification bell, "Log or schedule" and the title switcher are all in the top bar - fine, but the switcher should be
  the only title filter (remove the duplicate chips) or the chips should follow it.

## Proposed sidebar

```
Home                     (the Brain's greeting, today's 3 things, counts)
My day                   (To do · Calendar · Reminders)
Call notes

CLIENTS
  Contacts · Companies · Groups

SALES
  Overview · Bookings · Proposals · Rate card · Editions · Invoicing · My commission
  More ▸ All items · Renewals · Weekly summary · Costs & profit · Compare editions

EDITORIAL
  Editorial plan

OUTREACH
  Mail merge · Email templates

THE BRAIN
  Chat with the Brain · Review Queue
  Automations · Data health        (administrators and data managers only)

──────────
Feedback · Settings · (you)
```

Same sections as today (so Settings > Sections keeps working); fewer items open at once.

## Order of work (after sign-off)

1. Rename AI → Brain (text, help guides, assistant's name, coverage test).
2. Character component + first placements (button, chat, empty states, errors, loading, login).
3. Sidebar regroup + one page header everywhere.
4. Company and contact pages in the new style.
5. Merge/rename the repeated pages (Overview/Dashboard, Today/Calendar/Reminders) - only what you agree to.
