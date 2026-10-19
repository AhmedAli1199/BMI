// Takes the Help Centre screenshots (docs/help-centre-plan.md): drives the app as Sally on the tutorial demo data,
// rings what each step is about with its step number, and saves frontend/public/help/<article>/<n>.png.
//
//   cd backend && python scripts/seed_tutorials.py --yes      (demo database only - resets the tutorial data)
//   node docs/help-centre/shoot.mjs [http://localhost:3000] [path-to-chrome]
//
// Re-run it whenever a screen changes; every picture is made fresh.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(here, "../../frontend/package.json"));
const { chromium } = require("playwright");
const [APP = "http://localhost:3000", CHROME = process.env.CHROME_PATH || undefined] = process.argv.slice(2);
const OUT = path.join(here, "../../frontend/public/help");

// --lang: date boxes follow the browser language, so the pictures show UK dates
const browser = await chromium.launch({ executablePath: CHROME, args: ["--lang=en-GB"], env: { ...process.env, LANG: "en_GB.UTF-8", LANGUAGE: "en_GB" } });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5, baseURL: APP,
  locale: "en-GB", timezoneId: "Europe/London" });
const page = await ctx.newPage();
page.setDefaultTimeout(120000);

await page.goto("/login");
await page.fill('input[type="email"]', "sally.parker@tutorial.bmi");
await page.fill('input[type="password"]', "BMI-tutorial-2026");
await page.click('button[type="submit"]');
await page.waitForURL((u) => !String(u).includes("/login"));
// no tips, tour or celebrations in the pictures
await page.addInitScript(() => { window.__noCoach = true; });
await page.addStyleTag({ content: "" }).catch(() => {});

const field = (label) => page.locator(`xpath=(//label[starts-with(normalize-space(.), ${JSON.stringify(label)})]//*[self::input or self::select or self::textarea])[1]`);
const suggestion = (text) => page.locator("body > div[style] button", { hasText: text }).first();

/** Rings each locator (numbered when there's more than one) and saves the picture. */
async function shot(article, n, targets, { clip = null, settle = 600, keepFloating = false } = {}) {
  await page.waitForTimeout(settle);
  const boxes = [];
  for (const t of targets) {
    const b = await t.boundingBox({ timeout: 15000 }).catch(() => null);
    if (b) boxes.push(b);
  }
  await page.evaluate(([boxes, keepFloating]) => {
    document.querySelectorAll("[data-help-mark]").forEach((e) => e.remove());
    // hide the floating Ask the Brain / Feedback buttons so they don't sit in the picture (unless it's about them)
    if (!keepFloating) document.querySelectorAll("[data-feedback-ui]").forEach((e) => { e.style.visibility = "hidden"; });
    boxes.forEach((b, i) => {
      const ring = document.createElement("div");
      ring.setAttribute("data-help-mark", "");
      Object.assign(ring.style, {
        position: "fixed", left: `${b.x - 6}px`, top: `${b.y - 6}px`, width: `${b.width + 12}px`, height: `${b.height + 12}px`,
        border: "3px solid var(--ring)", borderRadius: "10px", boxShadow: "0 0 0 4px color-mix(in srgb, var(--ring) 22%, transparent)",
        zIndex: 2147483646, pointerEvents: "none",
      });
      document.body.appendChild(ring);
      if (boxes.length > 1) {
        const dot = document.createElement("div");
        dot.setAttribute("data-help-mark", "");
        dot.textContent = String(i + 1);
        Object.assign(dot.style, {
          position: "fixed", left: `${b.x - 18}px`, top: `${b.y - 18}px`, width: "24px", height: "24px", borderRadius: "999px",
          background: "var(--ring)", color: "white", font: "700 13px/24px system-ui, sans-serif", textAlign: "center",
          zIndex: 2147483647, pointerEvents: "none",
        });
        document.body.appendChild(dot);
      }
    });
  }, [boxes, keepFloating]);
  const dir = path.join(OUT, article);
  fs.mkdirSync(dir, { recursive: true });
  // show the part of the screen that matters: from the sidebar's edge, centred on what's ringed
  let c = clip;
  if (!c && boxes.length) {
    const top = Math.max(0, Math.min(...boxes.map((b) => b.y)) - 220);
    c = { x: 256, y: Math.min(top, 900 - 560), width: 1184, height: 560 };
  }
  await page.screenshot({ path: path.join(dir, `${n}.png`), clip: c ?? { x: 256, y: 0, width: 1184, height: 900 } });
  await page.evaluate(() => {
    document.querySelectorAll("[data-help-mark]").forEach((e) => e.remove());
    document.querySelectorAll("[data-feedback-ui]").forEach((e) => { e.style.visibility = ""; });
  });
  console.log(`  ${article}/${n}.png`);
}

