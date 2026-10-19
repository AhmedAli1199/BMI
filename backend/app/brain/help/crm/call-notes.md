---
title: Call notes and the notetaker
screens: ["/calls", "/calls/[id]", "/calls/meetings"]
summary: Send BMI Notetaker into a Meet or Teams call (or let it join from your calendar), read the summary, actions and transcript afterwards, and save them onto the contact's history.
sources: ["frontend/src/app/(app)/calls/page.tsx", "frontend/src/app/(app)/calls/[id]/page.tsx", "frontend/src/app/(app)/calls/meetings/page.tsx", "frontend/src/components/calls/send-notetaker.tsx", "frontend/src/components/calls/call-actions.tsx", "frontend/src/components/calls/call-status.tsx", "frontend/src/components/calls/calls-tabs.tsx", "frontend/src/components/calls/calendar-setup.tsx", "frontend/src/components/calls/meetings-agenda.tsx", "frontend/src/components/calls/notetaker-check.tsx", "backend/app/api/routes/calls.py", "backend/app/api/routes/calendar.py", "backend/app/services/calendar_sync.py", "backend/app/services/notetaker.py", "backend/app/automations/call_notes.py"]
---

## What this screen is for
BMI Notetaker is a guest that joins your Google Meet or Microsoft Teams call, records it, and writes up the notes when it ends: a summary, the next step, key points, decisions, money and dates mentioned, who's doing what, and the full transcript. **Meetings** is a calendar of connected Google and Outlook meetings, showing what the notetaker will do with each: administrators and data managers see everyone's (the description says "Everyone's meetings in one shared calendar"), everyone else sees their own ("Your meetings from your connected calendar"). **Recorded calls** lists the calls it has been in. Notes can be saved onto the contact's history in one click.

## What you see
**Meetings** (Call notes > **Meetings**)
- For administrators, a **Notetaker check** button at the top right.
- **Send the notetaker**: a box to paste a meeting link.
- **Your calendars**: Outlook Calendar and Google Calendar, each "Not connected", connected (with the email and when it was last read), or in red if it needs reconnecting. Below: **When I have a meeting with a Meet or Teams link**.
- The meetings list, grouped by day, from yesterday to two weeks ahead, with a filter sidebar and search. Each meeting shows the time (or "All day"), title, a lock if it's private, the call type (Google Meet, Microsoft Teams, Zoom), a **link** to join, who from BMI is in it ("(organiser)", "(declined)"), outside guests, the matched contact and company (they open in a new tab), and a coloured line saying what the notetaker will do or did:
  - green: will be recorded, or recorded (notes are in Call notes);
  - amber: in the call now, writing up, or should be joining now;
  - red: not recorded, with why (not let in, failed, never joined, never sent);
  - grey: won't be recorded, with the rule that stopped it (no meeting link, all-day, skipped, private, internal, cancelled).

