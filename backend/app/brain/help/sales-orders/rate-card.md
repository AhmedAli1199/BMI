---
title: Rate card
screens: ["/sales/rate-card", "/sales/rate-card/[brand]"]
summary: Each brand's prices, laid out like the media packs, which proposals, bookings and renewal emails all quote from.
sources: ["frontend/src/app/(app)/sales/rate-card/page.tsx", "frontend/src/app/(app)/sales/rate-card/[brand]/page.tsx", "frontend/src/components/rate-card/brand-rate-card.tsx", "frontend/src/components/rate-card/price-sheet.tsx", "frontend/src/components/rate-card/section-sheet.tsx", "frontend/src/components/rate-card/offers-panel.tsx", "frontend/src/components/rate-card/next-year-dialog.tsx", "frontend/src/components/rate-card/history-sheet.tsx", "frontend/src/components/rate-card/online-links.tsx", "frontend/src/lib/rate-card-types.ts", "backend/app/api/routes/rate_card.py", "backend/app/sales/brands.py", "backend/app/sales/offers.py", "backend/app/automations/settings_registry.py", "backend/app/api/routes/sales.py"]
---

## What this screen is for
The rate card holds every price BMI sells, one page per brand: Onboard Hospitality, The Business Travel Magazine and Selling Travel. It's laid out like the media packs. Proposals, bookings, renewal emails and proposal request replies all take their prices from here, so this is the one place to keep prices right. All prices are before VAT.