async function fillBooking() {
  await page.goto("/sales/deals/new");
  await page.getByPlaceholder("Search the CRM…").click();
  await page.keyboard.type("Gate", { delay: 60 });
  await suggestion("Gate Gourmet").click();
  await page.getByPlaceholder("Search for the contact…").click();
  await page.keyboard.type("Daniel", { delay: 60 });
  await suggestion("Daniel Weber").click();
  await field("Title").selectOption({ label: "OnBoard Hospitality (OBH)" });
  await page.waitForTimeout(500);
  await field("From the rate card").selectOption({ label: "Full page (210 x 297 mm, 3 mm bleed) - £2,990" });
  await page.waitForTimeout(500);
  await page.locator("select[aria-label='Issue, month or event']").first().selectOption({ label: "Issue 108 · 10 Dec 2026 · book by 2 Dec 2026" });
  await page.waitForTimeout(500);
}

// ---- Make a booking --------------------------------------------------------------------------------------------
console.log("make-a-booking");
await page.goto("/sales/deals");
await page.getByRole("heading", { name: "Bookings", level: 1 }).waitFor();
await shot("make-a-booking", 1, [page.locator('a[href="/sales/deals/new"]')], { clip: { x: 256, y: 0, width: 1184, height: 520 } });

await page.goto("/sales/deals/new");
await page.getByPlaceholder("Search the CRM…").click();
await page.keyboard.type("Gate", { delay: 60 });
await suggestion("Gate Gourmet").waitFor();
await shot("make-a-booking", 2, [page.getByPlaceholder("Search the CRM…"), suggestion("Gate Gourmet")]);
await suggestion("Gate Gourmet").click();
await page.getByPlaceholder("Search for the contact…").click();
await page.keyboard.type("Daniel", { delay: 60 });
await suggestion("Daniel Weber").click();
await page.waitForTimeout(500);
await shot("make-a-booking", 3, [field("Contact name"), field("Contact email")]);
await field("Title").selectOption({ label: "OnBoard Hospitality (OBH)" });
await page.waitForTimeout(500);
await field("From the rate card").selectOption({ label: "Full page (210 x 297 mm, 3 mm bleed) - £2,990" });
await shot("make-a-booking", 4, [field("Title"), field("From the rate card"), field("Price each (£)")]);
const runs = page.locator("select[aria-label='Issue, month or event']").first();
await runs.selectOption({ label: "Issue 108 · 10 Dec 2026 · book by 2 Dec 2026" });
await runs.scrollIntoViewIfNeeded();
await shot("make-a-booking", 5, [runs]);
await page.evaluate(() => window.scrollTo(0, 0));
await shot("make-a-booking", 6, [page.getByRole("button", { name: "Confirm the booking" }), page.getByRole("button", { name: "Pencil it in" })],
  { clip: { x: 256, y: 0, width: 1184, height: 460 } });
await page.getByRole("button", { name: "Confirm the booking" }).click();
await page.waitForURL(/\/sales\/deals\/[0-9a-f-]{36}$/);
await page.getByText("Confirmed", { exact: true }).waitFor();
const confirmedUrl = page.url();
await shot("make-a-booking", 7, [page.getByText("Confirmed", { exact: true }), page.locator("table").first()], { clip: { x: 256, y: 0, width: 1184, height: 760 } });

// ---- Send the confirmation -------------------------------------------------------------------------------------
console.log("send-the-confirmation");
await page.goto(confirmedUrl);
await page.getByRole("button", { name: "Email the confirmation" }).waitFor();
await shot("send-the-confirmation", 1, [page.getByText("The confirmation hasn't been sent yet", { exact: false }).first(), page.getByRole("button", { name: "Email the confirmation" })],
  { clip: { x: 256, y: 0, width: 1184, height: 460 } });
