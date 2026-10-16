# Tutorial videos

Short screen-recorded lessons (1 to 3 minutes each) that teach one task at a time. They are teaching videos, not
adverts: no sales talk, and the voiceover only says what is on screen at that moment. Each video has a blueprint
here that an AI video tool (Google Antigravity) can follow step by step. Every label, selector and position in a
blueprint was checked in the real app on the tutorial data before it was written down.

## Recording setup (same for every video)

1. A demo database, never the live one. Load the tutorial data, and run it again before **every take** (it removes
   the bookings made in earlier takes, so the screens look the same each time):

   ```
   cd backend
   DATABASE_URL=postgresql+psycopg://.../bmi_demo python -m scripts.seed_tutorials --yes
   ```

   It makes Gate Gourmet (Airline catering) with Daniel Weber (Head of Marketing), Onboard Hospitality issues 108
   (10 Dec 2026, book by 2 Dec) and 109 (18 Mar 2027, book by 10 Mar), the 2026 rate cards, and two sign-ins:
   `sally.parker@tutorial.bmi` (Sales) and `samantha.elmer@tutorial.bmi` (Accounts), password `BMI-tutorial-2026`.
2. Run the frontend as a production build (`npm run build && npm start`), so the development badge in the bottom
   left corner doesn't show.
3. Browser window 1440 x 900, zoom 100%, light theme, sidebar open. Record at 2x pixel density for sharp zooms.
4. Booking numbers go up with every take (2441, 2442...), so scripts and checks never rely on the number.

## Selector rules

- base-ui makes element IDs at random, so never select by `id` except the four section anchors on the booking
  form (`#df-client`, `#df-items`, `#df-price`, `#df-doc`).
- Most form labels wrap their input, so select a field from its label:
  ```js
  const field = (label) => page.locator(`xpath=(//label[starts-with(normalize-space(.), ${JSON.stringify(label)})]//*[self::input or self::select or self::textarea])[1]`);
  ```
- Search suggestions (company, contact) open in a pop-up at the end of the page: `page.locator("body > div[style] button", { hasText: "..." })`.
- Buttons by their visible text: `page.getByRole("button", { name: "...", exact: true })`. A link drawn as a button
  (like "New booking") counts as a button, not a link, so select it by its address: `a[href="/sales/deals/new"]`.
- Money shows up inside drop-down options too, so match amounts exactly: `page.getByText("£2,990", { exact: true })`.

## Who does what (agreed 15 Oct - every script must say it this way)

- The **salesperson** confirms a booking once the client has said yes ("Confirm the booking"). That is the sign-off
  on the sale, and they send the confirmation to the client themselves.
- **Accounts** check a confirmed booking (client, CRM company, addresses, items) only so it can be invoiced. It is
  not an approval of the sale and doesn't hold up the confirmation (setting "Confirmation waits for the check" is off).

## Curriculum

Sales Orders first, in the order a new person meets them. Each video ends where the next one starts.

| # | Video | Who it's for | Length | What it teaches |
|---|---|---|---|---|
| 1 | **Making a new booking** ([blueprint](01-making-a-booking/blueprint.md)) | Sales | 2:45 | Client, contact, an item from the rate card, two issues, confirming once the client has said yes |
| 2 | Sending the confirmation | Sales | 1:30 | Email the confirmation, Print or PDF, what the client receives, "hasn't been sent yet" |
| 3 | Pencil it in, then confirm | Sales | 1:30 | Holding space without counting it in sales figures or commission, confirming later |
| 4 | Packages and "to be allocated" | Sales | 2:30 | One package price, Every open issue, To be allocated, allocating later |
| 5 | Discounts, agencies and free extras | Sales | 2:00 | % off this item, % off the whole booking, agency commission, Free - added value, Below rate card |
| 6 | When to invoice | Sales, Accounts | 2:00 | The six choices, what "ready to invoice" means, due dates, reminders |
| 7 | Checking bookings before invoicing | Accounts | 2:00 | The check card in the Review Queue: client, CRM company, addresses and items; "looks right" or "needs a fix". It's a check for invoicing - the salesperson has already confirmed the sale |
| 8 | Draft invoices in Xero | Accounts | 2:30 | Making the draft, what happens when something doesn't match, invoice codes |
| 9 | Changing a booking | Sales | 2:00 | Change, what locks once it's checked or invoiced, asking Accounts to approve a change |
| 10 | Hand-offs to editorial and production | Sales, Production | 1:45 | Hand off to, who gets the email and when, resending |
| 11 | Editions and deadlines | Sales, Production | 2:30 | The editions list, an edition's page, the checks when an issue goes to press |
| 12 | The Invoicing page | Accounts | 2:30 | What still needs invoicing, invoices that don't match, Xero invoices with no booking |
| 13 | Rebooking next year | Sales | 1:30 | A pencilled copy on next year's issues and prices |
| 14 | From proposal to booking | Sales | 3:00 | Building a proposal from the rate card and turning a yes into a booking |
| 15 | My commission | Sales | 2:00 | The monthly statement and what counts as new business |
| 16 | Overview and dashboard | Managers | 2:30 | Booked against invoiced, this year against last, the weekly summary |
| 17 | Asking the AI for help | Everyone | 1:30 | Ask AI on any page, Show me, "This didn't help" |

Recommended order to make them: 1, 2, 6, 7, 8, 10 (one booking's full life, from sale to invoice), then 3, 4, 5, 9,
11, 12, and the rest. Each one gets the same check in the real app before its blueprint is written: none of the
labels in the table beyond video 1 should be used in a script until that check is done.

## Previewing before Antigravity (about 3 minutes, no AI)

Each video has a `preview.mjs` that plays its blueprint in the real app at real speed and records it: the voiceover
as subtitles, each step's callout and badge, a visible cursor, and a ring on what's being pointed at. The words and
timings are read from `blueprint.md`, so change the script there, run the preview, watch it, and repeat. Only send
the blueprint to Antigravity once the preview is right. It's a rough cut: the zooms, split-screens and pop-outs are
only named on the callout ("Callout B"), and native drop-downs can't be filmed, so the choice just appears.

```
cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/bmi_demo python -m scripts.seed_tutorials --yes
cd .. && node docs/tutorials/01-making-a-booking/preview.mjs http://localhost:3000
```

It writes `preview.webm` beside the blueprint (open it in Chrome), and warns in the terminal if a step's actions
take longer than its time - that means the voiceover needs more seconds. Uses the Playwright already installed in
`frontend/`; if it can't find a browser, add the Chrome path as a second argument.

When only a few steps change, ask Antigravity to remake just those steps and keep the rest, rather than the whole
video.
