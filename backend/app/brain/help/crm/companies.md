---
title: Companies
screens: ["/companies", "/companies/[id]"]
summary: The list of client and prospect companies, and each company's page with its details, people, history, notes and everything it has booked.
sources: ["frontend/src/app/(app)/companies/page.tsx", "frontend/src/app/(app)/companies/[id]/page.tsx", "frontend/src/components/company-form-dialog.tsx", "frontend/src/components/act-company-card.tsx", "frontend/src/components/act-subbar.tsx", "frontend/src/components/add-existing-contact-picker.tsx", "frontend/src/components/contact-form-dialog.tsx", "frontend/src/components/touchpoint-bar.tsx", "frontend/src/components/unified-activity-timeline.tsx", "frontend/src/components/field-change-history.tsx", "frontend/src/components/remind-me-dialog.tsx", "frontend/src/components/record-reminders.tsx", "frontend/src/components/sales/company-bookings.tsx", "frontend/src/components/sales/orders-table.tsx", "frontend/src/components/sales/order-sheet.tsx", "backend/app/api/routes/companies.py", "backend/app/api/routes/sales.py", "backend/app/core/visibility.py"]
---

## What this screen is for
Companies lists every account in the CRM: advertisers, agencies and prospects, across every title. Open a company to see its details, the people who work there, what has happened with it, its notes, and everything it has booked with BMI. From a company you can also start a mail merge to its people, build a proposal or start a new booking.

## What you see
**The list**
- "Companies", with how many accounts match, a **Search company name...** box and **Add company**.
- A table: **Company**, **Industry**, **Contacts** (how many people are linked) and **Source** (the database badge). 50 a page, with **Previous** and **Next**.

**A company's page**
- **Companies** above the name goes back to the list. Under the name: the industry and which database it's in.
- On the right: **Remind me**, **Mail merge**, **Build a proposal**, **New booking**, and **Previous company** / **Next company** arrows with "3 of 5".
- An amber strip with your own reminders about this company, if any.
- **Company details** in three columns (empty fields are hidden until you press **Edit Company**): Company Profile (Name, Industry, Phone, E-mail, Web Site), Headquarters Address, and Account Status & Scope (Category, Territory, Region, Employees, plus how many Linked Contacts and Logged Notes).
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

### New booking
Opens the blank booking form with this company already chosen (see the "New booking and change booking form" guide).

### Edit Company, Save Changes, Cancel
**Edit Company** makes the card editable: Name, Industry, Phone, E-mail, Web Site, the address, Category, Territory, Region and Employees. **Save Changes** saves; **Cancel** throws the changes away. The copy icon next to the phone or email copies it; the Web Site link opens the site in a new tab.

### History of changes
Who changed which company field, from what to what, and when.

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
The Act! custom fields stored on this company, under their stored names.

## How it works
- You only see companies in the databases you've been given. If your access is limited to a group of contacts, you see the companies those contacts work for. Administrators see every company. Opening a company outside your access shows "not found".
- A booking links to a company when its client name matches the company exactly, or when someone confirms a suggested match in the Review Queue, or when it's linked from the booking or item itself. Only linked bookings show on the Bookings tab.
- Every edit to the company's own fields is recorded in **History of changes**, with who made it.
- **Add existing contact** moves the person to this company; they're no longer linked to their old one.
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

**Q: How do I log a call with the company rather than a person?**
A: Click the **Activity & History** tab, press the "Log or schedule →" bar, choose **Log**, pick the type and result, and press **Save**.

## If something doesn't work
- **The company doesn't open ("not found")**: it's in a database you haven't been given access to.
- **No Bookings tab**: the order register couldn't be read just then. Reload the page.
- **Add to company is greyed out**: pick a person from the search first.
- **Add company is greyed out**: type a name.
- **A person I just added with Add existing contact isn't in the list**: reload the page.
- **The record arrows are greyed out**: you opened the company directly rather than from the list.
- **I can't delete a company here**: there's no delete button on the company page.
