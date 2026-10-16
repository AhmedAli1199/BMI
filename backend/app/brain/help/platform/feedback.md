---
title: Feedback button and board
screens: ["/feedback"]
summary: Telling the team what's broken, confusing or missing from any page (point at it, screenshots, voice), voting with Me too, and the board where everyone's feedback is tracked, downloaded and passed to GitHub.
sources: ["frontend/src/app/(app)/feedback/page.tsx", "frontend/src/components/feedback/feedback-widget.tsx", "frontend/src/components/feedback/feedback-board.tsx", "frontend/src/components/feedback/feedback-detail.tsx", "frontend/src/components/feedback/feedback-pins.tsx", "frontend/src/components/feedback/capture-overlay.tsx", "frontend/src/components/feedback/annotate-dialog.tsx", "frontend/src/lib/feedback-types.ts", "backend/app/api/routes/feedback.py", "backend/app/feedback/github.py"]
---

## What this screen is for
Every page has a **Feedback** button at the bottom right. Use it to tell the team something's broken, something's confusing, an idea, or something that looks wrong - and point at exactly what you mean. Everything sent lands on the **Feedback** board (Feedback in the menu), where everyone at BMI can see it, add their vote, comment and follow where it's up to. Administrators and data managers move each one along and mark it fixed.

## What you see
### The Feedback button and panel
- The **Feedback** button sits at the bottom right of every page (the **Ask the Brain** button sits just above it). A number on it shows how much open feedback there already is about this page. It steps aside while a pop-up or side panel is open, and doesn't appear on print pages.
- Pressing it opens the **Feedback** panel:
  - Four kinds to choose from: **Something's broken**, **I don't understand this**, **I wish it could…** and **Looks wrong**.
  - A box to type in, with a microphone button to say it instead.
  - **Point at it**, **Snap an area** and **Whole screen**.
  - What you've pointed at (with a pin) and your screenshots, each with a cross to remove it.
  - "Already reported? Add your vote instead of sending it again." - open feedback that looks like the same thing, as you type.
  - **Show the <number> open on this page**, when there is some.
  - At the bottom: which page it's about, and **Send**.
  - **Everyone's feedback** at the top opens the board in a new tab.

### The board (Feedback)
- Four count tiles: **Open**, **New**, **Looking at it** and **Fixed**. Press one to filter.
- Tabs: **Open**, **New**, **Looking at it**, **Fixed**, **Won't do** and **All**.
- A search box ("Search words, a page, a person or #12").
- Filters: **Every kind**, **Every page** (with how many open on each), the sort (**Newest first**, **Most votes first**, **Recently changed**, **Oldest first**) and **Only mine**.
- **Download feedback** and a line saying how many pieces are shown (and, if switched on, that each one is also a GitHub issue).
- A card for each piece: the first screenshot, its number, status and kind, the words, what was pointed at, the page, who sent it and when, and counts of screenshots, comments and votes. The vote count includes the sender.

Status colours: **New** (blue), **Looking at it** (amber), **Fixed** (green), **Won't do** (grey).

## Buttons and controls
### Feedback (the button on every page)
Opens the panel. It remembers which page you were on when you opened it.

### Something's broken / I don't understand this / I wish it could… / Looks wrong
Say what kind of feedback this is. Hover over one for a hint. You can change it later.

### Say it instead (microphone)
Records you speaking and types it into the box. Press it again (**Stop**) when you've finished.

### Point at it
The panel steps aside and a banner says "Click the thing you mean." As you move the mouse, whatever is under it is outlined and named. Click it to add it, with a close-up screenshot. Press Esc to stop. You can point at up to 10 things.

### Snap an area
Takes a picture of the page, then you drag a box over the part you mean. **Whole screen** in the banner uses all of it. The picture then opens in the mark-up window.

### Whole screen
Takes a picture of the whole page and opens it in the mark-up window.

### Mark up the screenshot (Arrow, Box, Draw, Hide, Undo)
Draw an **Arrow** or **Box** to point things out, **Draw** freehand, or use **Hide** to black out anything private before it's sent. **Undo** removes the last mark. Press **Add this screenshot** to keep it, or **Cancel**. Clicking a screenshot in the panel opens it again to mark it up. Up to 6 screenshots per piece of feedback.

### Me too
Adds your vote to feedback someone else sent, instead of sending the same thing again. Press it again to take your vote off (it reads **Voted** or **You said me too** while your vote is on). You can't vote on your own.

### Show the <number> open on this page
Puts numbered dots on the page where people pointed. Click a dot to see what was said, with **Me too** and **Open it**. The strip at the bottom says how many are open and how many aren't on screen right now; its cross (**Hide the dots**) removes them.

### Send
Sends it. You need at least some words, something pointed at, or a screenshot. You'll see "Thanks, that's feedback #<number>" with **See it** (opens it on the board) and **Send more**.

