# Help Centre - the plan (agreed with Ahmed, 19 Oct; full build waits until BMI's feedback has settled)

Proper help articles for BMI staff, like big software companies have: one article per task, written for people who
aren't technical, with screenshots and links between articles. **Only the pilot is built** (5 articles, the
/help pages); the rest is written once BMI's feedback is in, so the articles describe the app as it is then.

## Why separate from the Brain's guides
`backend/app/brain/help/**` (33 guides, ~71k words) is the Brain's reference: every button on every screen, in screen
order. People don't read that way - they come to do one thing ("send the confirmation"). So the articles are written
around tasks, from the same facts. The guides stay as they are for the Brain; each article lists the guide it came
from, and the Brain's answers can end with "Read the full article".

## Shape
- **In the app at /help** (staff only, follows each person's access: no admin articles for salespeople, hidden
  sections stay hidden). Categories follow the menu: Getting started, Clients, Sales, Editorial, Outreach, The Brain,
  Admin. Search at the top; popular articles for your role.
- **~80-100 short task articles** ("Make a booking", "Send the confirmation", "Pencil a booking in and confirm it
  later", "Set a reminder", "Run a mail merge", "Deal with a bounced email"...), a few **"About…"** overviews (how
  bookings, invoicing and Accounts fit together) and **"Something's not right"** troubleshooting pages. The 17 tutorial
  lessons map onto them; each article can embed its video.
- **Every article the same:** the task as the title + one line on what you'll do; who it's for; numbered steps (one
  action each, exact button names in bold, a screenshot with the button ringed); short Tip / Good to know boxes;
  "What happens next"; "If something's not right"; related articles; "Was this helpful?" (goes to Feedback).
- **Help from where you are:** a small "Help" link on each page opens its article.

## Writing rules (style guide)
Short sentences; "you"; everyday words; say what's on screen ("press **Confirm**"), never how it works inside; no
system names, no "AI" (say "the Brain"); British spelling; at most ~8 steps - longer becomes two articles; one idea per
paragraph; the roles agreed with BMI (the salesperson confirms and sends the confirmation; Accounts check bookings only
for invoicing).

## Screenshots that make themselves
Each step names the page and the thing to ring. A Playwright script (`docs/help-centre/shoot.mjs`, same set-up as
the tutorial recorder: tutorial seed data, Sally Parker, Morning theme, 1440x900) takes the picture, draws the ring and
step number, and saves `frontend/public/help/<article>/<n>.png`. When a screen changes, re-run it - nothing goes stale.

## Checks (when built in full)
Tests like the Brain's help-coverage test: every bold button name in an article exists on screen (ui_map.json); every
related link points at a real article; every step's screenshot exists; every screen has an article. CLAUDE.md rule:
change a screen -> update its article.

## Order
1. **Pilot (done 19 Oct):** /help home + article page, 5 articles with real screenshots - for Ahmed (and Sally) to
   judge tone and layout.
2. After BMI's feedback settles: Sales in full (~30), then Clients, Outreach, Editorial, the Brain, Admin.
3. Search, Help links on every page, "Read the full article" from the Brain, the checks.

## Pilot - where things are
- Articles: `frontend/src/content/help/articles.ts` (typed data, one object per article; `**bold**` and
  `[text](article-slug)` inside text).
- Pages: `frontend/src/app/(app)/help/page.tsx` (home), `frontend/src/app/(app)/help/[slug]/page.tsx` (article),
  `frontend/src/components/help/*`.
- Screenshots: `docs/help-centre/shoot.mjs` -> `frontend/public/help/`.
