// Rough preview of a tutorial video, made in a few minutes instead of an hour: plays a blueprint in the real app
// at real speed, with the voiceover as subtitles, each step's callout, a visible cursor and a ring on the target,
// and records it. The words come straight from the video's blueprint.md, so edit the blueprint and run it again.
// It's an animatic for checking wording, order and timing - the polished camera moves are Antigravity's job.
import fs from "node:fs";
import path from "node:path";

export function readBlueprint(file) {
  const text = fs.readFileSync(file, "utf8");
  const steps = {};
  const parts = text.split(/\n(?=STEP \d+ · )/).slice(1);
  for (const part of parts) {
    const head = part.match(/^STEP (\d+) · (\d+):(\d+)-(\d+):(\d+) · (.+)/);
    if (!head) continue;
    const n = Number(head[1]);
    const secs = (Number(head[4]) * 60 + Number(head[5])) - (Number(head[2]) * 60 + Number(head[3]));
    const vo = (part.match(/Voiceover: "([\s\S]*?)"\n/) || [])[1]?.replace(/\s*\n\s*/g, " ") ?? "";
    const arche = (part.match(/ARCHETYPE ([ABCD])/) || [])[1] ?? "A";
    const badge = part.match(/Badge pill: \[([\w-]+)\] "([^"]+)"/);
    const line = (part.match(/(?:Headline|Text): "([^"]+)"/) || [])[1] ?? "";
    steps[n] = { n, title: head[6].trim(), secs, vo, arche, badge: badge ? badge[2] : "", line };
  }
  return steps;
}

const OVERLAY = () => {
  if (document.getElementById("tut-layer")) return;
  const css = document.createElement("style");
  css.textContent = `
    #tut-layer{position:fixed;inset:0;pointer-events:none;z-index:2147483647;font-family:Inter,system-ui,sans-serif}
    #tut-cursor{position:fixed;width:22px;height:22px;margin:-3px 0 0 -3px;transition:transform .12s}
    #tut-cursor.down{transform:scale(.8)}
    #tut-ring{position:fixed;border:3px solid #f59e0b;border-radius:10px;box-shadow:0 0 0 6px rgba(245,158,11,.25);transition:all .5s ease;opacity:0}
    #tut-sub{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);max-width:980px;background:rgba(15,23,42,.88);color:#fff;
      font-size:20px;line-height:1.4;padding:12px 20px;border-radius:12px;text-align:center}
    #tut-step{position:fixed;left:16px;top:64px;background:rgba(15,23,42,.8);color:#cbd5e1;font-size:12px;padding:4px 10px;border-radius:999px}
    #tut-call{position:fixed;background:rgba(255,255,255,.9);backdrop-filter:blur(10px);border:1px solid rgba(30,58,138,.25);color:#0f172a;
      border-radius:14px;padding:10px 14px;box-shadow:0 10px 30px rgba(15,23,42,.2);font-size:15px;font-weight:600;max-width:360px;transition:opacity .3s}
    #tut-call b{display:inline-block;background:#1e3a8a;color:#fff;font-size:11px;padding:2px 8px;border-radius:999px;margin-right:8px;vertical-align:2px}
    #tut-call i{display:block;font-style:normal;font-size:11px;color:#64748b;font-weight:500;margin-top:3px}
    #tut-card{position:fixed;inset:0;background:rgba(15,23,42,.82);backdrop-filter:blur(12px);color:#fff;display:flex;flex-direction:column;
      align-items:center;justify-content:center;gap:12px;opacity:0;transition:opacity .4s}
    #tut-card b{background:#1e3a8a;padding:4px 12px;border-radius:999px;font-size:14px}
    #tut-card .t{font-size:54px;font-weight:700}`;
  document.head.appendChild(css);
  const layer = document.createElement("div");
  layer.id = "tut-layer";
  layer.setAttribute("data-feedback-ui", "");
  layer.innerHTML = `<div id="tut-ring"></div><div id="tut-call" style="opacity:0"></div><div id="tut-card"></div>
    <div id="tut-step"></div><div id="tut-sub"></div>
    <svg id="tut-cursor" viewBox="0 0 24 24"><path d="M3 2l7 19 2.5-7.5L20 11z" fill="#0f172a" stroke="#fff" stroke-width="1.5"/></svg>`;
  document.body.appendChild(layer);
  const cur = document.getElementById("tut-cursor");
  const at = window.__tutCursor || { x: 720, y: 450 };
  cur.style.left = at.x + "px"; cur.style.top = at.y + "px";
  addEventListener("mousemove", (e) => { cur.style.left = e.clientX + "px"; cur.style.top = e.clientY + "px"; window.__tutCursor = { x: e.clientX, y: e.clientY }; }, true);
  addEventListener("mousedown", () => cur.classList.add("down"), true);
  addEventListener("mouseup", () => cur.classList.remove("down"), true);
};

