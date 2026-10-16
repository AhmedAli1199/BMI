# How to make a tutorial video (instructions for an agent)

This is the exact method used for Video 1. Follow it step by step. The result is a real recording of the real app,
driven by a script, with the cursor, highlights and callouts drawn on top, and a voiceover added afterwards. Nothing
on screen is generated or imagined - which is why it looks right.

## The idea in one paragraph

Don't ask a video model to draw the app. **Drive the real app with Playwright and record the browser.** Inject a
small overlay into the page (a visible cursor, an amber ring on the target, a callout pill, chapter cards, optional
subtitles). Every step has a fixed length from the blueprint; the script does the step's actions and then holds
until its time is up, so the timing is exact. It writes down when each step started (`final.timeline.json`). A
second script makes one voice clip per step with text-to-speech and lays each clip at its step's start, giving
`final.mp4` and `final.srt`. Change a word in the blueprint, run again, done.

```
blueprint.md  ──(words, timings, callouts)──▶  preview.mjs + preview/lib.mjs  ──▶  final.webm + final.timeline.json
                                                       (Playwright in the real app)            │
                                                                                               ▼
                                                              preview/voiceover.py  ──▶  final.mp4 + final.srt
```

## Files

| File | What it is |
|---|---|
| `docs/tutorials/README.md` | Curriculum, recording setup, selector rules, who-does-what |
| `docs/tutorials/preview/lib.mjs` | Shared: reads the blueprint, the overlay, cursor glide, ring, callout, cards, step timing, timeline |
| `docs/tutorials/preview/voiceover.py` | Voice clips (Gemini text-to-speech) + mixing into the MP4 + subtitles |
| `docs/tutorials/NN-name/blueprint.md` | The script for one video - the single source of words and timings |
| `docs/tutorials/NN-name/preview.mjs` | The actions for each step of that video |
| `backend/scripts/seed_tutorials.py` | The demo data every video is recorded on (and the reset between takes) |

## One-time setup

1. Demo database (never the live one) with the app running on it:
   ```
   docker compose up -d db
   docker compose exec db createdb -U postgres bmi_demo
   cd backend
   export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/bmi_demo
   alembic upgrade head
   python -m scripts.seed_tutorials --yes
   uvicorn app.main:app --port 8000          # keep running, same DATABASE_URL
   cd ../frontend && npm run build && npm start   # production build: no development badge in the corner
   ```
2. `ffmpeg` (`brew install ffmpeg`, or `pip install imageio-ffmpeg`) and `pip install google-genai`.
3. `export GEMINI_API_KEY=...` for the voice. Optional: `GEMINI_TTS_MODEL` (default `gemini-2.5-flash-preview-tts`;
   use whatever Google's current text-to-speech model is called) and `TUTORIAL_VOICE` (default `Kore`).
4. Playwright comes from `frontend/node_modules` (already installed). If it can't find a browser, pass the Chrome
   path as the second argument to `preview.mjs`, or run `npx playwright install chromium` in `frontend/`.

## Making the finished video (when the blueprint and preview.mjs exist)

```
cd backend && python -m scripts.seed_tutorials --yes && cd ..          # every take: same starting screen
node docs/tutorials/01-making-a-booking/preview.mjs http://localhost:3000 --final
python docs/tutorials/preview/voiceover.py docs/tutorials/01-making-a-booking
```

Output: `final.mp4` (video + voice) and `final.srt` beside the blueprint. If `voiceover.py` prints
`! step NN ... give it Ns more`, change that step's times in the blueprint (shift the later steps too), seed, record
and run it again - clips already made are reused unless their words changed.

Without `--final` you get `preview.webm` with subtitles, step names and the callout type on each pill - use that while
writing. `--final --subtitles` keeps the subtitles burned in.

## Making a NEW video - the procedure

Do these in order. Don't skip the checking steps: they are why it comes out right.

### 1. Get the facts right before writing anything

- Read the screen's help guide in `backend/app/brain/help/sales-orders/` (exact button names, rules, common
  questions) and `docs/HANDOFF.md`. For behaviour that depends on a setting, read its description in
  `backend/app/automations/settings_registry.py` and its default in `backend/app/core/config.py`.
- Follow "Who does what" in `docs/tutorials/README.md`. Example: the salesperson's **Confirm the booking** is the
  sign-off that the client said yes, and they send the confirmation; the accounts check is only for invoicing.
- Never describe something you haven't seen happen in the app.

### 2. Make the data

