"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { CheckCircle2, Crosshair, ExternalLink, Info, Loader2, MapPin, MessageSquarePlus, Mic, Monitor, ScanLine, Square, ThumbsUp, X } from "lucide-react";
import { toast } from "sonner";
import { FEEDBACK_KINDS, type FeedbackElement, type FeedbackItem, type FeedbackKind, type FeedbackPin } from "@/lib/feedback-types";
import { feedbackPins, similarFeedback, toggleMeToo } from "@/lib/feedback-actions";
import { browserContext, captureScreen, crop, installProblemLog, toDataUrl } from "@/lib/feedback-capture";
import { friendlyError } from "@/lib/errors";
import { useSpeech } from "@/lib/use-speech";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { AnnotateDialog } from "@/components/feedback/annotate-dialog";
import { AreaOverlay, PickOverlay } from "@/components/feedback/capture-overlay";
import { FeedbackPins } from "@/components/feedback/feedback-pins";

type Shot = { key: string; data: string; width: number; height: number; label: string; canvas: HTMLCanvasElement };
type Marked = FeedbackElement & { key: string };

const newKey = () => Math.random().toString(36).slice(2, 10);

/** The Feedback button on every page: say what's wrong, point at it, snap a screenshot, see what's already been said. */
export function FeedbackWidget() {
  const pathname = usePathname() || "/";
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<null | "pick" | "area">(null);
  const [screen, setScreen] = useState<HTMLCanvasElement | null>(null);
  const [marking, setMarking] = useState<{ key: string; canvas: HTMLCanvasElement; label: string; replace?: string } | null>(null);
  const [busy, setBusy] = useState<null | "picture" | "sending">(null);

  const [kind, setKind] = useState<FeedbackKind>("broken");
  const [message, setMessage] = useState("");
  const [elements, setElements] = useState<Marked[]>([]);
  const [shots, setShots] = useState<Shot[]>([]);
  const [page, setPage] = useState<{ path: string; title: string; url: string } | null>(null);
  const [sent, setSent] = useState<FeedbackItem | null>(null);

  const [similar, setSimilar] = useState<FeedbackItem[]>([]);
  const [pins, setPins] = useState<FeedbackPin[]>([]);
  const [showPins, setShowPins] = useState(false);
  const [focusPin, setFocusPin] = useState<string | null>(null);

  const speech = useSpeech((t) => setMessage((m) => (m ? `${m} ${t}` : t)));

  useEffect(() => { installProblemLog(); }, []);

  // While a pop-up or side panel is open the rest of the page can't be clicked, so the button steps aside.
  const [covered, setCovered] = useState(false);
  useEffect(() => {
    const check = () => setCovered(!!document.querySelector("[data-base-ui-inert], [data-brain-panel]"));
    const mo = new MutationObserver(check);
    mo.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["data-base-ui-inert"] });
    return () => mo.disconnect();
  }, []);

  // What's already been said about this page (the count on the button, and the dots).
  const loadPins = useCallback(() => {
    if (pathname.includes("/print")) return;
    feedbackPins(pathname).then((p) => {
      setPins(p);
      // A link from the board ("Show me on the page") turns the dots on and opens that one.
      const id = new URLSearchParams(window.location.search).get("feedback_pin");
      if (id) { setFocusPin(id); setShowPins(true); }
    }).catch(() => setPins([]));
  }, [pathname]);
  useEffect(() => { loadPins(); }, [loadPins]);

  // Others' feedback that might be the same thing.
  useEffect(() => {
    if (!open || sent) return;
    const t = setTimeout(() => {
      similarFeedback(page?.path ?? pathname, [message, ...elements.map((e) => e.label)].join(" ")).then(setSimilar).catch(() => setSimilar([]));
    }, 500);
    return () => clearTimeout(t);
  }, [open, sent, message, elements, page?.path, pathname]);

  function pageTitle() {
    // Every page has the same browser title, so use the page's own heading.
    const h1 = document.querySelector("main h1, [data-slot=sidebar-inset] h1, h1");
    return (h1?.textContent || document.title || window.location.pathname).replace(/\s+/g, " ").trim().slice(0, 200);
  }

  function notePage() {
    setPage({ path: window.location.pathname, title: pageTitle(), url: window.location.href });
  }

  function start() {
    setSent(null);
    if (!page || (!message && !elements.length && !shots.length)) notePage();
    setOpen(true);
  }

  function addShot(canvas: HTMLCanvasElement, label: string, replace?: string) {
    const d = toDataUrl(canvas);
    const shot: Shot = { key: replace ?? newKey(), ...d, label, canvas };
    setShots((s) => (replace ? s.map((x) => (x.key === replace ? shot : x)) : [...s, shot].slice(-6)));
  }

  async function picked(el: Element, d: FeedbackElement) {
    setMode(null);
    notePage();
    setElements((xs) => [...xs, { ...d, key: newKey() }].slice(-10));
    setOpen(true);
    // A close-up of what they pointed at, so nobody has to guess.
    setBusy("picture");
    try {
      const r = el.getBoundingClientRect();
      const pad = 24;
      const box = { x: Math.max(0, r.left - pad), y: Math.max(0, r.top - pad), w: 0, h: 0 };
      box.w = Math.min(innerWidth - box.x, r.width + pad * 2);
      box.h = Math.min(innerHeight - box.y, r.height + pad * 2);
      if (box.w > 4 && box.h > 4) addShot(crop(await captureScreen(), box), d.label);
    } catch { /* the description is enough */ }
    finally { setBusy(null); }
  }

  async function snap() {
    setMode("area");
    setScreen(null);
    notePage();
    try { setScreen(await captureScreen()); }
    catch { setMode(null); setOpen(true); toast.error("Couldn't take a picture of the page. Describe it in words instead."); }
  }

  function areaDone(box: { x: number; y: number; w: number; h: number } | null) {
    const s = screen;
    setMode(null);
    setScreen(null);
    setOpen(true);
    if (s) setMarking({ key: newKey(), canvas: box ? crop(s, box) : s, label: box ? "Part of the screen" : "The whole screen" });
  }

  async function send() {
    setBusy("sending");
    try {
      const where = page ?? { path: window.location.pathname, title: pageTitle(), url: window.location.href };
      const res = await fetch("/api/files/feedback", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind, message, page_path: where.path, page_title: where.title, page_url: where.url,
          elements: elements.map(({ key: _k, ...e }) => { void _k; return e; }),
          context: browserContext(),
          images: shots.map((s) => ({ data: s.data, label: s.label, width: s.width, height: s.height })),
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || "");
      setSent(body as FeedbackItem);
      setMessage(""); setElements([]); setShots([]); setKind("broken"); setPage(null); setSimilar([]);
      loadPins();
    } catch (e) {
      toast.error(friendlyError(e, "Couldn't send your feedback. Try again in a moment."));
    } finally { setBusy(null); }
  }

  if (pathname.includes("/print")) return null;
  const canSend = !!(message.trim() || elements.length || shots.length) && busy === null;
  const btn = "flex flex-1 flex-col items-center gap-1 rounded-lg border border-border bg-background px-2 py-2 text-[11px] font-medium hover:border-primary hover:text-primary disabled:opacity-50";

  return (
    <>
      {mode === "pick" && <PickOverlay onPick={picked} onCancel={() => { setMode(null); setOpen(true); }} />}
      {mode === "area" && <AreaOverlay screen={screen} onDone={areaDone} onCancel={() => { setMode(null); setScreen(null); setOpen(true); }} />}
      {marking && (
        <AnnotateDialog key={marking.key} image={marking.canvas} open onCancel={() => setMarking(null)}
          onDone={(c) => { addShot(c, marking.label, marking.replace); setMarking(null); }} />
      )}
      {showPins && pins.length > 0 && !mode && <FeedbackPins pins={pins} focusId={focusPin} onClose={() => { setShowPins(false); setFocusPin(null); }} />}

      {!open && !mode && !marking && !covered && (
        <button type="button" data-feedback-ui="" onClick={start}
          className="fixed bottom-4 right-4 z-[2147481000] flex items-center gap-1.5 rounded-full bg-primary py-2 pl-3 pr-3.5 text-xs font-semibold text-primary-foreground shadow-lg ring-1 ring-primary/30 transition hover:translate-y-[-1px] hover:shadow-xl print:hidden">
          <MessageSquarePlus className="size-4" aria-hidden="true" /> Feedback
          {pins.length > 0 && <span className="rounded-full bg-primary-foreground/20 px-1.5 text-[10px]" title="Open feedback about this page">{pins.length}</span>}
        </button>
      )}

      {open && !mode && !marking && (
        <section data-feedback-ui="" aria-label="Send feedback"
          className="fixed inset-x-2 bottom-2 z-[2147481000] flex max-h-[88vh] flex-col overflow-hidden rounded-2xl border border-border bg-popover text-popover-foreground shadow-2xl sm:inset-x-auto sm:right-4 sm:bottom-4 sm:w-[25rem] print:hidden">
          <header className="flex items-center gap-2 border-b border-border/70 px-4 py-3">
            <MessageSquarePlus className="size-4 text-primary" aria-hidden="true" />
            <h2 className="text-sm font-semibold">Feedback</h2>
            <a href="/feedback" target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">Everyone&apos;s feedback <ExternalLink className="size-3" aria-hidden="true" /></a>
            <Button size="icon-sm" variant="ghost" aria-label="Close" onClick={() => setOpen(false)}><X className="size-4" /></Button>
          </header>

          {sent ? (
            <div className="flex flex-col items-center gap-2 px-6 py-8 text-center">
              <CheckCircle2 className="size-8 text-[var(--ok,var(--primary))]" aria-hidden="true" />
              <p className="text-sm font-semibold">Thanks, that&apos;s feedback #{sent.number}.</p>
              <p className="text-xs text-muted-foreground">Everyone can see it on the feedback board, and you&apos;ll get a notification when it&apos;s looked at or fixed.</p>
              <div className="mt-2 flex gap-2">
                <a href={`/feedback?open=${sent.id}`} target="_blank" rel="noreferrer"><Button size="sm" variant="outline" className="gap-1.5">See it <ExternalLink className="size-3" /></Button></a>
                <Button size="sm" onClick={() => { setSent(null); notePage(); }}>Send more</Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3 overflow-y-auto px-4 py-3">
              <div className="grid grid-cols-2 gap-1.5" role="radiogroup" aria-label="What kind of feedback">
                {FEEDBACK_KINDS.map((k) => (
                  <button key={k.kind} type="button" role="radio" aria-checked={kind === k.kind} onClick={() => setKind(k.kind)} title={k.hint}
                    className={`rounded-lg border px-2 py-1.5 text-left text-xs font-medium transition ${kind === k.kind ? "border-primary bg-primary/10 text-primary" : "border-border hover:border-primary/60"}`}>
                    {k.label}
                  </button>
                ))}
              </div>

              <div className="relative">
                <Textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={4} className="pr-10 text-sm"
                  placeholder={kind === "idea" ? "What would you like it to do?" : "What happened, or what's confusing?"} aria-label="Your feedback" />
                <Button size="icon-sm" variant="ghost" className="absolute right-1.5 bottom-1.5" disabled={speech.state === "writing"}
                  aria-label={speech.state === "listening" ? "Stop recording" : "Say it instead"} title={speech.state === "listening" ? "Stop" : "Say it instead"} onClick={speech.toggle}>
                  {speech.state === "listening" ? <Square className="size-3.5 text-destructive" /> : speech.state === "writing" ? <Loader2 className="size-3.5 animate-spin" /> : <Mic className="size-3.5" />}
                </Button>
              </div>

              <div className="flex gap-1.5">
                <button type="button" className={btn} onClick={() => { setOpen(false); setMode("pick"); }}><Crosshair className="size-4" /> Point at it</button>
                <button type="button" className={btn} onClick={() => { setOpen(false); void snap(); }}><ScanLine className="size-4" /> Snap an area</button>
                <button type="button" className={btn} disabled={busy !== null} onClick={async () => {
                  setOpen(false); notePage(); setBusy("picture");
                  try { const c = await captureScreen(); setMarking({ key: newKey(), canvas: c, label: "The whole screen" }); }
                  catch { toast.error("Couldn't take a picture of the page. Describe it in words instead."); }
                  finally { setBusy(null); setOpen(true); }
                }}><Monitor className="size-4" /> Whole screen</button>
              </div>

              {(elements.length > 0 || shots.length > 0 || busy === "picture") && (
                <div className="flex flex-col gap-2 rounded-lg border border-border/70 bg-muted/30 p-2">
                  {elements.map((e) => (
                    <div key={e.key} className="flex items-start gap-1.5 text-xs">
                      <MapPin className="mt-0.5 size-3.5 shrink-0 text-primary" aria-hidden="true" />
                      <div className="min-w-0 flex-1"><p className="truncate font-medium">{e.label}</p>{e.heading && <p className="truncate text-muted-foreground">under {e.heading}</p>}</div>
                      <button type="button" aria-label={`Remove ${e.label}`} className="text-muted-foreground hover:text-foreground" onClick={() => setElements(elements.filter((x) => x.key !== e.key))}><X className="size-3.5" /></button>
                    </div>
                  ))}
                  {(shots.length > 0 || busy === "picture") && (
                    <div className="flex flex-wrap gap-1.5">
                      {shots.map((s) => (
                        <div key={s.key} className="group relative">
                          <button type="button" title="Mark it up" onClick={() => setMarking({ key: newKey(), canvas: s.canvas, label: s.label, replace: s.key })}
                            className="block h-16 w-24 overflow-hidden rounded-md border border-border bg-background">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={s.data} alt={s.label} className="h-full w-full object-cover object-top" />
                          </button>
                          <button type="button" aria-label="Remove this screenshot" onClick={() => setShots(shots.filter((x) => x.key !== s.key))}
                            className="absolute -right-1.5 -top-1.5 hidden size-5 items-center justify-center rounded-full bg-foreground text-background group-hover:flex"><X className="size-3" /></button>
                        </div>
                      ))}
                      {busy === "picture" && <div className="flex h-16 w-24 items-center justify-center rounded-md border border-dashed border-border"><Loader2 className="size-4 animate-spin text-muted-foreground" /></div>}
                    </div>
                  )}
                  {shots.length > 0 && <p className="text-[11px] text-muted-foreground">Click a screenshot to draw on it or hide something private.</p>}
                </div>
              )}

              {similar.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <p className="text-xs font-semibold text-muted-foreground">Already reported? Add your vote instead of sending it again.</p>
                  {similar.map((f) => <SimilarRow key={f.id} f={f} onChange={(n) => setSimilar(similar.map((x) => (x.id === n.id ? n : x)))} />)}
                </div>
              )}

              {pins.length > 0 && (
                <button type="button" onClick={() => { setShowPins(true); setOpen(false); }} className="self-start text-xs font-medium text-primary hover:underline">
                  Show the {pins.length} open on this page
                </button>
              )}

              <p className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
                <Info className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
                <span>Along with it we save this page, what you pointed at, your browser and any errors from the last few minutes, so it can be fixed quickly. Everyone at BMI can see your feedback.</span>
              </p>
            </div>
          )}

          {!sent && (
            <footer className="flex items-center gap-2 border-t border-border/70 px-4 py-2.5">
              <span className="truncate text-[11px] text-muted-foreground">On {page?.title || pathname}</span>
              <Button size="sm" className="ml-auto gap-1.5" disabled={!canSend} onClick={send}>
                {busy === "sending" && <Loader2 className="size-3.5 animate-spin" />} Send
              </Button>
            </footer>
          )}
        </section>
      )}
    </>
  );
}

function SimilarRow({ f, onChange }: { f: FeedbackItem; onChange: (f: FeedbackItem) => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <div className="flex items-start gap-2 rounded-lg border border-border/70 p-2 text-xs">
      <div className="min-w-0 flex-1">
        <a href={`/feedback?open=${f.id}`} target="_blank" rel="noreferrer" className="line-clamp-2 font-medium hover:underline">#{f.number} {f.message || f.elements[0]?.label || f.kind_label}</a>
        <p className="mt-0.5 text-muted-foreground">{f.user_name} · {f.status_label}{f.me_too.length ? ` · ${f.me_too.length} more` : ""}</p>
      </div>
      {!f.mine && (
        <Button size="sm" variant={f.me_too_mine ? "default" : "outline"} className="h-7 shrink-0 gap-1 px-2 text-xs" disabled={busy}
          onClick={async () => { setBusy(true); try { onChange(await toggleMeToo(f.id)); } catch (e) { toast.error(friendlyError(e, "Couldn't add your vote")); } finally { setBusy(false); } }}>
          <ThumbsUp className="size-3" /> {f.me_too_mine ? "Voted" : "Me too"}
        </Button>
      )}
    </div>
  );
}
