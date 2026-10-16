---
title: Ask the Brain
screens: ["/brain", "/brain/activity"]
summary: The Brain beside every page - ask how anything works, why a booking is the way it is, or about clients and sales figures; point at things, add screenshots or speak, use Show me, and tell the team when an answer didn't help.
sources: ["frontend/src/app/(app)/brain/page.tsx", "frontend/src/app/(app)/brain/activity/page.tsx", "frontend/src/components/brain/brain-provider.tsx", "frontend/src/components/brain/brain-chat.tsx", "frontend/src/components/brain/brain-page.tsx", "frontend/src/components/brain/brain-markdown.tsx", "frontend/src/components/brain/show-me.ts", "backend/app/api/routes/brain.py", "backend/app/brain/access.py", "backend/app/brain/prompt.py", "backend/app/brain/runner.py", "backend/app/ui_sections.py"]
---

## What this screen is for
**The Brain** is BMI Brain's assistant. Ask it in plain words how anything works ("How do I make a new booking?"), why a booking is the way it is ("Why can't I edit this?"), or about clients and sales ("What did Caribbean Journal last buy, and at what rate?", "How much have we booked so far this year?"). It opens as a panel beside any page, so you can keep working while you read, or on its own page (**Chat with the Brain** in the menu). It only answers about what you're allowed to open yourself, and links to where each answer comes from.

## What you see
### The Ask the Brain button and panel
- The **Ask the Brain** button sits at the bottom right of every page, just above **Feedback**. **Ctrl+J** (**⌘J** on a Mac) opens and closes the panel from anywhere.
- The panel opens on the right; on a wide screen the page moves over to make room. Along the top: **Your conversations** (clock), **New conversation**, **Open on its own page** and **Close**.
- Before you ask, it greets you and suggests a few questions people usually ask on the page you're on. "You're on: <screen>" says which screen it thinks you're looking at.
- Answers stream in as they're written. While it works, you see its steps (for example "Reading the guide…") and "Thinking…".
- Answers use numbered steps, button names in bold, green **Tip** boxes and amber **Note** boxes, links that open in a new tab, and small **Show me** buttons next to buttons on your screen. Under the latest answer there may be up to three follow-up questions to press.
- Under each answer: thumbs up (**Helpful**), thumbs down (**Not helpful**), **Copy the answer** and **This didn't help**.
- At the bottom: the question box, **Send** (the arrow), **Point at it**, **Screenshot** and **Speak**. Anything you've pointed at or captured shows above the box, each with a cross to remove it.

### The Chat with the Brain page
The same chat, full size, with your conversations listed on the left and **New conversation** above them. Administrators also see **What it's been asked**.

### Questions people asked (administrators only)
- Four tiles for the last 14 days: **Answers (14 days)**, **Helpful / not**, **Average time to answer** and **Served from the cache** (how much of what it reads each time was already cached - cheaper and quicker; higher is better).
- A line saying how many pieces of notes and history it can search, whether it can search by meaning or only by exact words, and when that was last updated.
- Every question from the last two weeks: who asked, when, the page, what it looked up, how long it took, how much was cached, the rating, "Didn't answer" when it couldn't, and a **Feedback** link when someone pressed **This didn't help**.

## Buttons and controls
### Ask the Brain (button) / Ctrl+J
Opens the panel. **Ctrl+J** opens or closes it from any page.

### Send (arrow) / Enter
Sends your question. Enter sends; Shift+Enter starts a new line. While it's answering, **Stop** appears so you can cancel.

### Point at it
Click the thing on the page you're asking about (the panel stays open). It's added with a close-up screenshot. Ask "What does this do?", or just press Send - with nothing typed it asks "What is this and how do I use it?". Press Esc to stop pointing. Up to 4 things at a time.

### Screenshot
Takes a picture of the page; drag a box over the part you mean, or press **Whole screen**. Then mark it up (**Arrow**, **Box**, **Draw**, **Hide** to black out anything private) and press **Add this screenshot**. Up to 3 screenshots per question.

### Speak
Records your question and types it into the box. Press **Stop** when you've finished, check the words, then send.

### Suggested questions and follow-ups
Press one to ask it straight away.

### Show me
Highlights that button or link on your page for a few seconds (click anywhere to stop). If it isn't on screen it tells you - it may be inside a menu, a closed panel or another tab.

### Helpful / Not helpful
Rates the answer, which the team reviews. Press the same one again to take it back. Pressing **Not helpful** also opens the box to tell the team.

