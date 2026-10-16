// Preview of Video 1, recorded from the real app with the blueprint's words. See ../README.md ("Previewing").
//   node docs/tutorials/01-making-a-booking/preview.mjs [app address] [chrome path] [--final [--subtitles]]
// Run the tutorial seed first (it clears earlier takes). Takes about 3 minutes; writes preview.webm (or final.webm
// with --final) and its timeline next to this file. Then: python docs/tutorials/preview/voiceover.py <this folder>
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { args, director, finish, readBlueprint } from "../preview/lib.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(here, "../../../frontend/package.json"));
const { chromium } = require("playwright");
const [APP = "http://localhost:3000", CHROME = process.env.CHROME_PATH || undefined] = args();
const steps = readBlueprint(path.join(here, "blueprint.md"));

const browser = await chromium.launch({ executablePath: CHROME });
// sign in first, off camera
const login = await browser.newContext({ viewport: { width: 1440, height: 900 }, baseURL: APP });
const lp = await login.newPage();
await lp.goto("/login");
await lp.fill('input[type="email"]', "sally.parker@tutorial.bmi");
await lp.fill('input[type="password"]', "BMI-tutorial-2026");
await lp.click('button[type="submit"]');
await lp.waitForURL((u) => !String(u).includes("/login"), { timeout: 120000 });
for (const u of ["/sales/deals", "/sales/deals/new"]) await lp.goto(u, { timeout: 120000 });   // warm the pages up
const state = await login.storageState();
await login.close();

const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, baseURL: APP, storageState: state,
  recordVideo: { dir: here, size: { width: 1440, height: 900 } } });
const page = await ctx.newPage();
const t0 = Date.now();   // the video starts when the page opens
const field = (label) => page.locator(`xpath=(//label[starts-with(normalize-space(.), ${JSON.stringify(label)})]//*[self::input or self::select or self::textarea])[1]`);
const suggestion = (text) => page.locator("body > div[style] button", { hasText: text }).first();
const total = page.getByText("Booking total", { exact: true }).locator("xpath=ancestor::div[1]");   // the card on the right
const h = director(page, steps, t0);
// a native drop-down can't be filmed, so: click it, pause as if reading, then choose
const choose = async (sel, label) => { await h.click(sel); await page.waitForTimeout(700); await sel.selectOption({ label }); await page.waitForTimeout(400); };

await page.goto("/sales/deals");
await page.getByRole("heading", { name: "Bookings", level: 1 }).waitFor();

await h.step(0, async (s) => { await h.card(s); await page.waitForTimeout(s.secs * 1000 - 600); await h.card(s, false); });

await h.step(1, async (s) => {
  const btn = page.locator('a[href="/sales/deals/new"]');
  await h.glide([330, 160], 300); await h.ring(btn); await h.callout(s, btn, "below");
  await page.waitForTimeout(1500); await h.click(btn, 900);
  await page.waitForURL("**/sales/deals/new"); await h.ensure();
});

await h.step(2, async (s) => {
  const box = page.getByPlaceholder("Search the CRM…");
  await h.ring(box); await h.click(box); await h.callout(s, box, "right"); await h.type("Gate");
  await suggestion("Gate Gourmet").waitFor(); await page.waitForTimeout(600);
  await h.click(suggestion("Gate Gourmet"), 600);
  await page.waitForTimeout(500); await h.ring(field("Client name as booked"));
});

await h.step(3, async (s) => {
  const box = page.getByPlaceholder("Search for the contact…");
  await h.ring(box); await h.click(box); await h.type("Daniel");
  await suggestion("Daniel Weber").waitFor(); await page.waitForTimeout(500);
  await h.click(suggestion("Daniel Weber"), 600);
  await page.waitForTimeout(400); await h.ring(field("Contact email")); await h.callout(s, field("Contact name"), "above");
});

await h.step(4, async (s) => {
  const row = field("Salesperson");
  await h.glide([1095, 428], 700); await h.ring(row); await h.callout(s, row, "below");
  await page.waitForTimeout(1500); await h.ring(field("Booking date"));
});

await h.step(5, async (s) => {
  await h.ring(field("Title")); await choose(field("Title"), "OnBoard Hospitality (OBH)");
  await h.ring(field("From the rate card")); await h.glide(field("From the rate card"), 700); await h.callout(s, field("From the rate card"), "above");
});

await h.step(6, async (s) => {
  await choose(field("From the rate card"), "Full page (210 x 297 mm, 3 mm bleed) - £2,990");
  await h.ring(field("Price each (£)")); await page.waitForTimeout(1800);
  await h.glide([1100, 560], 700); await h.ring(total); await h.callout(s, total, "left");
});

await h.step(7, async (s) => {
  await page.evaluate(() => window.scrollTo({ top: 200, behavior: "smooth" })); await page.waitForTimeout(900);
  const runs = page.locator("select[aria-label='Issue, month or event']").first();
  await h.ring(runs); await h.callout(s, runs, "right"); await h.click(runs); await page.waitForTimeout(2500);
  await runs.selectOption({ label: "Issue 108 · 10 Dec 2026 · book by 2 Dec 2026" });
});

await h.step(8, async (s) => {
  const another = page.getByRole("button", { name: "Another", exact: true });
  await h.ring(another); await h.click(another);
  const second = page.locator("select[aria-label='Issue, month or event']").nth(1);
  await second.waitFor(); await h.ring(second);
  await choose(second, "Issue 109 · 18 Mar 2027 · book by 10 Mar 2027");
  await h.glide([1100, 300], 700); await h.ring(page.getByText("Total", { exact: true }).locator("xpath=..")); await h.callout(s, page.getByText("Total", { exact: true }), "left");
});

await h.step(9, async (s) => {
  await field("When to invoice").evaluate((e) => e.scrollIntoView({ block: "center", behavior: "smooth" })); await page.waitForTimeout(1000);
  await h.ring(field("When to invoice")); await h.glide(field("When to invoice"), 700); await h.callout(s, field("When to invoice"), "right");
});

await h.step(10, async (s) => {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" })); await page.waitForTimeout(1000);
  const btn = page.getByRole("button", { name: "Confirm the booking" });
  await h.ring(btn); await h.glide(btn, 800); await page.waitForTimeout(2500); await h.click(btn, 200);
  await page.waitForURL(/\/sales\/deals\/[0-9a-f-]{36}$/); await h.ensure();
  await page.getByText("Confirmed", { exact: true }).waitFor(); await h.callout(s, page.locator("h1"), "below");
});

await h.step(11, async (s) => {
  await h.ring(page.getByText("Confirmed", { exact: true })); await h.glide(page.getByText("Confirmed", { exact: true }), 700); await page.waitForTimeout(2200);
  const send = page.getByRole("button", { name: "Email the confirmation" });
  await h.ring(send); await h.glide(send, 800); await page.waitForTimeout(3500);
  const banner = page.getByText("Waiting for the accounts check.").locator("xpath=..");
  await h.ring(banner); await h.glide([800, 290], 900); await h.callout(s, banner, "below");
});

await h.step(12, async (s) => {
  const sched = page.getByRole("heading", { name: /^Schedule/ });
  await h.ring(page.locator("table").first()); await h.callout(s, sched, "above");
  await h.glide([1236, 512], 900); await h.ring(page.locator("table").getByText("Ready to invoice")); await page.waitForTimeout(3500);
  await h.glide([1232, 565], 700); await h.ring(page.getByText("Due 1 Jan 2027"));
});

await h.step(13, async (s) => { await h.card(s); });

await finish(ctx, page, here, h);
await browser.close();