Add what the video needs to `backend/scripts/seed_tutorials.py`: it must be safe to re-run (only adds what's missing)
and must **remove what earlier takes created** (see how it deletes Gate Gourmet's bookings), because leftovers change
the screen (for example "Invoice details filled in from their last booking" appears and pushes the form down).

### 3. Walk the flow in the real app and write down what you see

Write a throwaway Playwright script that signs in as the tutorial user at 1440 x 900 and does the task once. At each
point, save a screenshot and dump what's on screen:

```js
const dump = () => page.evaluate(() => [...document.querySelectorAll("h1,h2,h3,label,button,a,input,select,textarea")]
  .filter((e) => !e.closest("[data-feedback-ui]")).map((e) => { const r = e.getBoundingClientRect();
    return r.width && r.height ? { tag: e.tagName, text: (e.getAttribute("aria-label") || e.textContent || e.placeholder || "").trim().slice(0, 80),
      box: [r.x, r.y, r.width, r.height].map(Math.round) } : null; }).filter(Boolean));
```

Record exactly: labels, placeholders, drop-down option texts (`select.locator("option").allInnerTexts()`), what fills
in by itself, totals before and after, the message shown after saving, and the badges/banners on the next page. Look
at the screenshots. Those are the only words the script may use. Do it again on a fresh seed to make sure the screen
is the same both times.

### 4. Write the blueprint

Copy `01-making-a-booking/blueprint.md` and keep its layout - `lib.mjs` reads it. The parts the script reads:

```
STEP 03 · 0:33-0:44 · Choose the contact          <- number, start-end (m:ss), title
  Voiceover: "Next, the contact. Type their name ..."   <- may wrap onto indented lines; ends with a quote at line end
  Callout: ARCHETYPE A - ...                       <- A, B, C or D
    Badge pill: [user-round] "Contact" (...). Text: "Taken from their CRM record".   <- or Headline: "..."
```

Rules:
- **Length of a step = words in its voiceover ÷ 2.5, plus 1.5 seconds**, rounded up. Steps follow on with no gaps.
- The voiceover only names what is on screen and highlighted at that moment, using the exact on-screen words.
  Teaching only: no selling, no "powerful", no "seamless".
- One action per step, and show its result: before → action → what changed (hold the change on screen).
- Callout text is 8-10 words at most and doesn't repeat the voiceover. Don't use the same callout type twice in a row.
- First step is a chapter card (D), last step is an end card (D) naming the next lesson.
- Add a `QA:` block per step with Playwright checks of what the step claims (see Video 1), and run them all against
  the app before going further. Every one must pass.

### 5. Write preview.mjs

Copy `01-making-a-booking/preview.mjs` and replace the steps. Each step is:

```js
await h.step(3, async (s) => {                       // 3 = STEP 03 in the blueprint
  const box = page.getByPlaceholder("Search for the contact…");
  await h.ring(box);                                  // amber ring around it
  await h.click(box);                                 // cursor glides there and clicks
  await h.type("Daniel");                             // types at a human speed
  await suggestion("Daniel Weber").waitFor();
  await h.click(suggestion("Daniel Weber"), 600);
  await h.ring(field("Contact email"));               // move the ring to what changed
  await h.callout(s, field("Contact name"), "above"); // the step's pill: below | above | right | left
});                                                   // then it holds until the step's time is up
```

Helpers (`lib.mjs`): `h.glide(locator | [x, y], ms)`, `h.click(locator, ms)`, `h.type(text)`, `h.ring(locator | null)`,
`h.callout(step, locator, side)`, `h.hideCallout()`, `h.card(step, show)` (full-screen chapter card from the step's
badge and headline), `h.ensure()` (put the overlay back after the page changes). In the file: `field(label)`,
`suggestion(text)`, `choose(select, optionText)`.

### 6. Preview, fix, repeat

```
cd backend && python -m scripts.seed_tutorials --yes && cd ..
node docs/tutorials/NN-name/preview.mjs http://localhost:3000
```

Watch `preview.webm`. If the terminal says a step ran over, give it more time in the blueprint or make its actions
quicker. Fix wording in the blueprint, not in preview.mjs. When it's right, make the finished video (above).

## Things that will trip you up (and the fix)

| Problem | Fix |
|---|---|
| Element IDs change every load (the UI library makes them) | Never select by id, except `#df-client`, `#df-items`, `#df-price`, `#df-doc` on the booking form |
| `getByLabel` can't find form fields | Labels wrap their inputs: use `field(label)` (XPath: the first input/select/textarea inside the label whose text starts with that) |
| A link drawn as a button (e.g. "New booking") isn't found as a link | It counts as a button: select it by address, `a[href="/sales/deals/new"]` |
| Search suggestions aren't `role=option` | They open in a pop-up at the end of the page: `body > div[style] button` with the text |
| Money text matches a drop-down option | `getByText("£2,990", { exact: true })` |
| Native drop-downs don't show in recordings | Click it (cursor), wait ~0.7 s, then `selectOption` - the choice appears, which reads fine |
| Something is off screen (the Booking total isn't sticky) | Scroll to a set position first (`window.scrollTo({ top: 200, behavior: "smooth" })`), check positions in a screenshot |
| The real mouse pointer isn't in the recording | The overlay draws its own cursor that follows `page.mouse`; always move with `h.glide` / `h.click`, never `locator.click()` |
| The overlay disappears after going to a new page | Call `await h.ensure()` after every navigation |
| The video starts with the sign-in page | Sign in in a separate context, save `storageState`, and record a new context that uses it (see preview.mjs) |
| First page load is slow and eats a step's time | Visit the pages once before recording (the "warm up" loop) |
| Each take looks a bit different | Re-run the seed before every take; it clears earlier takes |
| Development badge in the corner | Record against `npm run build && npm start`, not `npm run dev` |
| Voice too long for its step | `voiceover.py` warns; add the seconds in the blueprint, shift later steps, record again |

## Prompt to give the local agent

> Read `docs/tutorials/HOW-TO-MAKE-A-VIDEO.md`, `docs/tutorials/README.md` and Video 1
> (`docs/tutorials/01-making-a-booking/`) in full. Make lesson N from the curriculum the same way: get the facts from
> the help guide and settings, add its data to `seed_tutorials.py`, walk the flow in the real app and record exact
> labels and positions, write `blueprint.md` in the same layout with QA checks that all pass, write `preview.mjs`
> using the helpers, record a preview and check it against the blueprint, then run `--final` and `voiceover.py`. Use
> only words you saw on screen. Don't change `lib.mjs` or `voiceover.py` unless something in them is actually
> broken. Show me `preview.webm` before making the final version.