**Recorded calls** (Call notes > **Recorded calls**)
- The same **Send the notetaker** box (or a note that it isn't connected yet).
- **Recent calls**: **Call** (title and summary), **With** (contact and company), **Status**, **When** (and whose call it was).

**A call's page**
- The title, a status label, the call type, the **meeting link** and who was in it.
- On the right: a **Contact** picker, **Stop recording** (while it's in the call) and **Save to history** (once notes are ready).
- While live, a line saying what's happening (on its way, waiting to be let in, recording, writing up). The page refreshes itself.
- **Summary** (with Next step, Key points, Decisions, Money mentioned, Dates mentioned), **Who's doing what** (each task, who and when, plus "Their interest": Interested, Neutral or Not keen) and the **Transcript** with times and speakers.

## Buttons and controls

### Send the notetaker: Meeting link, What it's about (optional), Who it's with (optional), Send
Paste a Google Meet or Teams link, optionally add a title and pick the contact, then press **Send**. The notetaker joins as "BMI Notetaker" and you're taken to the call's page. Someone in the call may need to let it in from the waiting room.

### Meetings, Recorded calls
The two tabs of Call notes.

### Connect, Reconnect, Disconnect (Your calendars)
**Connect** links your Outlook or Google calendar. It is read-only: BMI Brain only looks at your meetings and never changes them. **Reconnect** appears when a connection has stopped working. **Disconnect** asks to confirm, then removes that calendar's meetings from the shared calendar.

### Check now
Reads your connected calendars again straight away (they're read every few minutes anyway).

### When I have a meeting with a Meet or Teams link
Your recording preference:
- **The notetaker joins automatically**
- **Just remind me**: a notification about 10 minutes before, so you can press **Record** if you want notes.
- **Do nothing**
It saves as soon as you choose.

### Record, Skip, Undo (on a meeting)
For a meeting that hasn't ended and has a Meet or Teams link. **Record** sends the notetaker to this one meeting; **Skip** stops it for this one meeting. **Undo** goes back to your usual setting. Not shown for private meetings, Zoom, all-day events, meetings with no link, or where everyone from BMI declined.

### Filters and search (Meetings)
Search by title, person or company. Filter by **Who from BMI**, **Notetaker** (**Meant to be recorded** / **Not meant to be recorded**), **Call type** (Google Meet, Microsoft Teams, Zoom, No meeting link) and **Whose** (**Only my meetings**).

### The status label on a meeting
Opens that meeting's call page.

### Contact (on a call's page)
Links the call to a contact (or clears it). Needed before **Save to history**.

### Stop recording
Asks the notetaker to leave the call now. The notes follow a few minutes later.

### Save to history
Saves the notes onto the linked contact's history as a "Meeting Held" entry, and adds a reminder for you for each thing to do, due at 9am on the day agreed in the call (for example "by Friday", "next week" or "14 Nov"), or the next working day if no day was mentioned. Its Review Queue card is closed too. Afterwards it says "Saved to the contact's history".

### meeting link
Opens the original meeting link in a new tab.

### Notetaker check (administrators only)
Opens a side panel listing everything the automatic notetaker needs and whether each is working (the notetaker service can be reached, results can come back, the calendar job is running, when each calendar was last read), plus **Missed in the last 7 days** with the reason for each. **Check again** runs it again.

### Clear meeting history (administrators only, in Notetaker check)
After you confirm, removes every meeting on the list and calls off notetakers that were booked but haven't joined. Calendar connections stay, and calendars are read again straight away. Calls that were recorded keep their notes.

## How it works
- The calendars are read every few minutes. The same meeting in several people's calendars (same link and start time) shows once, with everyone from BMI who's in it. A moved meeting shows at its new time.
- About 20 minutes before a meeting, everyone at BMI in it gets a notice that the notetaker will join. The notetaker itself is sent a minute or two before the start, the same way as pasting a link by hand, and asks to join a minute or so early (an administrator can change this in Automations > Call notes). A meeting added late is still joined up to 30 minutes after it started.
- Whose preference counts: if someone from BMI organised the meeting, theirs decides. Otherwise it's recorded if someone from BMI who is going has **The notetaker joins automatically** and nobody going has **Do nothing**; if you disagree, it isn't recorded and you're reminded instead, so anyone can press **Record**. Pressing **Record** always records it. It's not recorded if it was skipped, cancelled, all-day, has no Meet or Teams link (Zoom isn't supported yet), everyone from BMI declined, everyone marked it private, or only BMI people are in it, unless an administrator has switched private or internal meetings on in Automations > Call notes.
- Private meetings show to others only as "Private meeting".
- Administrators and data managers see everyone's meetings and calls. Everyone else sees their own meetings, calls they sent, and calls of meetings they were in.
- When notes are ready, everyone from BMI who was in the meeting gets a notification, and a Call notes card goes to the Review Queue (filters: call type, their interest, whether a contact is linked; sorted by call date) with **Save to history** and **Not needed**. If the notetaker couldn't record, the person who sent it is told.
- The contact is matched from the guests' email addresses where possible. If you link the contact on the call's page later, its waiting Review Queue card shows them too.
- **Save to history** only saves once; pressing it again (here or in the Review Queue) doesn't add a second entry.

## Common questions
**Q: How do I get notes from a call I'm about to have?**
A: Copy the Meet or Teams link, go to Call notes, paste it into **Meeting link**, pick the contact under **Who it's with (optional)**, and press **Send**. Let "BMI Notetaker" in when it asks.

**Q: How do I get it to join all my client calls automatically?**
A: On **Meetings**, press **Connect** for your Outlook (or Google) calendar, then choose **The notetaker joins automatically**.

**Q: I don't want one meeting recorded.**
A: Find it on **Meetings** and press **Skip**. **Undo** puts it back.

**Q: How do I put the notes on the client's record?**
A: Open the call, pick the person in **Contact** if it isn't linked, then press **Save to history**. Or press **Save to history** on its card in the Review Queue.

**Q: Where's the transcript?**
A: At the bottom of the call's page, under **Transcript**.

**Q: Can I stop it recording part-way?**
A: Yes, press **Stop recording** on the call's page, or remove it from the meeting yourself.

**Q: Why does a meeting say "Not recorded - the notetaker wasn't let into the call"?**
A: Nobody admitted it from the waiting room. Next time, accept "BMI Notetaker" when it asks to join.

## If something doesn't work
- **"The notetaker isn't connected yet"** or the send box is missing: an administrator needs to connect the notetaker service.
- **Connect isn't there, it says "Not set up yet - an administrator needs to add it"**: that calendar type hasn't been set up for BMI yet.
- **A calendar shows in red**: press **Reconnect** and sign in again.
- **Save to history is greyed out**: link a **Contact** first.
- **"The notes aren't ready yet."**: wait until the status says completed; the page refreshes itself.
- **No Record or Skip buttons on a meeting**: it has ended, is private, is all-day, has no Meet or Teams link, is a Zoom call, everyone at BMI declined, or the notetaker is already in it.
- **A Zoom meeting isn't recorded**: Zoom isn't supported yet.
- **An internal meeting isn't recorded**: meetings with only BMI people are off unless an administrator switches them on, or you press **Record** on that meeting.
- **I can't see a colleague's meetings**: only administrators and data managers see everyone's.
- **No Notetaker check button**: only administrators see it.
