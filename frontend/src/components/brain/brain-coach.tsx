"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrainBuddy } from "@/components/brain/brain-buddy";
import { findOnPage, spotlight } from "@/components/brain/show-me";
import { coachState, dismissTip, setTourDone, type CoachState, type CoachTip } from "@/lib/brain-coach";

/** The Brain as a coach, beside every page (mounted by BrainProvider):
 *  - **tips**: at most one, for the page you're on (rules in backend app/brain/coach.py), a moment after it opens;
 *    "Not now" hides it for a week, "Got it" for good. Never while the chat or the tour is open.
 *  - **the welcome tour**: on your first visit to Home, the Brain points at the few things that matter for your role.
 *    Steps whose target you can't see (a hidden section) are skipped. Settings > "Take the tour again" replays it.
 *  - **celebrations**: `celebrate("...")` from lib/celebrate.ts shows a short cheer.
 * Tips and celebrations each have an off switch in Settings > The Brain. Everything respects reduced motion. */

type Step = { target?: string; title: string; text: string };
const side = (href: string) => `[data-sidebar="sidebar"] a[href="${href}"]`;
const ASK = "button[title^='Ask the Brain']";
const START: Step = { title: "Hi, I'm the Brain", text: "I'll show you around in a few quick steps. You can skip at any point." };
const END: Step = { title: "That's the tour", text: "I'll pop up now and then with something worth doing. You can switch that off in Settings, under The Brain." };

export const TOURS: Record<string, Step[]> = {
  sales: [
    START,
    { target: side("/automations/today"), title: "Today", text: "Your list for the day: follow-ups, renewals and promised call-backs that are due." },
    { target: side("/sales/deals"), title: "Bookings", text: "Every booking you make lives here. Confirm it once the client has said yes, then send them the confirmation from the booking." },
    { target: `${side("/activities")}, ${side("/reminders")}`, title: "Calendar & Reminders", text: "Calls, meetings and to-dos, and the reminders you set with Remind me on any contact or company." },
    { target: "[data-tour='titles'] > *", title: "Which title", text: "Switch between titles here. Contacts, companies and lists all follow it." },
    { target: ASK, title: "Ask me anything", text: "Stuck? Ask how something works, or about a client. I only answer about what you can see." },
    END,
  ],
  data_manager: [
    START,
    { target: side("/automations/review"), title: "Review Queue", text: "Suggestions from the automations wait here for someone to check - booking checks, new contacts, bounced emails and more." },
    { target: side("/sales/invoicing"), title: "Invoicing", text: "What's ready to invoice, and invoices that don't match their booking." },
    { target: "[data-tour='automations']", title: "Automations", text: "What each automation found, when it last ran, and its settings." },
    { target: side("/data-health"), title: "Data Health", text: "Gaps and duplicates in the contacts and companies, with a way to fix each." },
    { target: ASK, title: "Ask me anything", text: "Ask how something works, or about a client, a booking or the figures." },
    END,
  ],
  admin: [
    START,
    { target: "a[title='Settings']", title: "Settings", text: "Add the team, choose who sees which sections, and set your own preferences." },
    { target: "[data-tour='automations']", title: "Automations", text: "Switch automations on and off, see what they found and what the Brain costs." },
    { target: side("/automations/review"), title: "Review Queue", text: "Everything the automations want a person to check." },
    { target: ASK, title: "Ask me anything", text: "Ask how something works, or about a client, a booking or the figures." },
    END,
  ],
};
export const tourId = (role?: string) => `welcome-${role && TOURS[role] ? role : "sales"}`;

function visibleEl(sel?: string): HTMLElement | null {
  if (!sel) return null;
  for (const el of Array.from(document.querySelectorAll<HTMLElement>(sel))) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) return el;
  }
  return null;
}

