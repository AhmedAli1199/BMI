"use client";

import { useEffect, useImperativeHandle, useRef, useState } from "react";
import { ArrowUp, Check, CheckCircle2, Copy, Crosshair, ExternalLink, Loader2, MapPin, Mic, ScanLine, Square, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { toast } from "sonner";
import type { FeedbackElement } from "@/lib/feedback-types";
import type { BrainContext, BrainMessage } from "@/lib/brain-types";
import { askBrain } from "@/lib/brain-stream";
import { brainAnswerToFeedback, brainConversation, brainSuggestions, rateBrainAnswer } from "@/lib/brain-actions";
import { browserContext, captureScreen, crop, toDataUrl } from "@/lib/feedback-capture";
import { friendlyError } from "@/lib/errors";
import { useSpeech } from "@/lib/use-speech";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { AnnotateDialog } from "@/components/feedback/annotate-dialog";
import { AreaOverlay, PickOverlay } from "@/components/feedback/capture-overlay";
import { BrainBuddy } from "@/components/brain/brain-buddy";
import { BrainMarkdown } from "@/components/brain/brain-markdown";

export type Shot = { key: string; data: string; width: number; height: number; label: string; canvas?: HTMLCanvasElement };
export type Pointed = FeedbackElement & { key: string };
type Pending = { text: string; steps: string[] };
type Turn = BrainMessage & { localImages?: string[] };

const newKey = () => Math.random().toString(36).slice(2, 10);
const UUID = "[0-9a-f-]{36}";

/** What's on screen right now: the page, its heading and the record it shows. */
export function pageContext(): BrainContext {
  const path = window.location.pathname;
  const h1 = document.querySelector("main h1, [data-slot=sidebar-inset] h1, h1");
  const title = (h1?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 200);
  let record: BrainContext["record"];
  let m: RegExpMatchArray | null;
  if ((m = path.match(new RegExp(`^/sales/deals/(${UUID})`)))) record = { kind: "booking", id: m[1], label: title };
  else if ((m = path.match(new RegExp(`^/sales/orders/(${UUID})`)))) record = { kind: "booking item", id: m[1], label: title };
  else if ((m = path.match(new RegExp(`^/sales/editions/(${UUID})`)))) record = { kind: "edition", id: m[1], label: title };
  else if ((m = path.match(new RegExp(`^/sales/proposals/(${UUID})`)))) record = { kind: "proposal", id: m[1], label: title };
  const errors = (browserContext().errors as { message?: string }[]).filter((e) => e.message).slice(-5).map((e) => ({ message: String(e.message) }));
  return { page_path: path, page_title: title, record, errors };
}

export type Seed = { question?: string; elements?: Pointed[]; shots?: Shot[]; send?: boolean };
export type ChatHandle = { seed: (s: Seed) => void };

/** The conversation: questions, streamed answers with live steps, "Show me", follow-ups, ratings, attachments. */
export function BrainChat({ variant, conversationId, onConversation, seed, handle, userName }: {
  variant: "panel" | "page";
  conversationId: string | null;
  onConversation: (id: string | null) => void;
  /** Handed over when it opens (e.g. "Ask AI" with something already pointed at). */
  seed?: Seed | null;
  handle?: React.Ref<ChatHandle>;
  userName?: string;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const [input, setInput] = useState("");
  const [elements, setElements] = useState<Pointed[]>([]);
  const [shots, setShots] = useState<Shot[]>([]);
  const [mode, setMode] = useState<null | "pick" | "area">(null);
  const [screen, setScreen] = useState<HTMLCanvasElement | null>(null);
  const [marking, setMarking] = useState<{ key: string; canvas: HTMLCanvasElement; label: string } | null>(null);
  const [intro, setIntro] = useState<{ configured: boolean; questions: string[]; guide: string | null } | null>(null);
  const [loading, setLoading] = useState(!!conversationId);
  const scroller = useRef<HTMLDivElement>(null);
  const abort = useRef<AbortController | null>(null);
  const speech = useSpeech((t) => setInput((v) => (v ? `${v} ${t}` : t)), "/api/files/brain/transcribe");

  // Open an earlier conversation (the parent remounts this when someone picks a different one).
  useEffect(() => {
    if (!conversationId) return;
    brainConversation(conversationId).then((c) => setTurns(c.messages))
      .catch((e) => toast.error(friendlyError(e, "Couldn't open that conversation")))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // What people usually ask on this page.
  useEffect(() => {
    brainSuggestions(window.location.pathname).then(setIntro).catch(() => setIntro({ configured: true, questions: [], guide: null }));
  }, []);

  // Something else (the Ask AI button, a "how does this work?" link) hands over a question or attachments.
  function handleSeed(sd: Seed) {
    if (sd.elements?.length) setElements((xs) => [...xs, ...sd.elements!].slice(-4));
    if (sd.shots?.length) setShots((xs) => [...xs, ...sd.shots!].slice(-3));
    if (sd.question) {
      if (sd.send) void send(sd.question, sd.elements ?? [], sd.shots ?? []);
      else setInput(sd.question);
    }
  }
  useImperativeHandle(handle, () => ({ seed: handleSeed }));
  useEffect(() => {
    if (!seed) return;
    const t = setTimeout(() => handleSeed(seed), 0);
    return () => clearTimeout(t);
    // only the seed it was opened with
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" }); }, [turns.length, pending?.text, pending?.steps.length]);
  useEffect(() => () => abort.current?.abort(), []);

  async function send(text: string, els = elements, pics = shots) {
    const question = text.trim();
    if ((!question && !els.length && !pics.length) || pending) return;
    const ctx = { ...pageContext(), mode: variant === "panel" ? "ask" as const : "chat" as const, elements: els.map(({ key: _k, ...e }) => { void _k; return e; }) };
    const local: Turn = {
      id: `local-${newKey()}`, role: "user", text: question || "What is this and how do I use it?", context: ctx, rating: null,
      feedback_id: null, created_at: new Date().toISOString(), images: [], localImages: pics.map((s) => s.data),
    };
    setTurns((t) => [...t, local]);
    setInput(""); setElements([]); setShots([]);
    setPending({ text: "", steps: [] });
    abort.current = new AbortController();
    let convo = conversationId;
    try {
      await askBrain({ conversation_id: conversationId, message: question, context: ctx,
        images: pics.map((s) => ({ data: s.data, label: s.label, width: s.width, height: s.height })) }, {
        meta: (m) => { convo = m.conversation_id; },
        step: (label) => setPending((p) => (p ? { ...p, steps: [...p.steps, label] } : p)),
        text: (d) => setPending((p) => (p ? { ...p, text: p.text + d } : p)),
        done: (msg) => setTurns((t) => [...t, msg]),
      }, abort.current.signal);
      if (convo && convo !== conversationId) onConversation(convo);
    } catch (e) {
      if ((e as Error)?.name !== "AbortError") toast.error(friendlyError(e, "Couldn't get an answer just now. Please try again."));
    } finally { setPending(null); }
  }

  function addShot(canvas: HTMLCanvasElement, label: string) {
    const d = toDataUrl(canvas);
    setShots((s) => [...s, { key: newKey(), ...d, label, canvas }].slice(-3));
  }

  async function picked(el: Element, d: FeedbackElement) {
    setMode(null);
    setElements((xs) => [...xs, { ...d, key: newKey() }].slice(-4));
    try {
      const r = el.getBoundingClientRect();
      const pad = 24;
      const box = { x: Math.max(0, r.left - pad), y: Math.max(0, r.top - pad), w: 0, h: 0 };
      box.w = Math.min(innerWidth - box.x, r.width + pad * 2);
      box.h = Math.min(innerHeight - box.y, r.height + pad * 2);
      if (box.w > 4 && box.h > 4) addShot(crop(await captureScreen(), box), d.label);
    } catch { /* the description is enough */ }
  }

  async function snap() {
    setMode("area"); setScreen(null);
    try { setScreen(await captureScreen()); }
    catch { setMode(null); toast.error("Couldn't take a picture of the page. Describe it in words instead."); }
  }

  const empty = turns.length === 0 && !pending && !loading;
  const off = intro && !intro.configured;
  const canSend = !pending && !off && !!(input.trim() || elements.length || shots.length);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {mode === "pick" && <PickOverlay onPick={picked} onCancel={() => { setMode(null); }} />}
      {mode === "area" && <AreaOverlay screen={screen} onCancel={() => { setMode(null); setScreen(null); }}
        onDone={(box) => { const s = screen; setMode(null); setScreen(null); if (s) setMarking({ key: newKey(), canvas: box ? crop(s, box) : s, label: box ? "Part of the screen" : "The whole screen" }); }} />}
      {marking && <AnnotateDialog key={marking.key} image={marking.canvas} open onCancel={() => setMarking(null)} onDone={(c) => { addShot(c, marking.label); setMarking(null); }} />}

      <div ref={scroller} className={`flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto ${variant === "page" ? "px-2 py-4 sm:px-6" : "px-4 py-4"}`} aria-live="polite">
        {loading && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Opening…</p>}
        {empty && (
          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-2.5">
              <BrainBuddy mood={off ? "sleepy" : "waving"} size={60} className="shrink-0" />
              <div className="text-sm">
                <p className="font-semibold">Hi{userName ? ` ${userName.split(" ")[0]}` : ""}, what would you like to know?</p>
                <p className="mt-0.5 text-muted-foreground">
                  Ask how anything in BMI Brain works, about a client, the figures, the editorial plan, your Review Queue or the automations. Point at something on the screen and I&apos;ll explain it.
                </p>
              </div>
            </div>
            {intro?.guide && <p className="text-xs text-muted-foreground">You&apos;re on: <span className="font-medium text-foreground">{intro.guide}</span></p>}
            {off && <p className="rounded-lg border border-border px-3 py-2 text-xs" style={{ color: "var(--warn)" }}>The Brain isn&apos;t switched on yet. An administrator can switch it on.</p>}
            {!!intro?.questions.length && !off && (
              <div className="flex flex-col gap-1.5">
                {intro.questions.map((q) => (
                  <button key={q} type="button" onClick={() => void send(q)}
                    className="rounded-lg border border-border/80 bg-background px-3 py-2 text-left text-[13px] hover:border-primary hover:text-primary">{q}</button>
                ))}
              </div>
            )}
          </div>
        )}
        {turns.map((t, i) => t.role === "user"
          ? <UserTurn key={t.id} t={t} />
          : <AnswerTurn key={t.id} t={t} last={i === turns.length - 1 && !pending} onAsk={(q) => void send(q, [], [])}
              onChange={(n) => setTurns((xs) => xs.map((x) => (x.id === n.id ? { ...x, ...n } : x)))} />)}
        {pending && (
          <div className="flex items-start gap-2.5">
            {!pending.text && <BrainBuddy mood="thinking" head size={26} className="brain-busy mt-0.5 shrink-0" />}
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            {pending.steps.length > 0 && (
              <ul className="flex flex-col gap-1 text-xs text-muted-foreground">
                {pending.steps.map((s, i) => (
                  <li key={i} className="flex items-center gap-1.5">
                    {i === pending.steps.length - 1 && !pending.text ? <Loader2 className="size-3 animate-spin" /> : <Check className="size-3" style={{ color: "var(--ok)" }} />} {s}…
                  </li>
                ))}
              </ul>
            )}
            {pending.text ? <BrainMarkdown text={pending.text} streaming />
              : !pending.steps.length && <p className="text-sm text-muted-foreground">Thinking…</p>}
          </div>
          </div>
        )}
      </div>

      <div className="border-t border-border/70 bg-popover px-3 py-2.5">
        {(elements.length > 0 || shots.length > 0) && (
          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            {elements.map((e) => (
              <span key={e.key} className="inline-flex max-w-[14rem] items-center gap-1 rounded-full border border-border bg-muted/40 py-0.5 pl-2 pr-1 text-[11px]">
                <MapPin className="size-3 shrink-0 text-primary" aria-hidden="true" /><span className="truncate">{e.label}</span>
                <button type="button" aria-label={`Remove ${e.label}`} onClick={() => setElements(elements.filter((x) => x.key !== e.key))}><X className="size-3" /></button>
              </span>
            ))}
            {shots.map((s) => (
              <span key={s.key} className="group relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={s.data} alt={s.label} className="h-10 w-14 rounded border border-border object-cover object-top" />
                <button type="button" aria-label="Remove this screenshot" onClick={() => setShots(shots.filter((x) => x.key !== s.key))}
                  className="absolute -right-1.5 -top-1.5 hidden size-4 items-center justify-center rounded-full bg-foreground text-background group-hover:flex"><X className="size-2.5" /></button>
              </span>
            ))}
          </div>
        )}
        <div className="relative">
          <Textarea value={input} onChange={(e) => setInput(e.target.value)} rows={variant === "page" ? 3 : 2} disabled={!!off}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (canSend) void send(input); } }}
            placeholder={elements.length || shots.length ? "What would you like to know about this?" : "Ask about a client, the figures, or how something works…"}
            aria-label="Your question" className="min-h-0 resize-none pr-11 text-sm" />
          <Button size="icon-sm" className="absolute bottom-1.5 right-1.5" aria-label="Send" disabled={!canSend} onClick={() => void send(input)}>
            {pending ? <Loader2 className="size-3.5 animate-spin" /> : <ArrowUp className="size-3.5" />}
          </Button>
        </div>
        <div className="mt-1.5 flex items-center gap-1">
          <Button size="xs" variant="ghost" className="gap-1 text-muted-foreground" disabled={!!pending} onClick={() => setMode("pick")}>
            <Crosshair className="size-3.5" /> Point at it
          </Button>
          <Button size="xs" variant="ghost" className="gap-1 text-muted-foreground" disabled={!!pending} onClick={() => void snap()}>
            <ScanLine className="size-3.5" /> Screenshot
          </Button>
          <Button size="xs" variant="ghost" className="gap-1 text-muted-foreground" disabled={speech.state === "writing" || !!off} onClick={speech.toggle}
            aria-label={speech.state === "listening" ? "Stop recording" : "Say it instead"}>
            {speech.state === "listening" ? <Square className="size-3.5" style={{ color: "var(--destructive)" }} /> : speech.state === "writing" ? <Loader2 className="size-3.5 animate-spin" /> : <Mic className="size-3.5" />}
            {speech.state === "listening" ? "Stop" : "Speak"}
          </Button>
          {pending && <Button size="xs" variant="ghost" className="ml-auto text-muted-foreground" onClick={() => abort.current?.abort()}>Stop</Button>}
        </div>
      </div>
    </div>
  );
}

function UserTurn({ t }: { t: Turn }) {
  const els = t.context?.elements ?? [];
  const pics = t.localImages?.length ? t.localImages : t.images.map((i) => `/api/files/brain/images/${i.id}`);
  return (
    <div className="flex flex-col items-end gap-1">
      {(els.length > 0 || pics.length > 0) && (
        <div className="flex flex-wrap justify-end gap-1">
          {els.map((e, i) => <span key={i} className="inline-flex max-w-[14rem] items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground"><MapPin className="size-3 text-primary" aria-hidden="true" /><span className="truncate">{e.label}</span></span>)}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {pics.map((src, i) => <img key={i} src={src} alt="Screenshot sent with the question" className="h-12 w-16 rounded border border-border object-cover object-top" />)}
        </div>
      )}
      <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-3 py-2 text-sm text-primary-foreground">{t.text}</p>
    </div>
  );
}

function AnswerTurn({ t, last, onAsk, onChange }: { t: Turn; last: boolean; onAsk: (q: string) => void; onChange: (t: Partial<Turn> & { id: string }) => void }) {
  const [asking, setAsking] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<{ id: string; number: number } | null>(null);

  async function rate(r: 1 | -1) {
    try { const res = await rateBrainAnswer(t.id, t.rating === r ? null : r); onChange({ id: t.id, rating: res.rating }); if (r === -1 && res.rating === -1) setAsking(true); }
    catch (e) { toast.error(friendlyError(e, "Couldn't save that")); }
  }

  async function tellTeam() {
    setBusy(true);
    try {
      const r = await brainAnswerToFeedback(t.id, note);
      setSent({ id: r.feedback_id, number: r.number }); setAsking(false);
      onChange({ id: t.id, feedback_id: r.feedback_id, rating: -1 });
    } catch (e) { toast.error(friendlyError(e, "Couldn't send that to the team")); }
    finally { setBusy(false); }
  }

  const suggestions = t.context?.suggestions ?? [];
  return (
    <div className="flex flex-col gap-2">
      <BrainMarkdown text={t.text} />
      <div className="flex flex-wrap items-center gap-0.5 text-muted-foreground">
        <Button size="icon-xs" variant="ghost" aria-label="Helpful" aria-pressed={t.rating === 1} onClick={() => void rate(1)}>
          <ThumbsUp className="size-3.5" style={t.rating === 1 ? { color: "var(--ok)" } : undefined} />
        </Button>
        <Button size="icon-xs" variant="ghost" aria-label="Not helpful" aria-pressed={t.rating === -1} onClick={() => void rate(-1)}>
          <ThumbsDown className="size-3.5" style={t.rating === -1 ? { color: "var(--destructive)" } : undefined} />
        </Button>
        <Button size="icon-xs" variant="ghost" aria-label="Copy the answer"
          onClick={() => { void navigator.clipboard.writeText(t.text.replace(/\[\[show:[^\]]+\]\]/g, "").trim()).then(() => toast.success("Copied")); }}>
          <Copy className="size-3.5" />
        </Button>
        {!t.feedback_id && !sent && !asking && (
          <button type="button" className="ml-1 text-[11px] hover:text-foreground hover:underline" onClick={() => setAsking(true)}>This didn&apos;t help</button>
        )}
        {(sent || t.feedback_id) && (
          <a href={`/feedback?open=${sent?.id ?? t.feedback_id}`} target="_blank" rel="noreferrer" className="ml-1 inline-flex items-center gap-1 text-[11px] hover:underline">
            <CheckCircle2 className="size-3" style={{ color: "var(--ok)" }} /> Sent to the team{sent ? ` (#${sent.number})` : ""} <ExternalLink className="size-3" />
          </a>
        )}
      </div>
      {asking && (
        <div className="flex flex-col gap-1.5 rounded-lg border border-border/80 bg-muted/30 p-2">
          <p className="text-xs font-medium">Tell the team, so the answer (or the screen) gets better.</p>
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="What did you need? (optional)" className="text-xs" aria-label="What you needed" />
          <div className="flex justify-end gap-1.5">
            <Button size="xs" variant="ghost" onClick={() => setAsking(false)}>Not now</Button>
            <Button size="xs" disabled={busy} onClick={() => void tellTeam()}>{busy && <Loader2 className="size-3 animate-spin" />} Send to the team</Button>
          </div>
        </div>
      )}
      {last && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map((q) => (
            <button key={q} type="button" onClick={() => onAsk(q)}
              className="rounded-full border border-border bg-background px-2.5 py-1 text-xs hover:border-primary hover:text-primary">{q}</button>
          ))}
        </div>
      )}
    </div>
  );
}
