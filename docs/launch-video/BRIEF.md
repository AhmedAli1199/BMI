# BMI Brain - launch film: director's brief

**What:** a 45-second film introducing BMI Brain to the people at BMI who will use it (sales, accounts, editorial,
production, admins). Not public.
**Feeling we want:** "wow, that's ours?" Premium, calm, confident. Simple story, high polish.
**Style source:** the Nitrosend launch film (saasexplain.com/work/claude-email.mp4, 64s, 1920x1080, 29.97fps). We copy
its *craft* (light, depth, motion, pacing). We do not copy its colours, logo or content: those are BMI's.

---

## 1. What the reference does (studied frame by frame)

| Time | What happens | The technique |
|---|---|---|
| 0-3s | White product cards (an email builder) drift in at an angle; a cursor drags an image in | 2.5D tilted UI cards, cursor choreography, shallow depth of field |
| 3-5s | Logo mark spins on a hot orange glow; "Hi, How can I help you?" slides through | Logo reveal, big kinetic type with a fast slide and motion blur |
| 5-10s | A prompt box; text **types itself**; cursor clicks Send | Typewriter text, cursor click with a press-in |
| 10-14s | The result (an onboarding email) appears as a floating card; camera pans down a stack of cards | Camera push and tilt, card stack with blur on everything not in focus |
| 14-16s | Wordmark "nitrosend" types out, then the logo mark lands | Text-on, logo lockup |
| 16-20s | Prompt again; a checklist builds: spinner → tick, "12-step onboarding", "Brand voice applied" | Staggered list, loading spinner resolving to a tick |
| 20-27s | The steps become a **vertical flow** of cards joined by thin lines; camera glides down it | Node flow, connector lines drawing on, vertical camera pan |
| 27-30s | One email card flies into an envelope icon; a red "1" badge pops | Object morph, notification pop with overshoot |
| 30-37s | Camera **pulls back** to a whole canvas of flows (Emails, Newsletters, Transactional) | Reveal by pull-back: "it's a whole system" |
| 37-41s | A frosted-glass button "Automated" with Figma-style selection handles | Glassmorphism, design-tool UI as decoration |
| 41-44s | A headline in a **monospaced** font in a blue selection box is retyped by a named cursor ("John"): Weekly → Week → Monthly | Live-editing gag, multiplayer cursor |
| 44-50s | The email in a browser window, then a phone: "Every ··· Device", then "Dark ··· Mode" on black | Split words either side of the device, hard colour flip to dark |
| 50-53s | A small black pill sits in the middle while big orange rings pulse outwards | Radial pulse / ripple |
| 53-56s | Numbers count up (30 → 82 → 255 → 342) as a line chart draws | Counter roll, line draw |
| 56-59s | "Works from any AI agent": the logo in the centre morphs from one to the next | Logo morph carousel |
| 59-64s | Logo + wordmark + tagline, then "Try free → nitrosend.com" pill | End card lockup, hold |

**The look in one line:** a pale off-white world (#F2F2F4-ish) with huge, soft, out-of-focus colour blobs (orange, red,
yellow) drifting at the edges; crisp white rounded cards with soft long shadows float in front; one clean sans-serif;
lots of empty space; every move eases out smoothly; the camera is always slightly moving.

**Pacing:** a new idea every 2-4 seconds; holds of about 1 second on each "result"; cuts and pops land on the beat.

---

## 2. BMI's look for motion

### Colour: "blue hour" instead of "sunset"

The reference's warm orange aurora becomes a BMI blue aurora. Same softness, same off-white canvas.

| Role | Colour | Where it comes from |
|---|---|---|
| Canvas | `#F4F6FA` (cool off-white) | Morning theme background, lifted |
| Deep blob | `#132C6B` BMI navy | `--primary` (Morning) |
| Bright blob | `#0099E5` BMI blue | `--ring`, the sidebar highlight |
| Glow / highlight | `#6CC8F5` (BMI blue, lighter) | mixed from #0099E5 + white |
| Warm accent (sparingly: celebrations only) | `#E8A33D` | close to `--warn`, so it feels like ours |
| Text | `#0E1424` near-black; `#5B6270` grey for secondary | `--chart-4` |
| Dark-mode beat | `#0B0E14` background, `#4EA8DE` blue | Night theme |