export function BrainCoach({ role, panelOpen }: { role?: string; panelOpen: boolean }) {
  const pathname = usePathname() || "/";
  const [state, setState] = useState<CoachState | null>(null);
  const [tip, setTip] = useState<CoachTip | null>(null);
  const [cheer, setCheer] = useState<string | null>(null);
  const [step, setStep] = useState<number | null>(null);
  const celebrationsOn = useRef(true);

  // tips (and the tour, on Home) for each page
  useEffect(() => {
    if (pathname.includes("/print") || pathname.startsWith("/login")) return;
    let live = true;
    const t = setTimeout(async () => {
      try {
        const s = await coachState(pathname);
        if (!live) return;
        setState(s);
        celebrationsOn.current = s.celebrations;
        const id = tourId(role);
        if (pathname === "/" && !s.tours_done.includes(id) && window.innerWidth >= 900) setStep(0);
        else setTip(s.tip);
      } catch { /* the coach is a nice-to-have: never get in the way */ }
    }, 1200);
    return () => { live = false; clearTimeout(t); setTip(null); };
  }, [pathname, role]);

  // celebrations from anywhere
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const on = (e: Event) => {
      if (!celebrationsOn.current) return;
      setCheer((e as CustomEvent<{ message: string }>).detail?.message || "Done");
      clearTimeout(timer);
      timer = setTimeout(() => setCheer(null), 3600);
    };
    window.addEventListener("brain:celebrate", on);
    return () => { window.removeEventListener("brain:celebrate", on); clearTimeout(timer); };
  }, []);

  const closeTip = useCallback((forever: boolean) => {
    if (!tip) return;
    void dismissTip(tip.id, forever).catch(() => {});
    setTip(null);
  }, [tip]);

  const steps = TOURS[role ?? ""] ?? TOURS.sales;
  const finishTour = useCallback(() => {
    setStep(null);
    void setTourDone(tourId(role)).catch(() => {});
  }, [role]);

  if (step !== null) return <Tour steps={steps} step={step} setStep={setStep} onFinish={finishTour} />;
  if (cheer) return <Bubble mood="celebrating" live="polite"><p className="text-sm font-semibold">{cheer}</p></Bubble>;
  if (!tip || panelOpen || !state?.tips) return null;
  return (
    <Bubble mood={tip.mood} live="polite" onClose={() => closeTip(false)}>
      <p className="text-sm">{tip.text}</p>
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        {tip.link && tip.action && (
          <Button size="xs" nativeButton={false} render={<Link href={tip.link} />} onClick={() => setTip(null)}>{tip.action}</Button>
        )}
        {tip.show && (
          <Button size="xs" onClick={() => { const el = findOnPage(tip.show!); if (el) spotlight(el); }}>{tip.action || "Show me"}</Button>
        )}
        <Button size="xs" variant="ghost" onClick={() => closeTip(!!tip.forever)}>{tip.forever ? "Got it" : "Not now"}</Button>
      </div>
    </Bubble>
  );
}

/** The Brain with a speech bubble, just above the Ask the Brain button. */
function Bubble({ mood, children, onClose, live }: { mood: "happy" | "pointing" | "celebrating"; children: React.ReactNode; onClose?: () => void; live?: "polite" }) {
  return (
    <div data-feedback-ui="" role="status" aria-live={live}
      className="fixed bottom-28 right-4 z-[2147481000] flex w-[22rem] max-w-[calc(100vw-2rem)] items-end gap-2 print:hidden">
      <BrainBuddy mood={mood} size={56} className="shrink-0" />
      <div className="relative min-w-0 flex-1 rounded-2xl rounded-bl-sm border border-border bg-popover p-3 pr-8 text-popover-foreground shadow-xl">
        {children}
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Close" className="absolute right-2 top-2 rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground">
            <X className="size-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

function Tour({ steps, step, setStep, onFinish }: { steps: Step[]; step: number; setStep: (n: number) => void; onFinish: () => void }) {
  // only the steps whose target is on screen for this person (a hidden section's step is skipped)
  const [shown] = useState(() => steps.filter((s) => !s.target || visibleEl(s.target)));
  const s = shown[Math.min(step, shown.length - 1)];
  const [box, setBox] = useState<DOMRect | null>(null);
  useLayoutEffect(() => {
    const measure = () => setBox(visibleEl(s.target)?.getBoundingClientRect() ?? null);
    visibleEl(s.target)?.scrollIntoView({ block: "nearest" });
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => { window.removeEventListener("resize", measure); window.removeEventListener("scroll", measure, true); };
  }, [s]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onFinish(); };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onFinish]);

  const last = step >= shown.length - 1;
  const W = 340;
  let pos: React.CSSProperties = { left: "50%", top: "50%", transform: "translate(-50%, -50%)" };
  if (box) {
    const right = box.right + 16 + W < window.innerWidth;
    const left = right ? box.right + 16 : Math.max(16, box.left - 16 - W);
    const top = Math.min(Math.max(16, box.top + box.height / 2 - 70), window.innerHeight - 220);
    pos = { left, top };
  }
  return (
    <div data-feedback-ui="" className="fixed inset-0 z-[2147482000] print:hidden" role="dialog" aria-modal="true" aria-label="Welcome tour">
      {box ? (
        <div aria-hidden="true" className="pointer-events-none fixed rounded-xl transition-all duration-300"
          style={{ left: box.left - 6, top: box.top - 6, width: box.width + 12, height: box.height + 12,
            border: "3px solid var(--primary)", boxShadow: "0 0 0 9999px color-mix(in oklab, var(--foreground) 40%, transparent)" }} />
      ) : (
        <div aria-hidden="true" className="fixed inset-0" style={{ background: "color-mix(in oklab, var(--foreground) 40%, transparent)" }} />
      )}
      <div className="fixed flex items-start gap-2" style={{ ...pos, width: W }}>
        <BrainBuddy mood={box ? "pointing" : last ? "celebrating" : "waving"} size={60} className="shrink-0" />
        <div className="min-w-0 flex-1 rounded-2xl border border-border bg-popover p-4 text-popover-foreground shadow-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{step + 1} of {shown.length}</p>
          <h2 className="mt-0.5 text-base font-bold">{s.title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{s.text}</p>
          <div className="mt-3 flex items-center gap-1.5">
            {!last && <Button size="xs" variant="ghost" onClick={onFinish}>Skip the tour</Button>}
            <span className="ml-auto" />
            {step > 0 && <Button size="xs" variant="outline" onClick={() => setStep(step - 1)}>Back</Button>}
            <Button size="xs" autoFocus onClick={() => (last ? onFinish() : setStep(step + 1))}>{last ? "Done" : "Next"}</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
