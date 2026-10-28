---
title: Companies
screens: ["/companies", "/companies/[id]"]
summary: The list of client and prospect companies, and each company's page with its details, people, history, notes and everything it has booked.
sources: ["frontend/src/app/(app)/companies/page.tsx", "frontend/src/app/(app)/companies/[id]/page.tsx", "frontend/src/components/company-form-dialog.tsx", "frontend/src/components/act-company-card.tsx", "frontend/src/components/act-subbar.tsx", "frontend/src/components/add-existing-contact-picker.tsx", "frontend/src/components/contact-form-dialog.tsx", "frontend/src/components/touchpoint-bar.tsx", "frontend/src/components/unified-activity-timeline.tsx", "frontend/src/components/field-change-history.tsx", "frontend/src/components/company-owners.tsx", "backend/app/sales/ownership.py", "backend/app/sales/regions.py", "frontend/src/components/remind-me-dialog.tsx", "frontend/src/components/record-reminders.tsx", "frontend/src/components/sales/company-bookings.tsx", "frontend/src/components/sales/orders-table.tsx", "frontend/src/components/sales/order-sheet.tsx", "backend/app/api/routes/companies.py", "backend/app/api/routes/sales.py", "backend/app/core/visibility.py"]
---

## What this screen is for
Companies lists every account in the CRM: advertisers, agencies and prospects, across every title. Open a company to see its details, the people who work there, what has happened with it, its notes, and everything it has booked with BMI. From a company you can also start a mail merge to its people, build a proposal or start a new booking.

## What you see
**The list**
- "Companies", with how many accounts match, a **Search company name...** box and **Add company**.
- A table: **Company**, **Industry**, **Contacts** (how many people are linked) and **Source** (the database badge). 50 a page, with **Previous** and **Next**.

**A company's page**
- **Companies** above the name goes back to the list. Under the name: the industry and which database it's in.
- On the right: **Remind me**, **Mail merge**, **Build a proposal**, **Pitch from notes**, **New booking**, and **Previous company** / **Next company** arrows with "3 of 5".
- An amber strip with your own reminders about this company, if any.
- **Company details** in three columns (empty fields are hidden until you press **Edit Company**): Company Profile (Name, Industry, Phone, E-mail, Web Site), Headquarters Address, and Account Status & Scope (Category, Territory, Region, Employees, plus how many Linked Contacts and Logged Notes).
- **Who looks after them**: one line per magazine (Onboard Hospitality for Onboard companies; The Business Travel Magazine, Selling Travel, Selling Travel events and the Accessibility Awards for Selling Travel and Prospects companies), with the salesperson ("Nobody yet" if no one), a label saying which rule decided it (By product, Last contact, Last booking, By region, New business, Nobody yet, Not sure yet, Chosen by a person) and why in plain words.
- **History of changes**.
- Tabs, each with a count: **Associated Contacts (<n>)**, **Activity & History (<n>)**, **Company Notes (<n>)**, **Bookings (<n>)** and **User Fields (<n>)**.

## Buttons and controls

### Search company name...
Type part of a company's name and press Enter. Only the name is searched.

### Show all companies
Shown when you arrive from **Fix** on the Data Health page, where the list shows only companies without an industry. Press it to go back to the full list.

### Which title (the switcher at the top of the app)
To see one database's companies, or all you can see, use the **All Titles** switcher at the top of the app. The choice also applies to Contacts, Groups and Home.

### Add company
Choose the **Database**, then type **Name**, **Industry**, **Category** and **Website**. **Add company** saves it and opens the new company. The name is required.

### A row in the list
Opens the company. The record arrows on its page then step through the same list.

### Previous company, Next company
Step to the neighbouring company in the list you came from.

### Companies (above the name)
Back to the list.

### Remind me
Set a reminder about this company: a quick pick (**Tomorrow** to **1 year**, landing at 9am) or your own date and time, an optional note, and **Email me as well**. **Set reminder** saves it. It arrives under the bell when due.