### This didn't help
Opens "Tell the team, so the answer (or the screen) gets better." Add what you needed (optional) and press **Send to the team**, or **Not now**. Your question and the answer become a piece of feedback, and the answer shows "Sent to the team (#<number>)" with a link to it.

### Copy the answer
Copies the answer's text.

### Your conversations (clock)
Lists your last 50 conversations, newest first. Press one to open it. The bin (**Delete <title>**, shown on hover) deletes one.

### New conversation
Starts a fresh chat. Earlier ones stay under **Your conversations**.

### Open on its own page
Opens the current conversation on the Chat with the Brain page in a new tab.

### What it's been asked
Administrators only, on the Chat with the Brain page. Opens the activity page described above. Links on it (the page, **Feedback**) open in a new tab.

## How it works
- **It only answers about what you can open yourself.** Your role, your database access and the sections an administrator has hidden for you (Settings > Sections people see) all apply. Ask about something outside that and it replies "You don't have permission to view that." and says nothing more about it. For example, Sales users can't ask about Data Health, the Automations Hub, the Xero connection or user accounts; only administrators can ask about the team page and section settings.
- It reads the records as you: a salesperson asking about clients gets the same view they'd have on screen.
- It knows the page you're on, the record on it (a booking, item, edition or proposal), what you pointed at and the last few messages that appeared on screen, so "this booking" means the one in front of you.
- For a booking, it checks the real booking - why it's locked, what Accounts still needs, when each item gets invoiced - rather than giving a general answer. It knows when you're the Accounts person.
- Figures (booked, invoiced, commission, this year against last, the July-June financial year) come from the same sums the screens use, so they match. Money is in pounds before VAT. It says which period a figure covers.
- It can't change anything yet - no creating, editing or sending. It tells you where to do it instead.
- If the records don't say, it says so rather than guessing. If a name could mean more than one client, it asks which.
- **Show me** buttons only appear for labels that really exist on that screen.
- Conversations are private to you. Administrators can see the questions and answers on the activity page, to improve the help.
- Screenshots and recordings are sent with your question so it can read them.
- If no key for the Brain has been added on the server yet, the panel says it isn't switched on and you can't send.

## Common questions
**Q: How do I ask about a button I don't understand?**
A: 1. Press **Ask the Brain** (or Ctrl+J). 2. Press **Point at it**. 3. Click the button. 4. Type your question, or just press Send.

**Q: Can it tell me why I can't edit a booking?**
A: Yes. Open the booking, press **Ask the Brain** and ask "Why can't I edit this?". It looks at that booking and gives the actual reason, and what you can do instead (for example **Request a change**).

**Q: Can I ask about a client?**
A: Yes, for clients you can see. Ask things like "What did <client> last buy and at what rate?" or "What was said in the last call with <client>?". Answers link to the company, booking or note they came from.

**Q: How do I find an old conversation?**
A: In the panel, press **Your conversations** (the clock), or open **Chat with the Brain** in the menu and pick it from the list on the left.

**Q: The answer was wrong or unhelpful - what should I do?**
A: Press **This didn't help**, say what you needed, and press **Send to the team**. It goes to the Feedback board so the help or the screen can be fixed.

**Q: Can I talk to it instead of typing?**
A: Yes. Press **Speak**, say your question, press **Stop**, check the words and send.

**Q: Why does it say "You don't have permission to view that."?**
A: That area is outside what you can open - your role doesn't include it, it's outside your database access, or an administrator has hidden that section for you. Ask an administrator if you need it.

**Q: Can it make a booking or send an email for me?**
A: Not yet. It explains how to do it and where, but it can't change anything itself.

## If something doesn't work
- **It says the Brain isn't switched on yet.** An administrator needs to add the Brain's key on the server.
- **"You don't have permission to view that."** See the question above.
- **Show me says the button isn't on the screen.** It may be inside a "..." menu, a closed panel or another tab. Open it and press **Show me** again.
- **"Couldn't take a picture of the page."** Describe it in words, or use **Point at it**.
- **"One of the screenshots is too big."** Drag a smaller box.
- **"That's a very long question."** Split it into a few shorter questions.
- **"We couldn't turn that into words just now."** or the microphone doesn't start - type your question instead, or check your browser allows the microphone.
- **The Ask the Brain button has gone.** It steps aside while a pop-up or the Feedback panel is open, and isn't shown on the Chat with the Brain page itself or on print pages. Ctrl+J still works.
- **I can't see What it's been asked.** It's for administrators only.
- **Couldn't get an answer just now.** Try again in a moment.
