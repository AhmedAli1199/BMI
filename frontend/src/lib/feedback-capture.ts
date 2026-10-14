/**
 * What the Feedback button records besides what the person says: recent errors on the page, a plain
 * description of anything they point at (and where it's made in the code), and screenshots.
 * Browser-only.
 */
import type { FeedbackElement } from "@/lib/feedback-types";

// ---- Recent errors -----------------------------------------------------------------------------

type Logged = { at: string; kind: string; message: string };
const MAX = 25;
const log: Logged[] = [];
let installed = false;

export function recordProblem(kind: string, message: string) {
  if (typeof window === "undefined" || !message) return;
  log.push({ at: new Date().toLocaleTimeString("en-GB"), kind, message: message.slice(0, 1000) });
  if (log.length > MAX) log.splice(0, log.length - MAX);
}

/** Keep the last few errors so a report says what actually went wrong. */
export function installProblemLog() {
  if (installed || typeof window === "undefined") return;
  installed = true;
  window.addEventListener("error", (e) => recordProblem("page error", e.message || String(e.error ?? "")));
  window.addEventListener("unhandledrejection", (e) => recordProblem("page error", e.reason instanceof Error ? e.reason.message : String(e.reason ?? "")));
  const orig = console.error.bind(console);
  console.error = (...args: unknown[]) => {
    recordProblem("console", args.map((a) => (a instanceof Error ? a.message : typeof a === "string" ? a : (() => { try { return JSON.stringify(a); } catch { return String(a); } })())).join(" "));
    orig(...args);
  };
  const origFetch = window.fetch.bind(window);
  window.fetch = async (...args: Parameters<typeof fetch>) => {
    const res = await origFetch(...args);
    if (res.status >= 400) {
      const url = typeof args[0] === "string" ? args[0] : args[0] instanceof URL ? args[0].href : args[0].url;
      recordProblem("request", `${res.status} ${url.replace(location.origin, "")}`);
    }
    return res;
  };
}

export const recentProblems = () => [...log];

export function browserContext() {
  const ua = navigator.userAgent;
  const m = ua.match(/(Edg|Chrome|Firefox|Version)\/(\d+)/);
  const name = m ? ({ Edg: "Edge", Chrome: "Chrome", Firefox: "Firefox", Version: "Safari" } as Record<string, string>)[m[1]] + " " + m[2] : ua.slice(0, 80);
  const os = /Windows/.test(ua) ? "Windows" : /Mac OS/.test(ua) ? "Mac" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Linux/.test(ua) ? "Linux" : "";
  return {
    browser: `${name}${os ? ` on ${os}` : ""}`,
    viewport: `${innerWidth} x ${innerHeight}`,
    screen: `${screen.width} x ${screen.height}`,
    zoom: `${Math.round(devicePixelRatio * 100)}%`,
    theme: document.documentElement.classList.contains("dark") ? "dark" : "light",
    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    errors: recentProblems(),
  };
}

// ---- Describing what someone points at ---------------------------------------------------------

const INTERACTIVE = "button, a[href], input, select, textarea, [role=button], [role=tab], [role=menuitem], [role=checkbox], [role=switch], [role=option], [role=link], label, summary, img, th, td, h1, h2, h3, h4";
const clean = (s: string | null | undefined, n = 80) => (s ?? "").replace(/\s+/g, " ").trim().slice(0, n);

/** The thing a click most likely means: the button, link or field around the exact spot. */
export function meaningful(el: Element): Element {
  const hit = el.closest(INTERACTIVE);
  if (hit && hit !== document.body) return hit;
  return el;
}

function roleWord(el: Element): string {
  const tag = el.tagName.toLowerCase();
  const role = el.getAttribute("role");
  if (tag === "button" || role === "button") return "Button";
  if (tag === "a" || role === "link") return "Link";
  if (role === "tab") return "Tab";
  if (role === "menuitem" || role === "option") return "Menu choice";
  if (role === "checkbox" || role === "switch" || (tag === "input" && /checkbox|radio/.test((el as HTMLInputElement).type))) return "Tick box";
  if (["input", "select", "textarea"].includes(tag) || role === "textbox" || role === "combobox") return "Field";
  if (tag === "th") return "Column";
  if (tag === "td" || tag === "tr") return "Table cell";
  if (tag === "table") return "Table";
  if (/^h[1-4]$/.test(tag)) return "Heading";
  if (tag === "img" || tag === "svg") return "Picture";
  if (tag === "label") return "Label";
  return "Area";
}

function nameOf(el: Element): string {
  const aria = el.getAttribute("aria-label") || el.getAttribute("title");
  if (aria) return clean(aria);
  const id = el.getAttribute("id");
  if (id) {
    const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (lab) return clean(lab.textContent);
  }
  if (["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) {
    const wrap = el.closest("label");
    const own = wrap ? clean(Array.from(wrap.childNodes).filter((n) => n.nodeType === 3 || (n as Element).tagName === "SPAN").map((n) => n.textContent).join(" ")) : "";
    return own || clean((el as HTMLInputElement).placeholder) || clean((el as HTMLInputElement).name);
  }
  if (el.tagName === "IMG") return clean((el as HTMLImageElement).alt) || "picture";
  return clean((el as HTMLElement).innerText ?? el.textContent);
}

/** The nearest heading above it, so "Button: Save" becomes "Save, under Confirmation". */
function headingFor(el: Element): string {
  let node: Element | null = el;
  for (let depth = 0; node && depth < 10; depth++, node = node.parentElement) {
    const hs = node.querySelectorAll("h1, h2, h3, h4, [data-slot=card-title], [data-slot=sheet-title], [data-slot=dialog-title]");
    for (const h of Array.from(hs)) {
      if (h === el || el.contains(h)) continue;
      // a heading before the element in the page
      if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) {
        const t = clean(h.textContent, 80);
        if (t) return t;
      }
    }
  }
  return "";
}

