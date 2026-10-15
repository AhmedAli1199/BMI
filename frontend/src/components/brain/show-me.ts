"use client";

/** "Show me": find the button/link with that label on the page and spotlight it for a few seconds. */

const CANDIDATES = "button, a, [role=button], [role=tab], [role=menuitem], [role=radio], [role=checkbox], label, summary, th, h1, h2, h3, legend";

const norm = (s: string | null | undefined) => (s || "").replace(/\s+/g, " ").replace(/[…:*]+$/g, "").trim().toLowerCase();

function visible(el: Element) {
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return false;
  const cs = getComputedStyle(el);
  return cs.visibility !== "hidden" && cs.display !== "none";
}

export function findOnPage(label: string): HTMLElement | null {
  const want = norm(label);
  if (!want) return null;
  const all = Array.from(document.querySelectorAll<HTMLElement>(CANDIDATES))
    .filter((el) => !el.closest("[data-brain-panel], [data-feedback-ui]") && visible(el));
  const name = (el: HTMLElement) => [norm(el.getAttribute("aria-label")), norm(el.textContent), norm(el.getAttribute("title"))];
  return all.find((el) => name(el).includes(want))
    ?? all.find((el) => name(el).some((n) => n.startsWith(want) && n.length - want.length < 25))
    ?? null;
}

let current: { stop: () => void } | null = null;

export function spotlight(el: HTMLElement) {
  current?.stop();
  el.scrollIntoView({ block: "center", behavior: "smooth" });
  const ring = document.createElement("div");
  ring.setAttribute("data-brain-spotlight", "");
  ring.setAttribute("aria-hidden", "true");
  Object.assign(ring.style, {
    position: "fixed", pointerEvents: "none", zIndex: "2147482500", borderRadius: "10px",
    border: "3px solid var(--primary)", boxShadow: "0 0 0 9999px color-mix(in oklab, var(--foreground) 22%, transparent), 0 0 24px 4px color-mix(in oklab, var(--primary) 55%, transparent)",
    transition: "all 120ms ease-out", animation: "brain-pulse 1.1s ease-in-out infinite",
  });
  document.body.appendChild(ring);
  let alive = true;
  const place = () => {
    if (!alive) return;
    const r = el.getBoundingClientRect();
    Object.assign(ring.style, { left: `${r.left - 6}px`, top: `${r.top - 6}px`, width: `${r.width + 12}px`, height: `${r.height + 12}px` });
    requestAnimationFrame(place);
  };
  place();
  const stop = () => { alive = false; ring.remove(); document.removeEventListener("pointerdown", stop, true); if (current?.stop === stop) current = null; };
  document.addEventListener("pointerdown", stop, true);
  setTimeout(stop, 4500);
  current = { stop };
}

/** True when it was found and highlighted. */
export function showMe(label: string): boolean {
  const el = findOnPage(label);
  if (!el) return false;
  spotlight(el);
  return true;
}