### Mail merge
Opens Mail merge with everyone at this company chosen as the contacts.

### Build a proposal
Opens a new proposal with this company already filled in (see the "Proposals" guide).

### Pitch from notes
Opens **Pitch from meeting notes**: paste or type your notes from a meeting with them that wasn't recorded, then press **Draft the pitch**. The Brain reads the notes for what the client wants, the angle to take and what they responded well to (leaving out anything personal or off the record), finds the closest proposals BMI has sent before, and drafts a proposal that answers what they said: the magazine's template, its next open issue, products from the rate card for what came up, and your own writing style. Prices only come from the rate card, never from the notes or old proposals. It opens as a draft in Proposals with a note at the top to check it says what you agreed. Notes that are too short or don't say what the client wants are refused with the reason. For a call the notetaker recorded, use **Make a pitch** on the call's page instead.

### New booking
Opens the blank booking form with this company already chosen (see the "New booking and change booking form" guide).

### Edit Company, Save Changes, Cancel
**Edit Company** makes the card editable: Name, Industry, Phone, E-mail, Web Site, the address, Category, Territory, Region and Employees. **Save Changes** saves; **Cancel** throws the changes away. The copy icon next to the phone or email copies it; the Web Site link opens the site in a new tab.

### Who looks after them, Change, Back to the rules
The (i) next to the heading explains the rules. **Change** (administrators and data managers only) opens a side panel with a drop-down per magazine: pick the salesperson, or "Nobody yet (whoever takes it first)", and press **Save**. Your choice is kept; the nightly check won't change it. **Back to the rules** (shown under a magazine someone chose) lets the rules decide again. The Business Travel Magazine, Selling Travel events and the Accessibility Awards always go to Kirsty, Steve and David, so they aren't in the panel.

### History of changes
Who changed which company field, from what to what, and when. Adding, changing or removing a phone number, email or address is listed too.

### Associated Contacts tab
Cards for everyone linked to the company, with job title and email. Click a card to open the person.
- **Add existing contact**: search for someone already in the CRM and press **Add to company**. Their company is changed to this one.
- **Add contact here**: the quick add form with this company already set; just type the name, title, department, email and phone, then **Add contact**.

### Activity & History tab
The "Quick Touchpoint ... Log or schedule →" bar opens the Log or schedule dialog for this company. Underneath is a timeline of the company's history and scheduled activities, with filters **All Activity**, **Calls**, **Meetings**, **Notes**, **Emails** and **Tasks**. The bin on an item deletes it after you confirm.

### Company Notes tab
The company's notes, newest first. The bin deletes a note (no undo). Add a note with the Log or schedule dialog's **Note** tab.

### Bookings tab
Everything this company has booked, from the Sales Order Register, across every title and year.
- **Lifetime value**: every live booking linked to this company. Cancelled, contra and moved items aren't counted.
- **Bookings** (how many live items), **Last booked**, and the **Titles** booked.
- Small bars show the booked value per year (by the year of the issue or event), when there's more than one year.
- The table below lists every item, including cancelled and moved ones (struck through), with the edition, when it was booked, what, the salesperson, value, invoice and status. Click a row to open the item sheet on the right to check or change it (see the "All items and renewals" guide). Clicking the edition opens the edition page. Only administrators and data managers see **Delete** in the item sheet.
- If nothing is linked yet, the tab explains how bookings get linked, with a link to the **edition page**.

### User Fields tab
The Act! custom fields with a value on this company, with their names tidied up (for example "User3").

