---
title: Examples library, How you write and the proposal requests report
screens: ["/sales/proposals/examples", "/sales/proposals/style", "/sales/proposals/report"]
summary: The shared links proposals can show as examples, your personal writing style for drafted replies and proposals, and a report on proposal requests that came in by email.
sources: ["frontend/src/app/(app)/sales/proposals/examples/page.tsx", "frontend/src/app/(app)/sales/proposals/style/page.tsx", "frontend/src/app/(app)/sales/proposals/report/page.tsx", "frontend/src/components/sales/examples-library.tsx", "frontend/src/components/sales/writing-profile.tsx", "backend/app/api/routes/proposal_examples.py", "backend/app/api/routes/proposal_style.py", "backend/app/proposals/examples.py", "backend/app/proposals/style.py", "backend/app/automations/proposal_requests.py", "backend/app/automations/settings_registry.py"]
---

## What this screen is for
These three screens sit behind the Proposals list. The **Examples library** holds links to past pages and resources (like the media pack) that anyone can drop into a proposal. **How you write** teaches the Brain your own writing style, so drafted replies and proposals come out sounding like you. The **Proposal requests report** shows how many emails asking for prices or a proposal came in, how quickly they got a reply, and how many became bookings.

## What you see
**Examples library** (Proposals > **Examples library**)
- Brand tabs across the top (one library per brand, shared by everyone). It opens on The Business Travel Magazine, which starts with a ready-made set of links.
- **Check the links** and **Add a link** on the right.
- A search box, a sector filter, a type filter and **Show retired ones**. A count says how many are shown, and how many links are "not opening" (in amber).
- A table: What it is (with a "Resource" badge for resources, "retired" for retired ones, and whose page it was), Format, Sector, Link (**Open** in a new tab, an amber "not opening" warning, or a small tick when the link was checked and works) and a pencil to change it.

**How you write** (Proposals > **How you write**)
- A status strip: either your drafts use **the standard style**, or they're written in **your own style** (with the date it was set up).
- Step 1: **Show it some of your past proposals**, with the list of what you've added.
- Step 2: **Tell it how you work (optional)**.
- Step 3: **Let the Brain work out your style**.
- **Your profile**: everything the Brain will follow, which you can change.
- On the right: **What the Brain has learned** and **Where it's used**.

**Proposal requests report** (Proposals > **Report**)
- Period tabs: **Last 30 days**, **Last 90 days** (the default), **Last year**.
- Admins and data managers also see a person picker: **Everyone** or one salesperson.
- Six tiles: Requests, Replied to, Usual time to reply, Still waiting, Became bookings, Booked from them.
- A table by salesperson: Requests, Replied, Usual time, Not requests, Waiting (amber when above 0), Full proposals, Bookings (with their value).
- Two breakdowns: **By type of request** and **By magazine**.

## Buttons and controls
### Brand tabs (Examples library)
Switch between the brands' libraries.

### Check the links
Checks every link of this brand in the background. Refresh the page after a minute to see the results. Links are also checked automatically once a week.

### Add a link / pencil (Change link)
Opens a side panel with: **What it is**, **Link**, **Type** (an example of a past page, or a resource such as the media pack), **Format** (for example "Spotlight on", "Q&A"), **Sector** (helps suggest it to similar clients), **Whose page it was (optional)** and **Retired - don't offer it any more**. **Save** keeps it; **Cancel** closes the panel. Anyone can add or change links.

### Search, sector and type filters, Show retired ones
Narrow the table. Search looks at the name, format and client.

### Open
Opens the link in a new tab so you can check it.

### Upload files
Add past proposals or replies as Word, PDF, text, saved email or web page files. Each must be under 15 MB.

### Paste one
Paste the text of an email or proposal, give it a name, and press **Add it** (it needs a reasonable amount of text). **Cancel** closes the box.

### Find them in my Sent Items
Looks in your Outlook Sent Items for emails that read like proposals and adds the best ones.

### Bin icon (next to a sample)
Removes that sample.

### Speak it / Stop
Record your note instead of typing it. Press **Stop** when you've finished; it's written into the box.

### Save the note
Saves what you typed in step 2.

### Work out my style
Reads your samples and note and fills in the profile below. Nothing changes in your drafts yet. If the Brain isn't switched on, the standard profile is filled in instead for you to change by hand.

