---
title: Proposals
screens: ["/sales/proposals", "/sales/proposals/new", "/sales/proposals/[id]"]
summary: Build a proposal for a client from the rate card and editorial plan, edit it on one page, send it as an email or Word document, and turn a yes into a booking.
sources: ["frontend/src/app/(app)/sales/proposals/page.tsx", "frontend/src/app/(app)/sales/proposals/new/page.tsx", "frontend/src/app/(app)/sales/proposals/[id]/page.tsx", "frontend/src/components/sales/proposal-new-form.tsx", "frontend/src/components/sales/proposal-editor.tsx", "frontend/src/components/sales/proposal-document.tsx", "frontend/src/components/sales/proposal-lines.tsx", "frontend/src/components/sales/proposal-sections.tsx", "frontend/src/components/sales/proposal-ai-revise.tsx", "frontend/src/components/sales/proposal-issue-picker.tsx", "frontend/src/components/mail-merge/rich-email-editor.tsx", "frontend/src/lib/proposals-types.ts", "backend/app/api/routes/proposals.py", "backend/app/proposals/pricing.py", "backend/app/proposals/drafting.py", "backend/app/proposals/context.py", "backend/app/proposals/blocks.py", "backend/app/proposals/render.py", "backend/app/sales/offers.py", "backend/app/api/routes/deals.py"]
---

## What this screen is for
Proposals are where a salesperson puts together an offer for a client. You pick the client, the title and the products, and the Brain drafts the wording for you to edit. Prices only ever come from the rate card or from what you type. Nothing goes to the client until you press **Send** yourself, and every sent proposal is noted on the client's record with a follow-up reminder.

## What you see
**Proposals list** (Sales Orders > Proposals)
- Buttons across the top: **Report**, **How you write**, **Examples library** and **New proposal**.
- If you haven't set up your writing style yet, a strip invites you to teach the Brain how you write, with a **Start** link.
- A table of proposals: Client (click to open), Campaign, Title, Total (before VAT), Status and By (who made it). Status is a grey **Draft** badge, or a coloured **Sent <date>** badge.
- Salespeople see only the proposals they made. Admins and data managers see everyone's. The list shows the latest 200.

**New proposal**
- Client (required), Who it's for (optional contact), Title, Which issue, Word template and Campaign name.
- "What you're offering": the products and prices panel (described below).
- **Draft the proposal** at the bottom.