## What you see
**Rate card home** (Sales Orders > Rate card)
- **Download all as Excel** and a year switch at the top.
- "Getting your <year> rate card ready": a three-step checklist (put each brand's prices in, check every price marked "Please check", add your offers and discounts). Each step is ticked and crossed out when done. The box disappears once all three are done.
- One row per brand: its name and website, how many prices (and how many are "on request"), how many offers, an amber "<n> to check" if any need checking, "<n> prices ready to load from the media pack" if the year is empty, when it was last changed, and "View only" if you can't change it. Click a row to open that brand.

**A brand's rate card**
- The title "<brand> rate card", a coloured brand stripe and the year switch.
- A toolbar (see below).
- If the year is empty: "No <year> prices yet", with a button to load the media-pack prices if they're available.
- An amber banner if any prices or offers still need checking.
- Jump links to each section, with how many prices each holds, and to Offers.
- One card per section: Print magazine, Sponsored content, Website, Newsletter & emails, Events & sponsorship, Awards, Directory listings, Other, then any of the brand's own sections. Each price shows its name, size (for example "210 x 297 mm, 3 mm bleed · 2 pages"), specs, "Also:" names, an end date ("Until <date>" in amber, "Ended <date>" in red) and notes. On the right: the price ("£2,990", "From £495", or "On request") with "per month", "per event" and so on underneath.
- **Offers & discounts**.
- **Online edition links** (folded away; click to open).
- **Removed from the rate card (<n>)** at the bottom, if anything was removed.

## Buttons and controls
### Year switch
Shows another year's prices. This year and next year are always offered.

### Download all as Excel / Excel
Downloads the prices for the year as a spreadsheet: every brand from the home page, or just this brand from its page. Anyone can download.

### Add a price
Opens the side panel to add a product (see "The price panel" below). Editors only.

### Add a section
Gives the brand its own heading for things the standard sections don't cover, such as "Cover wraps & belly bands". Fill in **What is it called?**, an optional **Short description** and **Booked under** (which part of the order register these bookings go into), then **Add section**. The section appears in every year. Editors only.

### Prepare <next year> prices / Add more to <next year>
Copies this year's list into next year (see "How it works"). Step 1: **Raise all prices by** (Keep the same, 3%, 5%, 10%, or type your own %) and, if raising, **Round the new prices to the nearest** £1 to £50. Press **See the new prices**. Step 2: every product with its old and new price; type over any you want to set yourself. **Save <year> prices** saves them and takes you to next year's page. **Back** returns to step 1. Editors only, and only when this year has prices.

### Changes
Opens "Changes to these prices", newest first: what changed, from what to what, who and when. **Put back** undoes one change, as long as nobody has changed it again since. Anyone can see the list; only editors can put back.

### Print or save as PDF
Opens your browser's print window. Choose "Save as PDF" there to make a PDF. Buttons and editing controls are left off the printout.

### How this page works
Shows or hides a short guide to the page.

### Load the <year> media-pack prices
Shown on an empty year when prices from that year's media pack are ready. Loads them all, each marked "Please check". Editors only.

### I've checked them all
On the amber banner. Marks every price and offer of this brand and year as checked (it asks first). Only use it if you've really looked at them all. Editors only.

### Clicking a price
Editors can click a price (hovering over it says **Click to change the price, then press Enter or click away to save (Escape cancels)**), type the new one and press Enter or click away. It saves straight away. Escape cancels without saving; clicking away with nothing changed (or the box empty) leaves the price as it was. If the new price is more than five times bigger or smaller than the old one, it asks you to confirm. A price that was "On request" becomes a set price.

### Clicking a product's name / pencil icon
Opens the price panel to change everything else about that product (hovering says **Change this product - name, size, pages, notes**). Editors only.

### Looks right
Shown next to a price marked "Please check". Press it if the price is correct, and the flag clears. People who can't edit see "Please check" instead.

### Up and down arrows
Move a price up or down within its section (they appear when you hover over the row). Editors only.

### Add (on a section) / Add prices to another section
Add a price straight into that section. The "Add prices to another section" buttons appear under the cards for empty standard sections.

### Pencil next to one of the brand's own section names
Rename the section, change its description or what it's booked under (**Save**), or **Remove section**. A section can only be removed when it has no prices in any year.

### The price panel (Add a price / Change <product>)
- **It's right**: shown when the price needs checking; clears the flag and saves.
- **Section**: where it appears.
- **What is it called?**
- **How is it priced?**: **A set price**, **Starts from** (the lowest price), or **Price on request** (no list price).
- **Price (£)** or **Starting price (£)**, and **The price is** per advert / item, per month, per week, per year, per event or per entry.
- **Size (optional)** (or **+ Add a size**): width x height, in mm (print, with bleed) or pixels (online). Give both or neither.
- **Pages (optional)** (or **+ Add a page count**): for example 2 for a double-page advertorial. Bookings of it then count these pages.
- **Other specs (optional)**.
- **Also called (optional)**: shorthand used on the order register (for example "FP" for Full page). Type and press Enter. It's how a booking finds this price for renewal emails.
- **Notes for the sales team (optional)**.
- **Price ends on (optional)**: for early-bird or limited-time prices.
- **Show where it's booked** (then **Hide where it's booked**) / **Booked under**: only change it if this product is booked somewhere other than the section's usual title.
- **Remove from the rate card** (with **Undo** in the message straight after), **Cancel**, and **Add price** or **Save changes**.

### Add an offer / clicking an offer
Opens the offer panel (editors only):
- **What kind of offer?**: **Discount for booking more** (Book 2 save 10%...), **Lower price for a series** (4 at £3,250 each...), **Early-bird price** (ends on a date) or **Just a note**.
- **Which part of the rate card?** and **Only for these products (optional)**: leave all unticked to cover the whole section.
- **The discounts** or **The series prices**, with **Add a step** and a bin (**Remove this step**) to remove a step.
- **Ends on** (required for early-bird, optional for the others).
- **How it reads on the rate card and proposals**: written for you from the steps; change it if you like.
- **More detail (optional)**, then **Save offer**, **Cancel**, or **Delete**.

### Online edition links
For each title: **Link to a page in an issue** and **Link to an issue**, using {edition}, {year} and {page}. An example of the finished link shows underneath. **Save** appears when you change one. Renewal emails use these to link advertisers to last year's ad. Admins, data managers and the brand's publishers can change them.

### Put back (removed products)
Under "Removed from the rate card", brings a removed product back. Editors only.