Rule: blobs are navy + blue + glow only. Warm amber appears in exactly two places: the confetti and one blob in the
celebration shot. Restraint is what makes it look expensive.

### Type

- **Geist** (the app's own font) for everything. Headlines Geist SemiBold, tight tracking (-3%), sentence case.
- **Geist Mono** for one gag only: the mail-merge field `{{first_name}}` (mirrors the reference's mono retype shot).
- Big type is BIG: headline words at 120-160px on a 1080p frame. Small UI text inside cards stays real-size and
  readable when the camera pushes in.

### The hero: the Brain

The reference's logo mark (the orange asterisk) is a static symbol. Ours is better: a **character**. The Brain
(direction B, `frontend/src/components/brain/brain-buddy.tsx`) is our mascot and plays the role of the reference's
logo mark in every place it appears (the opening, the "how can I help" moment, the pulse, the end card).

- Draw it from that SVG so it's identical to the app. Recolour for the film: outline `#132C6B`, body
  `color-mix(#132C6B 12%, white)`, sparks `#0099E5`.
- It has moods already: **waving** (hello), **thinking** (dots, while the Brain works), **pointing** (shows a
  thing), **celebrating** (arms up + confetti). Use them as written; animate the switch between moods with a quick
  squash (scale 0.92 → 1.04 → 1 over 0.35s).
- It never talks with a mouth-flap. It reacts.

### Cards = our real screens, rebuilt clean

Like the reference, we don't show blurry screenshots. We rebuild the key bits of BMI's screens as clean vector cards
with **real labels** (copy the exact words from the app; they're in `backend/app/brain/help/`). White, 20px radius,
1px `#E3E7EF` border, shadow `0 30px 60px -20px rgba(19,44,107,.25)`. Real screenshots appear only in the one
"browser window" shot, captured at 2x from the demo data.

### Words on screen

Plain, warm, short. Never "AI": always "the Brain". No technical names. British spelling.

---

## 3. The story

**Idea:** *"Everything you sell, in one place. And a Brain that helps."*

Three beats, like the reference:
1. **Hello** - meet the Brain (it answers your questions).
2. **It does the work** - a booking flows from proposal to invoice; the Brain checks things overnight; mail merges
   write themselves; small wins are celebrated.
3. **It's all yours** - every title, every team, every theme. End card.

Tagline options (pick one for the end card):
- **"Everything you sell. One place. One Brain."** (recommended)
- "Your work, with a Brain."
- "Less admin. More selling."

---

## 4. Shot list (45s at 30fps; music at 120 BPM = 1 beat every 0.5s)

All shots on the off-white canvas with the blue aurora drifting slowly unless noted. The camera always has a slow
drift (2-4% scale over the shot) so nothing is ever dead still.

**SHOT 1 · 0:00-0:03 · Cold open: cards in the air**
Three white cards float at different depths, tilted ~12° (rotateX 10, rotateY -14): a booking card ("Booking 2417:
Gate Gourmet", green "Confirmed" badge), a rate-card row, an editorial issue card ("Onboard Hospitality · Spring
issue"). Near and far cards are blurred (depth of field), the middle one is sharp. Cursor enters, drags the
booking card to the centre.
*Move:* parallax (near layers move faster), blur-in from 16px, ease-out-expo.

**SHOT 2 · 0:03-0:06 · The Brain arrives**
Cards blur and fall away. A navy/blue glow blooms in the centre; **the Brain pops in** (scale 0 → 1.08 → 1,
spring) in the **waving** mood. Headline slides in from the right past it with motion blur:
**"Hi, I'm the Brain."**
*Sound:* soft whoosh + a bright "pop" on the Brain's landing (on the beat).

**SHOT 3 · 0:06-0:11 · Ask it anything**
The "Ask the Brain" chat box (white card, the Brain's small head icon top-left, send button bottom-right). Text
types itself, ~18 characters/second with natural pauses:
**"How much has Gate Gourmet booked this year?"**
Cursor clicks Send (button presses in 0.94, then out). The Brain head switches to **thinking** (three dots pulse).
The answer card slides up under it: a short sentence and a figure (use the demo-data answer; don't invent).
*Move:* camera pushes in 8% while typing; on the answer, a soft light sweep crosses the card.

**SHOT 4 · 0:11-0:13 · Wordmark**
White frame. **"BMI Brain"** types on in Geist SemiBold, then the Brain's head slides into the gap at the start of
the line and the lockup settles. Hold half a second.

**SHOT 5 · 0:13-0:22 · A booking, start to finish (the flow)**
The reference's vertical card flow, with our sale. Cards joined by thin navy lines that **draw on** as the camera
glides down:
1. **Proposal** card - "Proposal for Gate Gourmet · 3 titles, 2 options"
2. **Booking** card - "Booking 2417: Gate Gourmet" + amber "· The confirmation hasn't been sent yet"
3. **Confirmation** card - an envelope; "Email the confirmation" button gets a click; amber note flips to
   "Confirmation sent today to daniel.weber@gategourmet.example"
4. **Invoice** card - "Ready to invoice" with a tick
Above the flow, a checklist builds with spinners turning into ticks (stagger 0.25s), just like the reference's
"12-step onboarding / Brand voice applied":
- ✓ Prices taken from the rate card
- ✓ Issue deadline checked
- ✓ Accounts copied in
Non-focused cards blur (6-10px). Each card arrives with a 40px rise + fade, ease-out-quint.
*Sound:* a tiny tick on each ✓, a "send" swoosh on the confirmation.

**SHOT 6 · 0:22-0:26 · While you sleep (pull-back reveal)**
Camera **pulls back** from the flow to reveal it's one of many, laid out like a calm map: columns labelled
**Review Queue**, **Today**, **Call notes**, **Data Health**, each with 2-3 small cards (e.g. "3 emails bounced",
"Renewal due: Selling Travel", "Call notes ready: Gate Gourmet"). A moon-blue night tint sweeps across, the Brain
sits at the top, small: first **sleepy**, then it wakes up and switches to **pointing**.
Headline fades up: **"It checks things overnight. You decide in the morning."**

**SHOT 7 · 0:26-0:30 · Confirm the booking (glass button + celebration)**
Close-up of a frosted-glass button **"Confirm the booking"** with design-tool selection handles at its corners
(the reference's "Automated" shot). Cursor clicks. The handles snap away, the button flashes, and the **Brain
celebrates** - arms up, confetti in navy, blue and the one warm amber. Small toast: **"Booking confirmed. Nice one."**
*Sound:* click + a short bright chime + soft confetti rustle. This is the emotional peak; hit it on a downbeat.

**SHOT 8 · 0:30-0:34 · Mail merge (the mono retype)**
A big email greeting in **Geist Mono**, in a blue selection box: **"Dear {{first_name}},"**
A named cursor ("Sally") clicks; the field flips through real-looking names on each beat:
"Dear Daniel," → "Dear Priya," → "Dear Tom," → back to "Dear {{first_name}},".
Caption underneath (Geist): **"One email to each person. Written for them."**

**SHOT 9 · 0:34-0:38 · Every title, every theme**
The app in a browser window (real 2x screenshot of Home on the demo data). Words split either side of it:
**"Every ··· title"** - the title switcher cycles Onboard Hospitality → Selling Travel → The Business Travel
Magazine (hard cuts on the beat).
Then the background **flips** like the reference's "Dark Mode": **"Morning · Evening · Night"** - the same screen
re-colours through our three themes (navy → mahogany → night blue), one per beat. Night ends on near-black.

**SHOT 10 · 0:38-0:41 · The pulse + numbers**
On near-black, then back to light: a small navy pill **"BMI Brain"** with the Brain's head, and big blue rings pulse
out from it (radial ripple, 3 rings, 0.6s apart). The rings settle into a line chart drawing upward while 3 numbers
**count up** beside it:
- **[contacts in BMI Brain]** contacts
- **[bookings this year]** bookings
- **4** titles, one place
Fill the bracketed figures from production before rendering (Ahmed). If we don't want real figures in the film,
swap to words: "Every contact · Every booking · Every title".

**SHOT 11 · 0:41-0:43 · For every team**
The reference's "Works from any AI agent" logo morph. Centre icon morphs (shape morph, 0.25s each, on the beat):
handshake → calculator → pen nib → printing press → gear, with the label changing:
**"For sales · accounts · editorial · production · admin"**

**SHOT 12 · 0:43-0:45 (+1s hold) · End card**
The Brain (happy) + **"BMI Brain"** wordmark, tagline under it:
**"Everything you sell. One place. One Brain."**
A pill button under the tagline: **"Open it today →"** with the app address. The aurora settles; music ends on a
soft final hit. Hold 1 second on the frame.

---

## 5. Motion rules (the craft, with the names to search for)

| Term | Our setting |
|---|---|
| **Easing** | Ease-out-expo `cubic-bezier(0.16, 1, 0.3, 1)` for entrances; ease-in-out-cubic for camera moves. Never linear (except the slow aurora drift). |
| **Spring / overshoot** | Pops (the Brain, badges, buttons) overshoot 4-8% and settle (stiffness ~180, damping ~16). |
| **Stagger** | Lists and checklists: 60-120ms between items; checklist ticks 250ms. |
| **Blur-in / motion blur** | Things arrive from 12-16px blur to 0; fast slides use directional motion blur. |
| **Depth of field** | Out-of-focus cards blurred 6-10px and slightly faded (opacity 0.6). Focus "racks" from one card to the next. |
| **2.5D / perspective tilt** | Cards in 3D space (perspective 1600px), tilted 8-14°, with parallax between layers. |
| **Camera push-in / pull-back** | Every shot has a slow push (2-4%); Shot 6 has a big pull-back (scale 1 → 0.35). |
| **Mask reveal** | Headlines rise out of an invisible line (clip-path), 0.5s. |
| **Typewriter** | Prompt text at ~18 chars/s with a blinking caret; small random pauses. |
| **Cursor choreography** | Mac-style arrow, moves on curved paths (bezier), slows before a click, button presses to 0.94. |
| **Line draw** | Connector lines and the chart use stroke-dashoffset, 0.6s, ease-in-out. |
| **Counter roll** | Numbers count up with ease-out over 0.8s; tabular figures so they don't jitter. |
| **Shape morph** | Shot 11 icons morph (path interpolation, e.g. Flubber or GSAP MorphSVG). |
| **Radial pulse** | Rings scale 0.6 → 2.2 while fading 0.5 → 0. |
| **Glassmorphism** | Backdrop blur 24px, white at 35%, 1px white-60% border, inner highlight on the top edge. |
| **Mesh / aurora gradient** | 3-4 big blurred circles (blur 120-180px) drifting slowly (8-12s loops); never sharp edges. |
| **Light sweep / sheen** | A soft diagonal white band crossing a card once, 0.7s, on "result" moments. |
| **Film grain** | Fine noise overlay at 3-4% opacity over everything (stops gradients banding, adds richness). |
| **Hit points** | Every pop, click, tick and cut lands on a beat or a half-beat of the music. |
| **Hold** | Each "result" (answer card, confirmed booking, end card) holds ~1s so people can read it. |
| **Match cut** | Shot 4 → 5: the Brain's head in the wordmark becomes the dot that starts the flow line. |

**Don'ts:** no lens flares, no 3D chrome logo, no stock footage, no fast spinning, no more than one idea per shot,
nothing on screen for under 0.8s if it has words in it, no tiny unreadable UI as the subject of a shot.

---

## 6. Sound

- **Music:** minimal, warm electronic, 118-122 BPM, light percussion, a soft synth pad, rising slightly into the
  celebration (Shot 7) and resolving on the end card. Searches that work: "minimal tech corporate", "clean product
  launch", "future bass light". Licensed sources: YouTube Audio Library, Pixabay Music, Artlist, Musicbed.
- **Sound effects** (subtle, -18 to -12 dB under the music): soft UI clicks, typing ticks, whoosh on slides, a pop
  on the Brain, a tiny tick per ✓, a send swoosh, a chime + confetti on the celebration, a low "boom" swell under
  the pull-back.
- **No voiceover** (like the reference). The film works with the sound off, so it can be played on a screen in the
  office or sent in Teams.
- Mix: music -14 LUFS integrated; leave 1 frame of silence at the end.

---

## 7. How to build it (for the local agent)

**Recommended route:** build the motion as code, render frames, then finish in the editor.

1. **Scenes in HTML + GSAP** (GSAP and all its plugins, including MorphSVG and SplitText, are free to use). One
   page, 1920x1080, one master GSAP timeline, labels per shot. Reuse:
   - the Brain SVG from `frontend/src/components/brain/brain-buddy.tsx` (copy the paths; keep the moods),
   - the Geist and Geist Mono fonts (from the `geist` npm package or Google Fonts),
   - exact button and screen labels from `backend/app/brain/help/**`.
2. **Render frame by frame**, deterministically: Playwright (Chromium is already set up in our tutorial tooling,
   see `docs/tutorials/preview/lib.mjs`) pauses the timeline, seeks to `frame / 30`, screenshots, repeat → PNG
   sequence → ffmpeg to ProRes or high-bitrate H.264. Frame-by-frame rendering means blur, glass and grain look
   perfect with no dropped frames. Render at 3840x2160 and scale to 1080p for a crisper result.
3. **The one real screenshot** (Shot 9): use the demo database and the tutorial seed
   (`backend/scripts/seed_tutorials.py`), sign in, capture Home at device scale 2 in each theme.
4. **Finish in OpenCut** (or ChatCut): drop in the rendered video, the music, the sound effects; nudge cuts to the
   beat; add the 1s end hold; export 1080p H.264 (10-15 Mbps) and a 4K master.
5. **Alternative to step 1:** Remotion (React; it would let you import the Brain component directly). Check its
   licence first - companies above a few people need a paid company licence.

**Deliverables:** `bmi-brain-intro-1080p.mp4`, `bmi-brain-intro-4k.mp4`, a muted version with burned-in captions
for Teams, a 1:1 cut (optional), and the project files.

---

## 8. Review checklist (before showing anyone)

- [ ] 40-50 seconds; end card holds at least 1s.
- [ ] Says "the Brain", never "AI". No system or company names other than BMI's own titles and the demo client.
- [ ] Every label matches the app exactly ("Confirm the booking", "Email the confirmation", "Ask the Brain",
      "Review Queue", "Today", "Call notes", "Data Health").
- [ ] The story matches how BMI works: the salesperson confirms the booking and sends the confirmation; Accounts
      only check bookings later, for invoicing. (Don't show Accounts approving a sale.)
- [ ] Only demo data on screen. No real client email addresses, no real prices.
- [ ] Every word readable at 1080p on a laptop; nothing with words is on screen for under 0.8s.
- [ ] Colours: navy, BMI blue and the off-white; amber only in the celebration.
- [ ] Works with the sound off.
- [ ] No banding in the gradients (grain on), no jitter in counters (tabular figures).

---

## 9. Paste this to the local agent

```text
You are making a 45-second internal launch film for "BMI Brain", BMI's sales and editorial app, for BMI staff only.
Read docs/launch-video/BRIEF.md in the BMI repo in full first; it is the director's brief, with a shot-by-shot list
(section 4), motion rules (section 5), sound (section 6) and build steps (section 7).

Style: copy the craft of the reference film https://saasexplain.com/work/claude-email.mp4 - pale off-white canvas,
huge soft out-of-focus colour blobs at the edges, crisp white rounded cards floating in tilted 3D space with depth of
field, a typing prompt with a cursor, a vertical flow of cards joined by lines, a pull-back reveal, a frosted-glass
button with selection handles, a monospaced retype gag, split words around a device, radial pulses, counting
numbers, a logo morph, and a clean end card. Use BMI's colours instead of orange: navy #132C6B, blue #0099E5,
light blue #6CC8F5 on #F4F6FA; amber #E8A33D only for the celebration confetti. Fonts: Geist and Geist Mono.

The hero is the Brain character: copy its SVG and moods from frontend/src/components/brain/brain-buddy.tsx
(outline #132C6B, body 12% navy on white, sparks #0099E5). Never write "AI" on screen - say "the Brain".
Use the exact labels from the app (they're in backend/app/brain/help/). Only demo data.

Build: one HTML page per the brief with a single GSAP timeline at 1920x1080 (render at 4K), render it frame by
frame with Playwright (pause, seek to frame/30, screenshot) and join with ffmpeg; then add music and sound effects
and finish in OpenCut. Work shot by shot: render each shot as a short preview, show me a still and the clip, and
only move on when I approve it. Finish with the checklist in section 8.
```