### Your profile fields
- **In a few words, how you write**, **Tone**, **Length** (short, medium, long) and **Usually sent** (as an email or as a Word document).
- **Greeting** ({first_name} is their name) and **Sign-off** ({my_first_name} is yours).
- **Direct clients' prices: % below the rate card** (0 to 50) and **Round those prices to the nearest** (£1, £10, £25, £50 or £100). Agencies always get the rate card price.
- **Things you always do** and **Things you never do**, one per line.
- **What goes in each kind of proposal**: tabs for Agency brief, PR pitch, General enquiry, Referral, After a call or event, Existing client and Full proposal. Tick what you include (free ways to work with us, audience numbers, prices, coming issues, examples, events and awards, media pack link, offer a call) and use the up and down arrows to set the order. Every tab except Full proposal also has **How you open** ({for_client} names an agency's client) and **How you close**.

### Use this profile
Saves the profile. From now on your drafted replies and new proposals follow it. "Not saved yet" shows while you have changes.

### Back to the standard style
Shown once you have a profile. Goes back to the standard style (it asks first). Your samples and note are kept, but what the Brain has learned is cleared.

### What the Brain has learned (tick boxes)
Each thing it has learned from your sent drafts. Untick one to undo it; it shows crossed out.

### Period tabs and Everyone / person chips (Report)
Change the time span, and (admins and data managers only) whose requests are counted.

### Salesperson name (Report)
Opens the Review Queue at the proposal request cards.

## How it works
- **Examples:** a link copied from an email with a security scanner's wrapping round it is cleaned up when saved, so clients see the real address. Links must start with https:// (or http://). Changing a link clears its check result. Broken and retired links are never suggested in a proposal. The **Examples of our work** part of a proposal picks a few from here, the client's sector first, unless you tick specific ones.
- **Style:** each person has their own profile; nobody else's is affected. You can add up to 12 samples. Only the writing is used: prices and figures in your samples are never copied into drafts. Any opening or closing wording that contains a figure is blanked.
- **Where your style is used:** replies drafted for proposal requests in your Review Queue (their order, greeting, opening, closing, sign-off, and direct-client prices from the rate card less your %, rounded), and new proposals (sent the way you usually send, your ready-made parts for a full proposal in your order, your tone).
- **Learning:** each time you send a drafted reply or proposal, the Brain notes what you took out and the sign-off you used. Something you take out 3 times in your last 6 is left out from then on. The same new sign-off used 3 times becomes yours.
- **Report:** a proposal request is an email the Brain spotted asking for prices, rates, a media pack or a proposal (the "Spot proposal requests" automation, off until an admin turns it on). Replied = sent from the card, answered another way, or turned into a full proposal. Usual time to reply is the middle value (half quicker, half slower). Became bookings = a booking made from that proposal, or any booking for that client made after the request (cancelled ones don't count). Values are before VAT.
- Salespeople see only their own requests in the report; admins and data managers see everyone's.

## Common questions
**Q: How do I add an example page to the library?**
A: 1. Open **Examples library** and pick the brand tab. 2. Press **Add a link**. 3. Fill in **What it is** and paste the **Link**. 4. Choose the format and sector. 5. Press **Save**.

**Q: A link has stopped working. What do I do?**
A: Press the pencil next to it and either paste a new link, or tick **Retired - don't offer it any more**, then **Save**. Broken links are never put into proposals.

**Q: How long does it take to set up my style?**
A: About 10 minutes. 1. Add three to ten past proposals with **Upload files**, **Paste one** or **Find them in my Sent Items**. 2. Optionally add a note. 3. Press **Work out my style**. 4. Check the profile. 5. Press **Use this profile**.

**Q: I give direct clients a better price than agencies. Can the Brain do that?**
A: Yes. In **Your profile**, set **Direct clients' prices: % below the rate card** and how to round, then press **Use this profile**. Agencies still get the rate card price.

**Q: The Brain keeps leaving out something I want.**
A: Look under **What the Brain has learned** and untick it. It goes back in.

**Q: I want to start over with my style.**
A: Press **Back to the standard style**. Your samples stay, so you can press **Work out my style** again.

**Q: Why does the report show nothing?**
A: Either no requests came in during that period, or proposal request spotting isn't switched on. An admin turns on "Spot proposal requests" in Automations settings.

**Q: Can I see a colleague's numbers?**
A: Only admins and data managers can. Salespeople see their own.

## If something doesn't work
- **"That file is over 15 MB"**: use a smaller file, or paste the text.
- **"We couldn't read that file"**: try a Word document or PDF, or paste the text.
- **"That doesn't have enough text in it to learn from"**: use a longer proposal.
- **"That's 12 already, which is plenty"**: remove one sample to add another.
- **Find them in my Sent Items doesn't work**: either Outlook couldn't be reached just now, or looking in Sent Items isn't set up for this account. Upload or paste instead.
- **Work out my style is greyed out**: add at least one sample or a note first.
- **Add it is greyed out**: the pasted text is too short.
- **Speak it doesn't record**: the browser can't record or the microphone isn't allowed. Type instead.
- **Save is greyed out on a link**: fill in both **What it is** and **Link**.
- **"The link needs to start with https://"**: paste the full web address.
- **The link check results don't appear**: the check runs in the background. Refresh after a minute.
- **I picked one person in the report and the others' chips vanished**: press **Everyone** first, then choose another person.