## How it works
- You only see companies in the databases you've been given. If your access is limited to a group of contacts, you see the companies those contacts work for. Administrators see every company. Opening a company outside your access shows "not found".
- A booking links to a company when its client name matches the company exactly, or when someone confirms a suggested match in the Review Queue, or when it's linked from the booking or item itself. Only linked bookings show on the Bookings tab.
- Every edit to the company's own fields is recorded in **History of changes**, with who made it.
- **Add existing contact** moves the person to this company; they're no longer linked to their old one.
- **Who looks after them** follows the rules agreed with Matt, in this order: (1) by product - The Business Travel Magazine and its events (including the Business Travel People Awards) are Kirsty's, Selling Travel events (Connect and the rest, worldwide) are Steve's, the Accessibility Awards are David's; (2) an existing client stays with whoever from that magazine's team was last in touch (a note, call, email or meeting in Act! or BMI Brain, on the company or any of its people) or last booked them, in the last 2 years (Automations > Sales Order Register > "Recent contact (years)"); (3) Onboard Hospitality: anyone else is new business for Craig; (4) Selling Travel: by the destination the client promotes, not where its office is (Visit Malta is a Malta client) - Sally: North America, Caribbean, UK, Pacific; Steve: Spain, Indian Ocean, Middle East and Gulf; David: Asia, Africa, Australasia, India and the sub-continent, Western and Eastern Europe, Scandinavia, Mexico and Central America, South America, ocean and river cruise, Channel Islands. The destination is read from the company's name, website and description. A client covering several regions goes to whoever was last in touch, however long ago; if nobody has been, to whoever takes it first. (5) Not sure (no destination found but the client is active, or someone was in touch long ago) -> administrators get a "Who looks after a client" card in the Review Queue, with a suggestion. It's worked out again every night, and each time the page is opened.
- Renewal reminders go to whoever looks after the client on that magazine, if they have a login.
- Deleting a company (not offered on this page) never deletes its people or bookings; they're just unlinked.

## Common questions
**Q: How do I find a company?**
A: Type part of its name in **Search company name...** and press Enter. Check the **All Titles** switcher at the top of the app isn't limiting you to one database.

**Q: How do I add a new person who works at this company?**
A: Open the company, stay on **Associated Contacts** and press **Add contact here**.

**Q: Someone in the CRM is listed under the wrong company. How do I fix it?**
A: Open the right company, press **Add existing contact**, find the person and press **Add to company**. Or open the person, press **Edit Record** and change Company.

**Q: How much has this client spent with us?**
A: Open the company and click the **Bookings** tab. **Lifetime value** is the total of every live booking linked to it.

**Q: Why isn't a booking showing on the company's Bookings tab?**
A: It hasn't been linked to this company yet. Open the item from the order register (or the edition page) and set its CRM company, or confirm the match in the Review Queue.

**Q: How do I email everyone at a company?**
A: Press **Mail merge** on the company page. Everyone there is chosen; untick anyone you want to leave out.

**Q: How do I start a proposal or a booking for this company?**
A: Press **Build a proposal** or **New booking** at the top of the company page.

**Q: Who looks after this client, and why?**
A: See **Who looks after them** under the company details: the salesperson for each magazine and the rule that decided it.

**Q: The wrong person looks after a client. How do I change it?**
A: Administrators and data managers press **Change** next to **Who looks after them**, pick the salesperson and press **Save**. It's kept until someone presses **Back to the rules**.

**Q: How do I log a call with the company rather than a person?**
A: Click the **Activity & History** tab, press the "Log or schedule →" bar, choose **Log**, pick the type and result, and press **Save**.

## If something doesn't work
- **The company doesn't open ("not found")**: it's in a database you haven't been given access to.
- **No Bookings tab**: the order register couldn't be read just then. Reload the page.
- **Add to company is greyed out**: pick a person from the search first.
- **Add company is greyed out**: type a name.
- **A person I just added with Add existing contact isn't in the list**: reload the page.
- **No Change button next to Who looks after them**: only administrators and data managers can change it.
- **Selling Travel says "Not sure yet"**: the Brain couldn't find the destination. Answer the card in the Review Queue, or press **Change**.
- **Someone left long ago still looks after a client**: only active salespeople count; their old notes don't. If they still show, someone chose them - press **Change**, then **Back to the rules**.
- **The record arrows are greyed out**: you opened the company directly rather than from the list.
- **I can't delete a company here**: there's no delete button on the company page.