## How it works
- **Who can change prices:** by default only admins and data managers. If an admin turns on the setting "Publishers can change their own prices", each brand's publishers can change their own brand too. Everyone else sees the rate card read-only, with "View only" on the home page.
- Each brand is split into the order register's titles behind the scenes. Each section's prices are filed under the right title (for example website prices for OBH go under OBH Web), so bookings, renewals and proposals still match.
- Prices loaded from a media pack are marked "Please check" until someone confirms them.
- You can't have two products with the same name in the same section and title for one year.
- **Next year:** every price for this year that isn't already in next year is copied, raised by your % and rounded. Prices "on request" stay on request. End dates move on a year. This year's prices don't change. Offers are copied too, moved on a year and marked "Please check", but only if next year has no offers yet.
- **Offers in proposals:** when a salesperson saves a proposal, the brand's offers are applied by themselves to rate card lines (per option and per title) and shown as their own green discount lines. Expired offers are skipped, and a price past its end date is flagged.
- Every change is recorded in **Changes**, so it can be undone.

## Common questions
**Q: How do I change a price?**
A: 1. Open the brand. 2. Click the price. 3. Type the new price. 4. Press Enter.

**Q: How do I set up next year's rate card?**
A: 1. Open the brand on this year. 2. Press **Prepare <next year> prices**. 3. Choose a rise (or **Keep the same**) and rounding. 4. Press **See the new prices** and type over any you want different. 5. Press **Save <next year> prices**. 6. Check the offers, which are marked "Please check".

**Q: The rate card for this year is empty. How do I fill it?**
A: If it says prices are ready from the media pack, press **Load the <year> media-pack prices**, then check each one. Otherwise go to last year and use **Prepare <year> prices**, or add them one by one with **Add a price**.

**Q: How do I add a "book 3, save 20%" discount?**
A: 1. Press **Add an offer**. 2. Choose **Discount for booking more**. 3. Pick the section (and products, if it's only for some). 4. Set "Book 2 save 10%", then **Add a step** for "3 save 20%". 5. Press **Save offer**. Proposals apply it automatically.

**Q: I changed a price by mistake.**
A: Press **Changes**, find the change and press **Put back**.

**Q: Where do cover wraps go?**
A: Press **Add a section**, call it "Cover wraps & belly bands", choose what it's booked under, and press **Add section**. Then **Add** prices into it.

**Q: How do I give someone a PDF of the rate card?**
A: Press **Print or save as PDF** and choose "Save as PDF" in the print window. Or press **Excel** for a spreadsheet.

**Q: Why does a product show "Ended" in red?**
A: Its "Price ends on" date has passed. Change the date or the price in the price panel.

## If something doesn't work
- **I can't click prices and there's no Add a price button**: you have view-only access. Only admins and data managers can change prices, unless an admin has turned on "Publishers can change their own prices". The note at the bottom of the home page about publishers only applies when that setting is on.
- **"Only administrators and data managers can change the rate card"**: as above.
- **"Type a price in pounds, e.g. 2990"**: the price must be a number of 0 or more.
- **Add price / Save changes is greyed out**: give the product a name and a price (or choose Price on request). Give both width and height, or neither.
- **"... is already on this rate card - edit that one instead"**: that product name already exists in that section for this year.
- **"There's already a section called ..."**: pick a different name.
- **I can't remove a section**: it still has prices in this or another year. Move or remove them first.
- **"Say when the early-bird price ends"**: early-bird offers need an end date.
- **"Each discount needs a number of bookings (2 or more) and a percentage"**: fill in every step, or remove the empty one.
- **Prepare next year's prices is missing**: you can't edit, or this year has no prices yet.
- **"Every <year> price is already in <next year>. Nothing to copy."**: next year is already filled. Add any new ones by hand.
- **Put back is missing on a change**: it has been changed again since, or it's a kind of change that can't be undone automatically. Edit it directly.
- **My typed price disappeared**: you pressed Escape, or what you typed wasn't a price (a message says so). Click the price again, type it and press Enter.
