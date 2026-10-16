# Video 1 - Making a new booking (Antigravity blueprint)

Checked in the real app on 16 Oct 2026 (tutorial data, signed in as Sally Parker, 1440 x 900). Reference frames are
in `frames/`. Paste everything inside the block below into Antigravity. Run the tutorial seed before every take
(see `../README.md`).

````text
════════════════════════════════════════════════════════════════════
ANTIGRAVITY EXECUTION BLUEPRINT - VIDEO 01: MAKING A NEW BOOKING
════════════════════════════════════════════════════════════════════

──────────────────────────────
1. VIDEO METADATA
──────────────────────────────
Title ............ Making a new booking
Series ........... BMI Brain - Sales Orders, lesson 1 of 17
Audience ......... Salespeople (role: Sales)
Goal ............. The viewer can record a booking the client has agreed: client, contact, one item from the
                   rate card, two issues, then confirm it. Confirming is the salesperson's sign-off that the
                   client said yes; Accounts only check it later, before it's invoiced.
Length ........... 2:47 (14 steps)
Tone ............. Calm, plain, step by step. Teaching only - no selling, no praise of the product.
Voice (TTS) ...... British English, neutral, ~150 words a minute. Say "pounds" in full for money.
App URL .......... http://localhost:3000 (production build: npm run build && npm start)
Viewport ......... 1440 x 900, deviceScaleFactor 2, light theme, browser zoom 100%, sidebar open
Sign-in .......... sally.parker@tutorial.bmi / BMI-tutorial-2026
Before each take . cd backend && DATABASE_URL=.../bmi_demo python -m scripts.seed_tutorials --yes
Ends on .......... The new booking's page (the next lesson, "Sending the confirmation", starts from it)

Golden rules for this video
- The voiceover only names what is visible and highlighted at that moment.
- Every action shows: the state before -> the cursor action -> the change on screen. Hold the change for at
  least 1.2 s before the next move.
- Cursor: glide 600-900 ms with ease-in-out between targets, 150 ms press, then 250 ms pause. Typing: 90 ms per
  letter.
- Callout archetypes never repeat in two steps in a row (order used: D A B A C A C B C A B A C D).
- Callout text never repeats the voiceover word for word.

Callout archetypes (as defined for the series)
A  Floating glass pill beside the target (max 8-10 words), with an anchor direction.
B  Editorial split-screen: the app window slides 22% to the right; a 4-6 word headline on the left.
C  3D pop-out: the target lifts to 1.18x, everything around it blurs 2.5 px; numbers in it count up.
D  Kinetic chapter card, full frame, 1.2 s in.

Helper used in the checks (form labels wrap their inputs; IDs are random, never use them):
  const field = (label) => page.locator(`xpath=(//label[starts-with(normalize-space(.), ${JSON.stringify(label)})]//*[self::input or self::select or self::textarea])[1]`);
  const suggestion = (text) => page.locator("body > div[style] button", { hasText: text }).first();

──────────────────────────────
2. REAL UI LAYOUT & DATA SNAPSHOT
──────────────────────────────
Screen A - Bookings list  (/sales/deals)
  Top bar (dark, full width, y 0-56): "BMI Publishing", publication switcher "Onboard Hospitality",
    "Log or schedule" button, bell (top-right).
  Sidebar (left, x 0-256): Platform links; "Sales" group with "Sales Orders" open: Overview, Dashboard,
    Editions, All items, Renewals, Proposals, Bookings, Rate card, Invoicing, My commission.
  Breadcrumb "Sales Orders"; H1 "Bookings" (x 288, y 110).
  Top-right buttons: "Confirmation details" (1117,182,163x28) and the link "New booking" (1288,182,120x28).
  Floating, bottom-right: "Ask AI" (1338,811) and "Feedback" (1296,852).

