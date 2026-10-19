---
title: Groups
screens: ["/groups", "/groups/[id]"]
summary: Contact groups and sub-groups (mailing lists, segments, panels): find a group, see its members, remove several at once, copy them into another group, export or mail-merge them.
sources: ["frontend/src/app/(app)/groups/page.tsx", "frontend/src/app/(app)/groups/[id]/page.tsx", "frontend/src/components/group-form-dialog.tsx", "frontend/src/components/group-members-table.tsx", "frontend/src/components/contact-selection-actions.tsx", "frontend/src/components/contacts/copy-emails-button.tsx", "frontend/src/components/delete-entity-button.tsx", "frontend/src/components/publication-quick-filter.tsx", "backend/app/api/routes/groups.py", "backend/app/services/contact_lookup.py", "backend/app/core/visibility.py"]
---

## What this screen is for
Groups are named lists of contacts, as in Act!: circulation lists, award panels, advertiser rosters, one-off mailing lists. Groups can sit inside other groups. Use this screen to find a group, check who's in it, tidy it up before a mailing, make a smaller group from it, export it to Excel, or send a mail merge to it.

## What you see
**The list**
- "Groups", with how many groups there are, a **Search group name...** box and **New group**.
- One indented list: each top-level group, with its sub-groups underneath it (marked with a small arrow). Each row shows the name, the description if there is one, and the number of members.
- **Previous** and **Next** for more pages (50 groups a page).

**A group's page**
- A **Groups** link above the name to go back to the list.
- The group's name and description, with **Export**, **Mail merge**, **Edit** and **Delete**.
- **Members (<n>)**: everyone in the group and its sub-groups - the same people **Export** and **Mail merge** use. If the group has sub-groups, a line underneath says how many are in this group itself. A table of **Name**, **Company** and **Job title**, with a tick box on each row. Someone who is only in a sub-group has a small "in <sub-group>" label next to their name; click it to open that sub-group.
- Members load 200 at a time. Below the table, "Showing <n> of <total>" and **Show <n> more** loads the next lot.

## Buttons and controls

### Search group name...
Type part of a group's name and press Enter.

### Which title (the switcher at the top of the app)
To see one database's groups, or all you can see, use the **All Titles** switcher at the top of the app.

### New group
Choose the **Database**, type a **Name** and an optional **Description**, then **Create group**. The group starts empty. To make a group with people already in it, tick them on the Contacts list (or in another group) and use **New group** in the selection bar instead.

### A group row
Opens the group's page.

### Export
Downloads every member as an Excel sheet, including the members of its sub-groups.

### Mail merge
Opens Mail merge with this group chosen as the contacts. It includes the members of its sub-groups. You can untick people there to leave them out of that one mailing without taking them out of the group.

### Edit
Change the group's **Name** and **Description**, then **Save changes**. You can't move a group to another database.

### Delete
Asks "Delete <group>?" and then deletes the group after you press **Delete**. The contacts themselves are not deleted, only their membership of this group. Sub-groups are kept but are no longer nested under it. This can't be undone.

### Tick boxes and the selection bar
Tick members (the top box ticks all the members shown so far). A bar appears with "<n> contacts selected" and:
- **Remove from this group**: takes all the ticked people out in one go. The list keeps your place. People who are only in a sub-group aren't removed - you're told how many were left, and need to open the sub-group to remove them.
- **Add to group**: copy them into another group (this group isn't offered). People already there are left as they are.
- **New group**: start a new, smaller group from them. Type a **Group name** and optional description, then **Create group**.
- **Export**: just the ticked people, to Excel.
- **Copy emails**: their addresses, ready for Outlook's Bcc box (unsubscribed, bounced and repeated addresses left out).
- **Mail merge**: just the ticked people.
- The X clears the selection.

### Name and Company in the members table
Click a name (or anywhere on the row) to open the contact. Click the company to open it.

## How it works
- Groups belong to one database (one title's contact book).
- What you see is limited by your access in Settings > Users. Someone given one group sees only that group and its sub-groups. Opening a group outside your access shows "not found". Administrators see everything.
- A group includes its sub-groups for **Export**, **Mail merge**, the contacts lookup and the members table on the group's page.
- Adding people to a group never removes them from the other groups they're in.
- Ways to put people in a group: tick them on Contacts or another group and use **Add to group** or **New group**; use **Add to group** on a contact's Groups tab; or choose a group when importing a file.

## Common questions
**Q: How do I add people to a group?**
A: Go to Contacts, look them up, tick them, press **Add to group** in the selection bar, pick the group and press **Add to group**. For one person, open them, click the **Groups** tab and press **Add to group**.

**Q: How do I remove lots of people from a group before a mailing?**
A: Open the group, tick everyone to remove, and press **Remove from this group**.

**Q: I only want to leave a few people out of this one mailing.**
A: Don't remove them from the group. Press **Mail merge** and untick them in step 2 (Contacts).

**Q: How do I make a smaller list from a big group?**
A: Open the big group, tick the people you want, press **New group**, name it and press **Create group**. Delete it after the mailing if you don't need it.

**Q: How do I get a group into Excel?**
A: Open it and press **Export**. To export some of them, tick them and press **Export** in the selection bar.

**Q: How do I copy a group's email addresses into Outlook?**
A: Tick the members (the top box ticks them all) and press **Copy emails**, then paste into Bcc.

**Q: Will deleting a group delete the contacts?**
A: No. Only the group and its memberships go. The people stay in the CRM and in their other groups.

## If something doesn't work
- **Create group is greyed out**: type a name.
- **The group doesn't open ("not found")**: it's outside the databases or group you've been given.
- **The member count on the group's list is lower than on the group's page**: the Groups list counts people put directly in each group; the group's page, Mail merge and Export also include its sub-groups.
- **Not everyone is in the table**: members load 200 at a time - press **Show <n> more** below the table.
- **There's no Bulk update in a group**: bulk update is on the Contacts list. Look the group up there with **Advanced search** (In group), then use **Bulk update**.
- **"No members yet"**: nobody is in this group or any of its sub-groups.
