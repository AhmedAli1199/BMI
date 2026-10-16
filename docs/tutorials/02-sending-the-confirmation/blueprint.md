# Video 2 - Sending the confirmation (DRAFT blueprint)

Status: **draft - not yet walked in the app.** Labels come from `backend/app/brain/help/sales-orders/booking-page.md`
(kept in step with the app's buttons by the help-coverage test). Before recording, walk the flow once
(HOW-TO-MAKE-A-VIDEO.md step 3), fix any wording or positions here, and fill in the QA checks marked "verify".

## Notes for whoever builds this

- **Starting point:** a confirmed Gate Gourmet booking that hasn't been sent (the end of lesson 1). The seed clears
  bookings, so preview.mjs makes it **off camera** first: in the sign-in context, fill the New booking form exactly as
  in lesson 1 (no overlay, normal speed) and press "Confirm the booking", note the booking's address, then start
  recording on that address.
- **No Outlook on the demo:** "Send" can't really send there. Step 06 points at Send and clicks **Close**. Check what
  the email window shows when Outlook isn't connected (the guide says it tells you to connect in Settings > Email): if
  that note is on screen, keep it out of the zoom, or change the voiceover to match what's visible.
- **Print or PDF opens a new tab**, which a recording of one tab won't show. Instead, go to the same address in the
  recorded tab (`/sales/deals/<id>/print`), then come back with `page.goBack()`.
- **"I sent it another way"** is in the "More" (…) menu. It records the confirmation as sent without emailing - this
  is the step that changes the status on camera.
- Roles: the salesperson sends the confirmation; Accounts only check the booking later, for invoicing.

````text
════════════════════════════════════════════════════════════════════
ANTIGRAVITY EXECUTION BLUEPRINT - VIDEO 02: SENDING THE CONFIRMATION
════════════════════════════════════════════════════════════════════

1. VIDEO METADATA
Title ............ Sending the confirmation
Series ........... BMI Brain - Sales Orders, lesson 2 of 17
Audience ......... Salespeople (role: Sales)
Goal ............. The viewer can check the confirmation, email it to the client from the booking page, and record
                   it as sent when it went another way.
Length ........... 1:42 (10 steps)
Viewport/voice ... as lesson 1 (1440 x 900, sign in as sally.parker@tutorial.bmi)
Starts on ........ /sales/deals/<id> - Booking 24NN: Gate Gourmet, Confirmed, not sent (made off camera)
Ends on .......... the same page, now showing the confirmation as sent

2. REAL UI (from the help guide - verify in the walk-through)
Booking page: H1 "Booking 24NN: Gate Gourmet"; buttons top-right "Change", "Email the confirmation" (highlighted
  while not sent), "Print or PDF", "More" (…). Status: green "Confirmed" + amber "· The confirmation hasn't been sent
  yet". After sending: "Confirmation sent <date> to <address>".
Print page (/sales/deals/<id>/print): the printable confirmation, with a "Print or save as PDF" button.
Email window (after "Email the confirmation"): "To" (daniel.weber@gategourmet.example), "Copy to (optional)",
  "Subject", "Message", buttons "Send" and "Close". The confirmation goes as a Word file. Production and accounts
  addresses from Confirmation details are always copied.
More menu: "Download as Word", "I sent it another way", "Rebook for next year", ...

3. STEP-BY-STEP SCENE CHOREOGRAPHY

STEP 00 · 0:00-0:09 · Chapter card
  Voiceover: "Sending the confirmation. Once a booking is confirmed, you send the client their confirmation from
    the booking page."
  Callout: ARCHETYPE D - Badge pill: [clapperboard] "Lesson 2" (primary navy). Headline: "Sending the confirmation".
  Cursor hidden. Behind: the booking page, blurred.

STEP 01 · 0:09-0:22 · Not sent yet
  Voiceover: "This is the booking from lesson one. It's confirmed, and the amber note says the confirmation hasn't
    been sent yet. Email the confirmation stays highlighted until it has."
  Target: "Confirmed" badge + "The confirmation hasn't been sent yet" (top-left), then "Email the confirmation"
    (top-right). Cursor glides from the note to the button and hovers. No click.
  Callout: ARCHETYPE A - pill BELOW the note. Badge pill: [mail] "Not sent" (amber). Text: "The amber note goes once it's sent".
  QA (verify): expect(getByText("The confirmation hasn't been sent yet")).toBeVisible();
               expect(getByRole("button", { name: "Email the confirmation" })).toBeEnabled();

STEP 02 · 0:22-0:31 · Check it first
  Voiceover: "To see what the client will get, click Print or PDF. The confirmation opens on its own page."
  Target: "Print or PDF" (top-right). Click -> the printable confirmation (recorded tab goes to /sales/deals/<id>/print).
  Callout: ARCHETYPE B - split-screen as the page appears. Badge pill: [file-text] "Preview" (primary navy).
    Headline: "Exactly what the client sees".

STEP 03 · 0:31-0:43 · The document
  Voiceover: "It shows the client's details and every item, with the issue it runs in and its price. Print or save
    as PDF saves a copy."
  Target: the items table (centre), then the "Print or save as PDF" button. Hover only - don't open the print window.
  Callout: ARCHETYPE C - pop-out of the items table. Badge pill: [list] "Items" (primary navy).
    Headline: "Taken straight from the booking".
  Verify: what the document actually shows at the top (address? contact? title?) and reword "the client's details".

STEP 04 · 0:43-0:49 · Open the email
  Voiceover: "Back on the booking, click Email the confirmation."
  Action: page.goBack(); glide to "Email the confirmation", click. The email window opens.
  Callout: ARCHETYPE A - pill LEFT of the button. Badge pill: [mail] "Email" (primary navy). Text: "Opens a ready-made email".

STEP 05 · 0:49-1:03 · Check the email
  Voiceover: "The email is ready: To has Daniel's address, and the subject and message are filled in. Change
    anything you need. The confirmation goes with it as a Word file."
  Target: the "To" box, then "Subject", then "Message" (ring moves down the three).
  Callout: ARCHETYPE C - pop-out of the email window. Badge pill: [paperclip] "Word file" (primary navy).
    Headline: "Production and accounts are always copied".
  QA (verify): expect(the "To" box).toHaveValue("daniel.weber@gategourmet.example");

STEP 06 · 1:03-1:14 · Send or close
  Voiceover: "Press Send and it goes from your own Outlook, and a note is added to the client's company. Close shuts
    it without sending."
  Target: "Send" (hover only - the demo has no Outlook), then "Close" (click). Window closes.
  Callout: ARCHETYPE A - pill ABOVE "Send". Badge pill: [send] "Your Outlook" (emerald). Text: "Sent from your own mailbox".

STEP 07 · 1:14-1:24 · Sent another way
  Voiceover: "Emailed it from somewhere else? Open the More menu, and choose I sent it another way. Nothing is
    emailed; it's just recorded."
  Target: "More" (…) top-right, click; the menu opens; click "I sent it another way".
  Callout: ARCHETYPE B - split-screen while the menu is open. Badge pill: [check] "Recorded" (primary navy).
    Headline: "Keeps the record straight".

STEP 08 · 1:24-1:34 · Now it's sent
  Voiceover: "The status now says when the confirmation was sent, and who to. Accounts check the booking
    separately, before it's invoiced."
  Target: the status line - now "Confirmation sent <date> to daniel.weber@gategourmet.example". Cursor rests beside it.
  Callout: ARCHETYPE C - pop-out of the status line. Badge pill: [circle-check] "Sent" (emerald).
    Headline: "Date and address saved".
  QA (verify): expect(getByText(/Confirmation sent .* to daniel\.weber@gategourmet\.example/)).toBeVisible();
               expect(getByText("The confirmation hasn't been sent yet")).toHaveCount(0);

STEP 09 · 1:34-1:42 · End card
  Voiceover: "That's the confirmation sent. Next, pencilling a booking in, and confirming it later."
  Callout: ARCHETYPE D - Badge pill: [arrow-right] "Next lesson" (primary navy). Headline: "Pencil it in, then confirm".
  Cursor hidden.
````