/** A selector that finds it again (for the dots on the page). */
export function selectorFor(el: Element): string {
  const parts: string[] = [];
  let node: Element | null = el;
  while (node && node !== document.body && parts.length < 10) {
    const tag = node.tagName.toLowerCase();
    if (node.id && !/^(radix|base-ui|_r_|«)/.test(node.id) && !/:/.test(node.id)) { parts.unshift(`#${CSS.escape(node.id)}`); break; }
    const parent: Element | null = node.parentElement;
    if (!parent) break;
    const same = Array.from(parent.children).filter((c) => c.tagName === node!.tagName);
    parts.unshift(same.length > 1 ? `${tag}:nth-of-type(${same.indexOf(node) + 1})` : tag);
    node = parent;
  }
  return parts.join(" > ");
}

/** Where it's made in the code, from the data-src stamps (feedback-source-loader.cjs): page code first, shared parts last. */
export function sourceFor(el: Element): string[] {
  const seen: string[] = [];
  for (let node: Element | null = el; node && seen.length < 8; node = node.parentElement) {
    const s = node.getAttribute("data-src");
    if (s && !seen.includes(s)) seen.push(s);
  }
  const shared = (s: string) => s.startsWith("components/ui/");
  return [...seen.filter((s) => !shared(s)), ...seen.filter(shared)].slice(0, 5);
}

export function describe(el: Element): FeedbackElement {
  const r = el.getBoundingClientRect();
  const word = roleWord(el);
  const name = nameOf(el);
  const heading = headingFor(el);
  return {
    label: name ? `${word}: ${name}` : word,
    role: word,
    text: clean((el as HTMLElement).innerText ?? el.textContent, 300) || undefined,
    selector: selectorFor(el),
    heading: heading || undefined,
    path: [heading, name ? `${word}: ${name}` : word].filter(Boolean).join(" › "),
    source: sourceFor(el),
    rect: { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) },
    viewport: { w: innerWidth, h: innerHeight },
  };
}

// ---- Screenshots ---------------------------------------------------------------------------------

const isFeedbackUi = (n: Node) => n instanceof Element && !!n.closest?.("[data-feedback-ui]");

/** A picture of the screen as it is now (without the feedback panel). Falls back to the browser's own
 * screen capture (it asks first) if the page can't be drawn. */
export async function captureScreen(): Promise<HTMLCanvasElement> {
  try {
    const { domToCanvas } = await import("modern-screenshot");
    const canvas = await domToCanvas(document.body, {
      width: innerWidth, height: innerHeight, scale: Math.min(2, devicePixelRatio || 1),
      backgroundColor: getComputedStyle(document.body).backgroundColor,
      filter: (n) => !isFeedbackUi(n),
      features: { restoreScrollPosition: true },
      timeout: 15000,
    });
    if (canvas.width > 0) return canvas;
    throw new Error("empty");
  } catch {
    return captureWithBrowser();
  }
}

async function captureWithBrowser(): Promise<HTMLCanvasElement> {
  const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false, preferCurrentTab: true } as DisplayMediaStreamOptions);
  try {
    const video = document.createElement("video");
    video.srcObject = stream;
    video.muted = true;
    await video.play();
    await new Promise((r) => setTimeout(r, 250));
    const c = document.createElement("canvas");
    c.width = video.videoWidth;
    c.height = video.videoHeight;
    c.getContext("2d")?.drawImage(video, 0, 0);
    return c;
  } finally {
    stream.getTracks().forEach((t) => t.stop());
  }
}

/** Cut out part of a screen picture; the box is in page (CSS) pixels. */
export function crop(screen: HTMLCanvasElement, box: { x: number; y: number; w: number; h: number }): HTMLCanvasElement {
  const k = screen.width / innerWidth;
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(box.w * k));
  c.height = Math.max(1, Math.round(box.h * k));
  c.getContext("2d")?.drawImage(screen, box.x * k, box.y * k, box.w * k, box.h * k, 0, 0, c.width, c.height);
  return c;
}

/** As small a file as looks right: PNG for small or simple pictures, JPEG for big ones. Shrunk to 2000px wide at most. */
export function toDataUrl(canvas: HTMLCanvasElement): { data: string; width: number; height: number } {
  let c = canvas;
  if (c.width > 2000) {
    const s = 2000 / c.width;
    const small = document.createElement("canvas");
    small.width = 2000;
    small.height = Math.round(c.height * s);
    small.getContext("2d")?.drawImage(c, 0, 0, small.width, small.height);
    c = small;
  }
  let data = c.toDataURL("image/png");
  if (data.length > 1_500_000) data = c.toDataURL("image/jpeg", 0.85);
  return { data, width: c.width, height: c.height };
}