await page.getByRole("button", { name: "Email the confirmation" }).click();
const dialog = page.getByRole("dialog");
await dialog.waitFor();
await shot("send-the-confirmation", 2, [dialog], { clip: { x: 0, y: 0, width: 1440, height: 900 } });
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
await page.locator("button[aria-label='More'][aria-haspopup=menu]").click();
const sentOther = page.getByRole("menuitem", { name: "I sent it another way" });
await sentOther.waitFor();
await shot("send-the-confirmation", 3, [sentOther], { clip: { x: 256, y: 0, width: 1184, height: 520 } });
await sentOther.click();
await page.getByText(/Confirmation sent/).first().waitFor();
await page.waitForTimeout(800);
await shot("send-the-confirmation", 4, [page.getByText(/Confirmation sent/).first()], { clip: { x: 256, y: 0, width: 1184, height: 420 } });

// ---- Pencil a booking in ---------------------------------------------------------------------------------------
console.log("pencil-a-booking-in");
await fillBooking();
await page.evaluate(() => window.scrollTo(0, 0));
await shot("pencil-a-booking-in", 1, [page.getByRole("button", { name: "Pencil it in" })], { clip: { x: 256, y: 0, width: 1184, height: 460 } });
await page.getByRole("button", { name: "Pencil it in" }).click();
await page.waitForURL(/\/sales\/deals\/[0-9a-f-]{36}$/);
await page.getByText("Pencilled", { exact: true }).first().waitFor();
await shot("pencil-a-booking-in", 2, [page.getByText("Pencilled", { exact: true }).first(), page.getByRole("button", { name: "Confirm", exact: true })],
  { clip: { x: 256, y: 0, width: 1184, height: 460 } });

// ---- Set a reminder --------------------------------------------------------------------------------------------
console.log("set-a-reminder");
await page.goto("/contacts");
await page.getByRole("link", { name: "Daniel Weber" }).first().click();
await page.getByRole("button", { name: "Remind me" }).waitFor();
await shot("set-a-reminder", 1, [page.getByRole("button", { name: "Remind me" })], { clip: { x: 256, y: 0, width: 1184, height: 420 } });
await page.getByRole("button", { name: "Remind me" }).click();
const rem = page.getByRole("dialog");
await rem.waitFor();
await rem.getByRole("button", { name: "1 week" }).click().catch(() => {});
await rem.locator("textarea, input[type=text]").last().fill("Ask Daniel about the spring issue").catch(() => {});
await shot("set-a-reminder", 2, [rem.getByRole("button", { name: "1 week" }), rem.getByRole("button", { name: "Set reminder" })],
  { clip: { x: 0, y: 0, width: 1440, height: 900 } });
await rem.getByRole("button", { name: "Set reminder" }).click();
await page.waitForTimeout(1200);
await shot("set-a-reminder", 3, [page.getByText("Ask Daniel about the spring issue").first()], { clip: { x: 256, y: 0, width: 1184, height: 520 } });

// ---- Ask the Brain ---------------------------------------------------------------------------------------------
console.log("ask-the-brain");
await page.goto("/sales/deals");
const ask = page.locator("button[title^='Ask the Brain']");
await ask.waitFor();
await shot("ask-the-brain", 1, [ask], { clip: { x: 640, y: 500, width: 800, height: 400 }, keepFloating: true });
await ask.click();
await page.getByText(/what would you like to know/i).waitFor();
await page.waitForTimeout(800);
await shot("ask-the-brain", 2, [page.locator("textarea").last()], { clip: { x: 0, y: 0, width: 1440, height: 900 }, keepFloating: true });
await page.keyboard.press("Escape");
// a card the Brain made (planted by the seed-free helper below, so the picture doesn't need a live key)
const conv = process.env.HELP_CARD_CONVERSATION;
if (conv) {
  await page.goto(`/brain?c=${conv}`);
  await page.locator("[data-action-card]").first().waitFor();
  await shot("ask-the-brain", 3, [page.locator("[data-action-card]").first()], { clip: { x: 256, y: 120, width: 1184, height: 560 } });
}

await browser.close();
console.log("done");