### Status tiles and tabs, search, filters, sort and Only mine
Narrow down the board. Search matches the words, the page, the person's name, or a number like #12.

### Download feedback
Downloads a zip of exactly what the board is showing (same tab, filters and search): a readable document with the screenshots linked, a file with everything for the developers, and the screenshots themselves. Large lists are fine - it's built a batch at a time.

### Show more
Loads the next batch of cards.

### A feedback card
Opens the full details in a side panel:
- **Open the page** - opens the page it's about in a new tab.
- **Show me on the page** - opens that page with numbered dots on what was pointed at.
- **GitHub issue** - opens it on GitHub, if it's been sent there.
- The pencil (**Change it**) - edit the kind and words. The sender, administrators and data managers can do this.
- **What they pointed at**, **Screenshots** (click one to see it full size), the votes and **Me too**.
- **Where it's up to** - administrators and data managers only: choose **New**, **Looking at it**, **Fixed** or **Won't do**, add an optional note, and press **Save**.
- **Try again** - administrators and data managers, if it couldn't be sent to GitHub.
- **Browser and recent errors** - the browser, screen, zoom, theme and the errors on the page in the few minutes before. Only the sender, administrators and data managers see this.
- **Comments** - anyone can add one with **Add comment**.
- **Delete** - asks you to confirm and can't be undone.

## How it works
- With each piece of feedback the app saves the page, what you pointed at (its label, the heading it's under, and where it's made in the app's code), your browser, screen, zoom and theme, and any errors from the last few minutes, so it can be fixed quickly. Everyone at BMI can see your feedback.
- Administrators get a notification (under the bell) for each new piece of feedback.
- When an administrator or data manager changes the status, the sender and everyone who said Me too get a notification. Saving only a new note, without changing the status, doesn't send one.
- A new comment notifies the sender and everyone who voted (except the person commenting).
- Feedback notifications appear under the bell only; they're never emailed.
- **Open** means New or Looking at it. The count tiles always show the whole board, whatever filters you've chosen.
- You can delete your own feedback while it's still New. After that, only administrators and data managers can.
- If GitHub is switched on, each new piece becomes a GitHub issue labelled with its kind, with the screenshots. Edits, comments and status changes are passed on, and **Fixed** or **Won't do** closes the issue.
- When you press **This didn't help** on an Ask the Brain answer, the question and answer arrive here as an **I don't understand this** piece of feedback.

## Common questions
**Q: How do I report a button that isn't working?**
A: 1. Press **Feedback** at the bottom right. 2. Choose **Something's broken**. 3. Press **Point at it** and click the button. 4. Say what happened. 5. Press **Send**.

**Q: Someone's already reported the same thing - what should I do?**
A: Press **Me too** on their feedback (it shows under "Already reported?" as you type, on the dots, or on the board). That adds your vote and you'll be told when it's fixed.

**Q: How do I hide private details in a screenshot?**
A: In the mark-up window, choose **Hide** and drag over the private part. It's blacked out before it's sent. To change a screenshot you've already added, click it in the panel.

**Q: How do I know when my feedback is fixed?**
A: You'll get a notification under the bell when its status changes. On the board, tick **Only mine** to see everything you've sent and where it's up to.

**Q: How do I see what's already been said about this page?**
A: The number on the **Feedback** button shows how many are open. Open the panel and press **Show the <number> open on this page** to see them as dots.

**Q: How do I mark feedback as fixed?**
A: Administrators and data managers: open the card, choose **Fixed** under **Where it's up to**, add a note saying what changed, and press **Save**.

**Q: How do I get all the feedback into a file?**
A: On the board, choose the tab and filters you want, then press **Download feedback**.

**Q: Can I change what I wrote?**
A: Yes. Open it on the board and press the pencil. You can also add more detail with **Add comment**.

## If something doesn't work
- **Send is greyed out.** Type something, point at something, or add a screenshot first.
- **"Couldn't take a picture of the page."** Some pages can't be captured. Describe it in words, or use **Point at it** instead.
- **"One of the screenshots is too big."** Snap a smaller area instead of the whole screen.
- **There's no Me too button.** It's your own feedback - you can't vote on it.
- **I can't change the status.** Only administrators and data managers can.
- **I can't delete my feedback.** You can only delete your own while it's still New. Ask an administrator or data manager.
- **I can't see the browser and errors section.** Only the sender, administrators and data managers see it.
- **The Feedback button has disappeared.** It steps aside while a pop-up, side panel or the Ask the Brain panel is open, and isn't shown on print pages. Close the pop-up and it comes back.
- **The microphone doesn't work.** Your browser may not allow recording, or the microphone is blocked. Type it instead.
- **There's no GitHub link.** GitHub isn't switched on, or this one hasn't been sent yet. Administrators and data managers can press **Try again** if it failed.