Screen B - New booking form  (/sales/deals/new), page scrolled to the top
  Breadcrumb "Sales Orders > Bookings > New booking"; H1 "New booking"; under it: "Everything the client has
    agreed, in one place. Each item is added to its issue, and the confirmation is printed from it."
  Left column (x 288-1100), cards from the top:
    "Client" card  (#df-client)                                     top-centre-left
      Company search, placeholder "Search the CRM…" ............... (305,284,383x32)
      Contact search, placeholder "Search for the contact…" ....... (700,284,383x32)
      "Client name as booked" (has an ⓘ) ......................... (305,348,383x32)
      "Contact name" (700,348) · "Contact email" (898,348)
      "Salesperson" select - already "Sally Parker (SP)" .......... (305,412,383x32)
      "Booking date" - already today, 10/16/2026 .................. (700,412,383x32)
      Link "Shared with another salesperson?" ..................... (305,461)
    "What they've booked" heading (ⓘ) + button "Add an item" ...... y ≈ 537
      Item card:
      "Title" select, "Choose…" ................................... (305,594,319x32)
      "From the rate card" select - greyed out until a title is chosen (636,594,447x32)
      "What it is, as it should read on the confirmation" ......... (305,658,778x32)
      "Size code" · "Each time" (1) · "Price each (£)" · "% off this item" (0) · "Rate card price (£)"   y ≈ 722
      "Free - added value" tick box · "Extra wording"
      "Runs in (1)" with links "Every open issue", "Another", "To be allocated"
      Row: "Issue, month or event" select ("Choose the issue, month or event…"), two optional date boxes, ✕
      "Dates are optional: the exact day it runs (if not the issue's date) and when copy is due."
      "After it's sold: Production (suggested)"
    "Price" card (#df-price) and "Confirmation" card (#df-doc) further down, including
      "When to invoice" (default "As soon as allowed") and "Invoice in" (default Pounds).
  Right column (x 1121-1408) "Booking total" card - NOT sticky, scrolls with the page:
    before any item: "Total £0" · "Before VAT." · "Confirm the booking" (1137,338,254x32) · "Pencil it in" ·
      "Pencilled bookings hold the space but don't count in sales figures or commission until they're
      confirmed." · "Cancel"
    once an item is priced a row "At rate card" appears above Total, and the buttons move down 26 px:
      "Confirm the booking" -> (1137,364,254x32)

Screen C - The booking page  (/sales/deals/<id>)
  Toast, bottom-right (1060,823,356x54): "Booking 24NN created"
  H1 "Booking 24NN: Gate Gourmet" (304,110); under it "December, March · Sold by Sally Parker · ordered 16 Oct 2026"
  Buttons top-right: "Change", "Email the confirmation" (primary), "Print or PDF", "More" (…)
  Status: green badge "Confirmed" (304,211,83x22) + "· The confirmation hasn't been sent yet"
  Amber banner (304,253,1088x46): "Waiting for the accounts check. Accounts look over the client, CRM company,
    addresses and items before it's invoiced."
  Six figure cards, y 319-397: "Booking total £5,980" · "Agency commission £0" · "To invoice in all £5,980" ·
    "Invoiced so far £0" · "Ready to invoice £2,990" · "Below rate card 0%"
  "Schedule" heading + amber chip "1 ready to invoice" (y 418)
    Row 1: 10 Dec 2026 · Full page · OBH 108 · copy due 4 Dec 2026 · £2,990 · "Ready to invoice / Due 16 Oct 2026"
    Row 2: 18 Mar 2027 · Full page · OBH 109 · copy due 12 Mar 2027 · £2,990 · "Due 1 Jan 2027"
    Footer: "2 items  £5,980"
  "Hand-offs to editorial and production": "Full page - Production: production@bmipublishing.co.uk · Goes after
    the accounts check"

Data used (from the tutorial seed - type exactly this)
  Company ........ type "Gate"   -> pick "Gate Gourmet · Airline catering"
  Contact ........ type "Daniel" -> pick "Daniel Weber · Gate Gourmet" (fills Daniel Weber, daniel.weber@gategourmet.example)
  Title .......... "OnBoard Hospitality (OBH)"
  Rate card ...... "Full page (210 x 297 mm, 3 mm bleed) - £2,990"
  Issues ......... "Issue 108 · 10 Dec 2026 · book by 2 Dec 2026", then "Issue 109 · 18 Mar 2027 · book by 10 Mar 2027"
                   (the list also shows "To be allocated (issue not decided yet)" and "Issue 107 · 13 Aug 2026 · deadline passed")
  Totals ......... £0 -> £2,990 (one issue) -> £5,980 (two issues)

──────────────────────────────
3. STEP-BY-STEP SCENE CHOREOGRAPHY
──────────────────────────────

STEP 00 · 0:00-0:10 · Chapter card
  Voiceover: "Making a new booking. You'll pick the client, add what they've bought, choose the issues it runs
    in, and confirm it."
  Target: none (full frame). Behind the card: Screen A, blurred 12 px.
  Camera: static, 1.0x.
  Cursor: hidden.
  Callout: ARCHETYPE D - Kinetic chapter card. Badge pill: [clapperboard] "Lesson 1" (primary navy).
    Headline: "Making a new booking". Sub-line: "Sales Orders · under 3 minutes". Card in 1.2 s, holds, out 0.4 s.
  QA:
    await page.goto("/sales/deals");
    await expect(page.getByRole("heading", { name: "Bookings", level: 1 })).toBeVisible();

STEP 01 · 0:10-0:18 · Open the form
  Voiceover: "This is Sales Orders, Bookings. To start, click New booking, at the top right of the list."
  Target: link "New booking" - page.locator('a[href="/sales/deals/new"]') - (1288,182,120x28), TOP-RIGHT.
  Camera: start 1.0x; at 0:12 push in to 1.35x centred on (1348,196) over 900 ms; after the click, pull back to
    1.0x as the new page loads.
  Cursor: appears under the H1 "Bookings" at (330,160) while the camera is wide, then glides to (1348,196);
    hover 300 ms (button darkens); click.
  State change: the page changes to "New booking" (Screen B) with the empty Client card.
  Callout: ARCHETYPE A - Floating glass pill, anchored BELOW-LEFT of the button, arrow pointing up-right.
    Badge pill: [mouse-pointer-click] "Start here" (primary navy). Text: "Opens an empty booking form".
  QA:
    await page.locator('a[href="/sales/deals/new"]').click();
    await page.waitForURL("**/sales/deals/new");
    await expect(page.getByRole("heading", { name: "New booking", level: 1 })).toBeVisible();
    await expect(page.getByPlaceholder("Search the CRM…")).toHaveValue("");

STEP 02 · 0:18-0:33 · Choose the company
  Voiceover: "Start with the client. In the company box, type the first few letters of the name, then pick the
    company from the list. Its name is copied into Client name as booked."
  Target: company search - page.getByPlaceholder("Search the CRM…") - (305,284,383x32), TOP-CENTRE-LEFT; then
    the suggestion (306,321,381x36); then "Client name as booked" (305,348,383x32).
  Camera: 1.0x -> 1.5x on the Client card (centre 500,330) over 800 ms, held for the whole step.
  Cursor: glide to (420,300), click, type "Gate" (90 ms a letter). The list opens under the box with one row
    "Gate Gourmet · Airline catering". Glide down to (496,339), click.
  State change: the box becomes a chip "Gate Gourmet · Airline catering" with "View" and ✕; "Client name as
    booked" fills with "Gate Gourmet". Hold 1.2 s on the filled field (soft glow on it).
  Callout: ARCHETYPE B - Editorial split-screen; window slides 22% right while the list is open.
    Badge pill: [building-2] "Client" (primary navy). Headline: "Linked to the CRM company".
  QA:
    await page.getByPlaceholder("Search the CRM…").pressSequentially("Gate", { delay: 90 });
    await expect(suggestion("Gate Gourmet")).toBeVisible();
    await suggestion("Gate Gourmet").click();
    await expect(field("Client name as booked")).toHaveValue("Gate Gourmet");

STEP 03 · 0:33-0:44 · Choose the contact
  Voiceover: "Next, the contact. Type their name and choose them. Their name and email address fill in by
    themselves."
  Target: contact search - page.getByPlaceholder("Search for the contact…") - (700,284,383x32), TOP-CENTRE; then
    the suggestion (701,327,381x36); then "Contact name" (700,348) and "Contact email" (898,348).
  Camera: hold 1.5x, pan right to centre (890,330) over 600 ms.
  Cursor: glide to (820,300), click, type "Daniel". One row appears: "Daniel Weber · Gate Gourmet". Glide to
    (891,345), click.
  State change: chip "Daniel Weber · Gate Gourmet" with "View" and ✕; "Contact name" = "Daniel Weber";
    "Contact email" = "daniel.weber@gategourmet.example" (text is cut off in the box - that's expected).
  Callout: ARCHETYPE A - Floating glass pill, anchored ABOVE the Contact name / Contact email pair, arrow down.
    Badge pill: [user-round] "Contact" (primary navy). Text: "Taken from their CRM record".
  QA:
    await page.getByPlaceholder("Search for the contact…").pressSequentially("Daniel", { delay: 90 });
    await suggestion("Daniel Weber").click();
    await expect(field("Contact name")).toHaveValue("Daniel Weber");
    await expect(field("Contact email")).toHaveValue("daniel.weber@gategourmet.example");

STEP 04 · 0:44-0:52 · Already filled in
  Voiceover: "Salesperson and Booking date are already filled in, with your name and today's date."
  Target: "Salesperson" (305,412,383x32) and "Booking date" (700,412,383x32), CENTRE-LEFT - treated as one row.
  Camera: hold 1.5x, tilt down to centre (694,428) over 500 ms.
  Cursor: rests still beside the row at (1095,428); no click.
  State change: none - this step shows what the form did for you. The row lifts.
  Callout: ARCHETYPE C - 3D pop-out of the row (1.18x, 2.5 px blur around it).
    Badge pill: [wand-sparkles] "Filled in" (emerald). Headline on the card: "Change only for a colleague's sale".
  QA:
    await expect(field("Salesperson")).toHaveValue(/.+/);
    await expect(field("Salesperson").locator("option:checked")).toHaveText("Sally Parker (SP)");
    await expect(field("Booking date")).not.toHaveValue("");

STEP 05 · 0:52-1:02 · Choose the title
  Voiceover: "Now, what they've booked. Choose the Title. The rate card list next to it opens up, with that
    title's prices."
  Target: "Title" select (305,594,319x32), BOTTOM-LEFT; then "From the rate card" (636,594,447x32), BOTTOM-CENTRE.
  Camera: pull to 1.25x and move to centre (694,600) over 800 ms (heading "What they've booked" in view).
  Cursor: glide to (464,610), click; the native list shows the titles; choose "OnBoard Hospitality (OBH)".
    Glide right to (859,610) and hover only.
  State change: "Title" shows "OnBoard Hospitality (OBH)"; "From the rate card" stops being greyed out and now
    reads "Choose a product, or type your own below".
  Callout: ARCHETYPE A - Floating glass pill, anchored ABOVE "From the rate card", arrow down.
    Badge pill: [book-open] "Rate card" (primary navy). Text: "Prices from this year's rate card".
  QA:
    await expect(field("From the rate card")).toBeDisabled();
    await field("Title").selectOption({ label: "OnBoard Hospitality (OBH)" });
    await expect(field("From the rate card")).toBeEnabled();
    await expect(field("From the rate card").locator("option").first()).toHaveText("Choose a product, or type your own below");

STEP 06 · 1:02-1:16 · Pick the product
  Voiceover: "Pick Full page. The description, the price and the rate card price all fill in, and the Booking
    total on the right goes up to two thousand, nine hundred and ninety pounds."
  Target: "From the rate card" (636,594,447x32); then the fields "What it is, as it should read on the
    confirmation" (305,658), "Price each (£)" (621,722), "Rate card price (£)" (937,722); then the "Booking
    total" card (1121,236 - 1408,575), TOP-RIGHT.
  Camera: 1.25x on the item card; at 1:10 glide right/up to the Booking total card at 1.4x (centre 1264,300)
    over 900 ms.
  Cursor: click (859,610); choose "Full page (210 x 297 mm, 3 mm bleed) - £2,990" from the list. Then park at
    (1100,560) out of the way.
  State change: description = "Full page"; Price each (£) = 2990; Rate card price (£) = 2990; the Booking total
    card gains "At rate card £2,990" and Total changes £0 -> £2,990; the buttons move down 26 px.
  Callout: ARCHETYPE C - 3D pop-out of the Booking total card; the Total figure counts £0 -> £2,990 in 700 ms.
    Badge pill: [tag] "Price" (primary navy). Headline: "Before VAT, at rate card".
  QA:
    const rc = field("From the rate card");
    await rc.selectOption({ label: "Full page (210 x 297 mm, 3 mm bleed) - £2,990" });
    await expect(field("What it is, as it should read on the confirmation")).toHaveValue("Full page");
    await expect(field("Price each (£)")).toHaveValue("2990");
    await expect(field("Rate card price (£)")).toHaveValue("2990");
    await expect(page.getByText("At rate card")).toBeVisible();
    await expect(page.getByText("£2,990", { exact: true }).first()).toBeVisible();

STEP 07 · 1:16-1:30 · Choose the issue
  Voiceover: "Under Runs in, choose the issue. Each one shows its date and its booking deadline, and an issue
    that's past its deadline says so."
  Setup: scroll the page to 200 px smoothly over 700 ms: await page.evaluate(() => window.scrollTo({ top: 200, behavior: "smooth" }))
    (after the scroll: "Runs in (1)" at (318,619); select at (318,650,258x32); Total at (1137,106)).
  Target: page.locator("select[aria-label='Issue, month or event']").first() - (318,650,258x32), BOTTOM-LEFT.
  Camera: 1.0x during the scroll, then 1.45x centred on (450,660) over 700 ms.
  Cursor: glide to (447,666), click. The list shows: "To be allocated (issue not decided yet)", "Issue 107 ·
    13 Aug 2026 · deadline passed", "Issue 108 · 10 Dec 2026 · book by 2 Dec 2026", "Issue 109 · 18 Mar 2027 ·
    book by 10 Mar 2027". Hover over "deadline passed" for 600 ms, then choose Issue 108.
  State change: the row shows "Issue 108 · 10 Dec 2026 · book b…" and "£2,990" at its right.
  Callout: ARCHETYPE B - Editorial split-screen while the list is open; window slides 22% right.
    Badge pill: [calendar-days] "Runs in" (primary navy). Headline: "Deadlines shown in the list".
  QA:
    const runs = page.locator("select[aria-label='Issue, month or event']");
    await expect(runs.first().locator("option", { hasText: "deadline passed" })).toHaveCount(1);
    await runs.first().selectOption({ label: "Issue 108 · 10 Dec 2026 · book by 2 Dec 2026" });
    await expect(page.getByText("Runs in (1)")).toBeVisible();

STEP 08 · 1:30-1:44 · Add a second issue
  Voiceover: "Running it twice? Click Another, and choose Issue 109. Runs in now shows two, and the total doubles
    to five thousand, nine hundred and eighty pounds."
  Target: link-style button "Another" - page.getByRole("button", { name: "Another", exact: true }) -
    (897,619,60x16), CENTRE-RIGHT; then the new row's select (318,699,258x32); then Total (1137,106), TOP-RIGHT.
  Camera: hold 1.45x, pan to (700,650) for the click; at 1:39 move to 1.3x showing both the rows and the Booking
    total card (centre 850,400) over 800 ms.
  Cursor: glide to (927,627), click; a second row appears below the first; glide to (447,715), click, choose
    "Issue 109 · 18 Mar 2027 · book by 10 Mar 2027". Park at (1100,560).
  State change: header "Runs in (1)" -> "Runs in (2)"; second row shows "Issue 109 · 18 Mar 2027 · book b…" and
    "£2,990"; Booking total: At rate card and Total £2,990 -> £5,980; under the item "£5,980 for 2".
  Callout: ARCHETYPE C - 3D pop-out of the Booking total card; Total counts £2,990 -> £5,980 in 700 ms.
    Badge pill: [calendar-plus] "2 issues" (primary navy). Headline: "One price for each issue".
  QA:
    await page.getByRole("button", { name: "Another", exact: true }).click();
    await expect(runs).toHaveCount(2);
    await runs.nth(1).selectOption({ label: "Issue 109 · 18 Mar 2027 · book by 10 Mar 2027" });
    await expect(page.getByText("Runs in (2)")).toBeVisible();
    await expect(page.getByText("£5,980", { exact: true }).first()).toBeVisible();

STEP 09 · 1:44-1:56 · When to invoice
  Voiceover: "Further down, When to invoice is set to As soon as allowed. Leave it, unless the client agreed
    something different."
  Setup: scroll so the field sits mid-screen, smoothly over 900 ms:
    await field("When to invoice").evaluate(e => e.scrollIntoView({ block: "center", behavior: "smooth" }))
    (after it: "When to invoice" at (305,434,383x32), "Invoice in" at (700,434,383x32)).
  Target: "When to invoice" (305,434,383x32), CENTRE-LEFT.
  Camera: 1.0x during the scroll, then 1.5x on (496,450) over 600 ms.
  Cursor: glide to (496,450) and hover; no click (the choice is left as it is).
  State change: none - the default is the lesson. Soft glow on the select.
  Callout: ARCHETYPE A - Floating glass pill, anchored to the RIGHT of the select, arrow left.
    Badge pill: [receipt] "Invoicing" (amber). Text: "Invoiced in the quarter it runs".
  QA:
    await expect(field("When to invoice")).toHaveValue("asap");
    await expect(field("When to invoice").locator("option:checked")).toHaveText("As soon as allowed");

STEP 10 · 1:56-2:08 · Confirm
  Voiceover: "When the client has said yes, click Confirm the booking. Confirming is your sign-off that it's agreed
    with the client. It's saved, with its own number."
  Setup: scroll to the top smoothly over 900 ms: await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }))
  Target: "Confirm the booking" - page.getByRole("button", { name: "Confirm the booking" }) - (1137,364,254x32),
    TOP-RIGHT. (Leave "Pencil it in" alone - it's lesson 3.)
  Camera: 1.0x for the scroll, then 1.4x on (1264,380) over 700 ms; after the click, back to 1.0x as Screen C
    loads.
  Cursor: glide to (1264,380), hover 300 ms, click.
  State change: the form is replaced by the booking page (Screen C); toast "Booking 24NN created" slides in at
    the bottom right.
  Callout: ARCHETYPE B - Editorial split-screen on Screen C as it arrives; window slides 22% right.
    Badge pill: [circle-check] "Confirmed by you" (emerald). Headline: "The client has said yes".
  QA:
    await page.getByRole("button", { name: "Confirm the booking" }).click();
    await page.waitForURL(/\/sales\/deals\/[0-9a-f-]{36}$/);
    await expect(page.locator("[data-sonner-toast]")).toContainText(/Booking \d+ created/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^Booking \d+: Gate Gourmet$/);

STEP 11 · 2:08-2:23 · Confirmed, and yours to send
  Voiceover: "It's marked Confirmed, and Email the confirmation is ready, so you can send it to the client now.
    The message underneath is for Accounts: they check it before it's invoiced, not before you send it."
  Target: badge "Confirmed" (304,211,83x22) TOP-LEFT; button "Email the confirmation" (1047,142,176x28)
    TOP-RIGHT; then the amber banner (304,253,1088x46) TOP-CENTRE.
  Camera: 1.4x on the badge (centre 345,222); at 2:11 pan to the button (centre 1135,156); at 2:16 pull to 1.2x
    on the banner (centre 700,276), each move 800 ms.
  Cursor: glide to (345,222) and hover; glide to (1135,156) and hover (button darkens, NO click - sending is
    lesson 2); then trace along under the banner to (800,290).
  State change: none - reading the new state. The button glows, then the banner glows softly.
  Callout: ARCHETYPE A - Floating glass pill, anchored BELOW the banner, arrow up.
    Badge pill: [receipt] "For invoicing" (amber). Text: "Accounts check it before it's invoiced".
  QA:
    await expect(page.getByText("Confirmed", { exact: true })).toBeVisible();
    await expect(page.getByText("The confirmation hasn't been sent yet")).toBeVisible();
    await expect(page.getByRole("button", { name: "Email the confirmation" })).toBeEnabled();
    await expect(page.getByText("Waiting for the accounts check.")).toBeVisible();

STEP 12 · 2:23-2:39 · The schedule
  Voiceover: "The Schedule lists both issues. Issue 108 runs this quarter, so it's ready to invoice now. Issue
    109 is due in January."
  Target: "Schedule" card (305,418 - 1391,620), CENTRE; rows at y 496-546 (OBH 108) and 546-583 (OBH 109); the
    Invoice column "Ready to invoice / Due 16 Oct 2026" (1190,504) and "Due 1 Jan 2027" (1190,557), CENTRE-RIGHT.
  Camera: 1.2x on the card (centre 848,510); at 2:31 push to 1.5x on the Invoice column (centre 1230,535).
  Cursor: glide along row 1 to (1236,512), pause; then down to (1232,565), pause.
  State change: none - reading. Row 1 then row 2 highlight in turn.
  Callout: ARCHETYPE C - 3D pop-out of the Schedule card; "2 items £5,980" counts up from £0 in 700 ms.
    Badge pill: [list-checks] "Schedule" (primary navy). Headline: "One row for each issue".
  QA:
    await expect(page.getByRole("heading", { name: /^Schedule/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "OBH 108" })).toBeVisible();
    await expect(page.getByRole("link", { name: "OBH 109" })).toBeVisible();
    await expect(page.locator("table").getByText("Ready to invoice")).toBeVisible();
    await expect(page.getByText("Due 1 Jan 2027")).toBeVisible();

STEP 13 · 2:39-2:47 · End card
  Voiceover: "That's a new booking made. Next, sending the confirmation to the client."
  Target: none (full frame). Behind: Screen C, blurred 12 px.
  Camera: slow pull back 1.0x -> 0.95x.
  Cursor: hidden.
  Callout: ARCHETYPE D - Kinetic chapter card. Badge pill: [arrow-right] "Next lesson" (primary navy).
    Headline: "Sending the confirmation". Sub-line: "Lesson 2 · Sales".
  QA:
    await expect(page.getByText("Hand-offs to editorial and production")).toBeVisible();
    await expect(page.getByText("Goes after the accounts check")).toBeVisible();

──────────────────────────────
4. WORDS ON SCREEN THAT MUST MATCH EXACTLY
──────────────────────────────
New booking · Search the CRM… · Gate Gourmet · Airline catering · Client name as booked · Search for the contact… ·
Daniel Weber · Gate Gourmet · Contact name · Contact email · Salesperson · Sally Parker (SP) · Booking date ·
What they've booked · Title · OnBoard Hospitality (OBH) · From the rate card ·
Full page (210 x 297 mm, 3 mm bleed) - £2,990 · Price each (£) · Rate card price (£) · Booking total · At rate card ·
Total · Before VAT. · Runs in (1) / Runs in (2) · Another · Issue 108 · 10 Dec 2026 · book by 2 Dec 2026 ·
Issue 109 · 18 Mar 2027 · book by 10 Mar 2027 · deadline passed · When to invoice · As soon as allowed ·
Confirm the booking · Pencil it in · Booking 24NN created · Confirmed · Email the confirmation · The confirmation hasn't been sent yet ·
Waiting for the accounts check. · Schedule · 1 ready to invoice · Ready to invoice · Due 1 Jan 2027 ·
Hand-offs to editorial and production
````