**A proposal** (one page editor)
- A green note at the top once it's sent, saying when, how, and the follow-up date.
- Amber warnings (drafts only) for anything missing, for example "No bookings on record for this client", "No 2026 rate card for ... yet", "We picked Issue ..., the next one still open for bookings", or rate card offer notes.
- **How it goes to the client**: **As an email** or **As a Word document**.
- Campaign name (Word header) and Word template.
- **Products and prices**: every line, its issues, options and totals.
- **Wording**: the **Change it with the Brain** box, then the whole proposal as one page with a formatting toolbar.
- The buttons along the bottom.
- On the right: **The issue** (date, advertising deadline, theme, features, with a link that opens the issue in a new tab), **History with BMI** (the client's past bookings and total from the order register) and a note saying whether the wording was drafted by the Brain or is standard text.

## Buttons and controls
### New proposal
Opens the new proposal form. You can also start one from **Build a proposal** on any company page, from **Pitch this issue** on an issue page, or from **Draft a proposal** in "Who should we pitch?". Those fill in the client and/or issue for you.

### Client / Who it's for (optional)
Search for the company, and optionally the contact. The contact's email address fills the "To" box when you email it. Picking a client fills the campaign name with "<client> 2026/27" style wording if it's empty.

### Title
The magazine or brand the proposal is mainly for. Changing it also changes the Word template to match and resets the issue.

### Which issue
The title's upcoming issues from the editorial plan, showing the date and "book by" deadline, or "advertising closed". Leave it on **The next open issue (picked for you)** and the Brain picks the next one still taking adverts, and flags that it did. The issue's date, deadline, theme and features go into the wording.

### Word template
Onboard Hospitality, Selling Travel or The Business Travel Magazine. It follows the title, but you can change it.

### Campaign name
Goes in the header of the Word document, for example "Delta Air Lines 2026/27".

### What sort of proposal
A single issue, Several issues, A year's programme, Digital (website, newsletters, social), Awards or event sponsorship, or A mixed package. It shapes the standard wording and what the Brain is told.

### % off the whole proposal
Taken off each option's total, after any % off a line and any rate card offer.

### Add from its rate card / title picker
Choose a title in the first drop-down, then a product in **Add from its rate card…**. The price is filled in from the rate card and can't be changed on the line. Products priced "on request" can't be added this way. Use your own line instead.

### Add my own line
A line for anything not on the rate card. Type what it is and the price. Every own line needs a name and a price.

### Qty, Each (£), % off, and the bin icon
Quantity, price per unit (own lines only), a % off that line, and remove the line. Once a line has issues picked, the quantity is set by how many issues it runs in.

### Pick issues (optional)… / Add another issue… / Every open issue
Choose which issues a line runs in. **Every open issue** adds all the title's issues still open for adverts (not monthly website slots). Click the small cross on an issue to remove it.

### Option
Type an option name (for example "Option A", "Option B") to offer the client a choice. Lines without an option are part of every option. Each option gets its own total.

### As an email / As a Word document
How it goes to the client. As an email, the proposal is the email itself, so keep it to text, simple tables and a few pictures. As a Word document, it goes into BMI's template with the magazine's logo, header and footer. You can switch any time before it's sent.

### Formatting toolbar
On the page: **Heading** (turns a line into a heading, which starts a new section), Bold, Italic, Underline, highlight and text colours, Bullet list, Numbered list, Add a link, Clear formatting, Insert a table (asks how many rows and columns), Add a row, Add a column (click in the table first) and Insert a picture (PNG, JPG or GIF; large pictures are shrunk).

### Add a ready-made part
Puts a shaded box where your cursor is, with its own heading. (The same menu also has **Text, tables and pictures**, which adds a normal section you write yourself.) These fill themselves from live data every time you preview or send:
- **Package and prices**: your products, their issues and the total, as a table.
- **Price list**: products and prices from the rate card.
- **Audience numbers**: the brand's figures from the editorial plan's brand settings.
- **Coming issues**: the next issues, themes and booking deadlines.
- **Events and awards**: the brand's coming events and awards.
- **Examples of our work**: links from the examples library.

The Investment heading always shows the package table under it automatically.

### Clicking a shaded box
Opens a side panel showing what it will say. For a price list, **Choose the products to show** (it changes to **Done choosing** while the list is open) (nothing ticked shows the main print, sponsored and newsletter prices). For coming issues, **Choose the title**. For examples, **Choose the examples** with a sector filter (nothing ticked lets the Brain pick, the client's sector first) and an **Add or change examples** link that opens the library in a new tab. The panel also has **Move up**, **Move down**, **Remove** and **Done**.

### Change it with the Brain
Type or say what you want different (headings, tone, length, sections added or removed) and press **Apply**. **Speak** records up to two minutes and writes it down for you; press **Stop recording** when done. The example chips fill the box with a suggestion. Ready-made parts keep their place; only the wording around them is rewritten. After a change, **Undo** puts it back how it was. Only on drafts.

### Preview / Edit
**Preview** shows the proposal exactly as it will go out, with every ready-made part filled in, plus warnings for emails (more than 4 pictures, a very large email, or a table with more than 5 columns). **Edit** goes back to the editor. Unsaved changes are saved first.

### Start again
Writes every section again from scratch, using the current issue and products. Your edits to the wording are replaced (it asks first). Use it after changing the issue. Drafts only.

### Change the issue
In the right-hand panel. Choose a different issue or **No particular issue**. The wording isn't rewritten, so press **Start again** or ask the Brain to bring the new issue's details in.

### Open <client>
Opens the company's page.

### Save
Saves your changes. Greyed out until something has changed. Saving also re-prices rate card lines and works out any rate card offers again.

### Download Word file
Downloads the proposal as a Word document in the chosen template. Saves first if needed. Works on sent proposals too.

### Email it from Outlook
Opens **Email the proposal**: To, Cc (optional), Subject, a message (or, when sent as an email, the opening line that goes above the proposal), **Also attach it as a Word document** (email only), and **Remind me to follow up in (days)** (14 by default). **Send** sends it from your own connected Outlook. Only after it sends is it logged on the client and the reminder set. **Cancel** closes it.

### I've sent it myself
For a proposal you sent another way. Choose **Emailed the downloaded file** or **Another way**, set the follow-up days, and press **Log it**.

### Delete draft
Deletes a draft (it asks first). Sent proposals are kept on record and can't be deleted.

### They said yes: make the booking / They chose <option>: make the order
Shown once a proposal is sent. Opens a new booking already filled in from the proposal: the client, contact, products, issues and discounts. If the proposal has options, there's one button per option. Check the issues and prices, then confirm the booking as usual.

## How it works
- Rate card lines are always priced from the rate card on the server, whatever the screen shows. Own lines keep the price you typed.
- A line's total = quantity (or number of issues) x price, less its % off. Each option's total = its lines plus the lines in every option, less the % off the whole proposal. The headline total on the list is the first option's.
- Rate card offers (such as "book 3, save 20%") are applied by themselves when you save, per option and per title. They show as green lines and as negative amounts in the Word file. Expired offers are skipped.
- All prices are before VAT.
- The Brain drafts five sections: Introduction, Your history with us, What we propose, Investment, Next steps. If the Brain wording includes any figure it wasn't given (from the client's history, the rate card or your lines), that section is replaced with standard wording. If the Brain isn't switched on, standard wording is used.
- If you've set up **How you write**, new proposals follow it: sent the way you usually send, your ready-made parts added before Next steps, written in your tone.
- When a proposal is sent or logged, a "Proposal sent" note is added to the company with the products and total, a follow-up reminder is set for you (it also emails you), and the proposal locks. The Brain also notes which ready-made parts you removed, so it can learn your style.
- Sending from Outlook needs your Outlook connected, and the whole email (with pictures and any Word file) must be under 3 MB.
- Making a booking from a proposal: with rate card offers, the booking uses a package price equal to the option's total; otherwise it uses the item prices with the same discounts. Lines with no issues picked go into the proposal's issue.

## Common questions
**Q: How do I send a proposal by email?**
A: 1. Choose **As an email** at the top. 2. Press **Preview** to check it. 3. Press **Email it from Outlook**. 4. Check To, Subject and the opening line. 5. Press **Send**.

**Q: How do I offer the client two choices?**
A: 1. Add the products. 2. In each line's **Option** box, type "Option A" or "Option B". 3. Leave lines that go in both choices empty. 4. Press **Save**. Each option now has its own total.

**Q: Can I change a rate card price for one client?**
A: Not on a rate card line. Either take a **% off** that line, use **% off the whole proposal**, or remove it and use **Add my own line** with the agreed price.

**Q: I changed the issue but the text still mentions the old one.**
A: Changing the issue doesn't rewrite your text. Press **Start again** (this replaces your edits), or type "use the new issue's details" in **Change it with the Brain** and press **Apply**.

**Q: How do I add a table or picture?**
A: Click where you want it, then use **Insert a table** or **Insert a picture** on the toolbar. Click inside a table to use **Add a row** or **Add a column**.

**Q: The client said yes. What now?**
A: Open the sent proposal and press **They said yes: make the booking** (or the button for the option they chose). Check the new booking and confirm it.

**Q: I emailed the Word file myself. How do I record it?**
A: Press **I've sent it myself**, pick **Emailed the downloaded file**, set the follow-up days and press **Log it**.

**Q: Can I undo a change made by the Brain?**
A: Yes. Straight after the change, press **Undo** in the "Change it with the Brain" box.

**Q: Where can I see proposals I sent?**
A: On the Proposals list (Status shows "Sent <date>") and as a "Proposal sent" note on the client's company page.

**Q: Can I edit a proposal after it's sent?**
A: No. It's locked once sent. You can still download the Word file, or start a new proposal.

## If something doesn't work
- **Draft the proposal is greyed out**: choose a client first.
- **"Give every line a name and a price"**: one of your own lines is missing its name or price.
- **"... isn't on the rate card - add it as your own line instead"** or **"... is priced on request"**: that product can't be priced from the rate card, so add it as your own line.
- **"Nothing on its rate card"**: the title has no rate card prices for this year or next. Ask whoever looks after the rate card, or use your own lines.
- **"No upcoming issues in the editorial plan"**: the title's issues haven't been added to the editorial plan yet.
- **"One of the issues ... isn't in the editorial plan any more"**: an issue was removed. Take it off the line and pick another.
- **Send is greyed out**: your Outlook isn't connected (connect it in Settings > Email), or the To box is empty.
- **"This is over 3 MB with its pictures"**: make the pictures smaller, or download the Word file and attach it yourself.
- **"Outlook didn't accept the email, so nothing was sent or logged"**: try again in a moment.
- **Change it with the Brain says the Brain isn't switched on**: edit the text directly instead.
- **"The new version mentioned figures we can't check"**: the Brain tried to add numbers it wasn't given, so nothing was changed. Say it another way.
- **I can't find a colleague's proposal**: salespeople only see their own. Ask an admin or data manager.
- **Buttons are missing and I can't type**: the proposal has been sent, so it's locked.
- **A shaded box says "Couldn't show this block just now"**: try **Preview** again in a moment.