export function director(page, steps) {
  let mouse = { x: 720, y: 450 };
  page.on("framenavigated", () => {});
  const ensure = () => page.evaluate(OVERLAY);
  const h = {
    page,
    async ensure() { await ensure(); },
    /** glide the cursor to a locator's centre (or a point) like a person would */
    async glide(target, ms = 800) {
      await ensure();
      let x, y;
      if (Array.isArray(target)) [x, y] = target;
      else { const b = await target.boundingBox(); x = b.x + b.width / 2; y = b.y + b.height / 2; }
      const n = Math.max(12, Math.round(ms / 16));
      for (let i = 1; i <= n; i++) {
        const t = i / n, e = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        await page.mouse.move(mouse.x + (x - mouse.x) * e, mouse.y + (y - mouse.y) * e);
        await page.waitForTimeout(ms / n);
      }
      mouse = { x, y };
    },
    async click(target, ms) { await h.glide(target, ms); await page.waitForTimeout(250); await page.mouse.down(); await page.waitForTimeout(150); await page.mouse.up(); await page.waitForTimeout(250); },
    async type(text) { await page.keyboard.type(text, { delay: 90 }); },
    /** ring around a locator (null hides it) */
    async ring(target) {
      await ensure();
      const b = target ? await target.boundingBox() : null;
      await page.evaluate((b) => { const r = document.getElementById("tut-ring"); if (!b) { r.style.opacity = 0; return; }
        Object.assign(r.style, { left: b.x - 6 + "px", top: b.y - 6 + "px", width: b.width + 12 + "px", height: b.height + 12 + "px", opacity: 1 }); }, b);
    },
    /** the step's callout next to a locator; side = below | above | right | left */
    async callout(step, target, side = "below") {
      await ensure();
      const b = target ? await target.boundingBox() : { x: 720, y: 300, width: 0, height: 0 };
      await page.evaluate(({ s, b, side }) => {
        const c = document.getElementById("tut-call");
        c.innerHTML = `<b>${s.badge}</b>${s.line}<i>Callout ${s.arche}${s.arche === "B" ? " (split-screen in the final cut)" : s.arche === "C" ? " (pop-out in the final cut)" : ""}</i>`;
        c.style.opacity = 1;
        const w = 360, pos = { below: [b.x, b.y + b.height + 14], above: [b.x, b.y - 74], right: [b.x + b.width + 16, b.y - 8], left: [b.x - w - 16, b.y - 8] }[side];
        c.style.left = Math.max(270, Math.min(innerWidth - w - 16, pos[0])) + "px"; c.style.top = Math.max(64, pos[1]) + "px";
      }, { s: step, b, side });
    },
    async hideCallout() { await page.evaluate(() => { const c = document.getElementById("tut-call"); if (c) c.style.opacity = 0; }); },
    async card(step, show = true) {
      await ensure();
      await page.evaluate(({ s, show }) => { const c = document.getElementById("tut-card");
        c.innerHTML = `<b>${s.badge}</b><div class="t">${s.line}</div>`; c.style.opacity = show ? 1 : 0; }, { s: step, show });
    },
    /** run one step: subtitles on, the step's actions, then hold until the step's time is up */
    async step(n, actions) {
      const s = steps[n];
      if (!s) throw new Error(`STEP ${n} isn't in the blueprint`);
      const start = Date.now();
      await ensure();
      await page.evaluate(({ s }) => { document.getElementById("tut-sub").textContent = s.vo; document.getElementById("tut-step").textContent = `Step ${String(s.n).padStart(2, "0")} · ${s.title}`; }, { s });
      await actions(s);
      const left = s.secs * 1000 - (Date.now() - start);
      if (left > 0) await page.waitForTimeout(left);
      else console.log(`  step ${n} ran ${Math.round(-left / 100) / 10}s over its ${s.secs}s - the voiceover may need more time`);
      await h.ring(null); await h.hideCallout();
    },
  };
  return h;
}

export async function finish(ctx, page, outDir, name) {
  const video = page.video();
  await ctx.close();
  if (!video) return;
  const src = await video.path();
  const dest = path.join(outDir, `${name}.webm`);
  fs.renameSync(src, dest);
  console.log(`Preview saved: ${dest}`);
}
