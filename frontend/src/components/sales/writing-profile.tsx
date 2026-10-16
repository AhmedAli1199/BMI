"use client";

import { useRef, useState, useTransition } from "react";
import { ArrowDown, ArrowUp, CheckCircle2, FileUp, Inbox, Loader2, Mic, RotateCcw, Sparkles, Square, Trash2, Wand2 } from "lucide-react";
import { toast } from "sonner";
import type { StyleItem, WritingProfileData, WritingProfileState } from "@/lib/proposals-types";
import { buildStyleProfile, deleteStyleSample, findStyleSamplesInSent, pasteStyleSample, resetStyleProfile, saveStyleNotes, saveStyleProfile, setLearned } from "@/lib/proposals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const card = "rounded-xl border border-border/80 bg-card p-4 shadow-2xs";
const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";
const SOURCE = { upload: "Uploaded", paste: "Pasted", sent: "From Sent Items" } as const;

function Step({ n, title, hint, children }: { n: number; title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className={card} aria-labelledby={`step-${n}`}>
      <h2 id={`step-${n}`} className="mb-3 flex items-center gap-2 text-sm font-bold">
        <span className="flex size-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">{n}</span>{title}
        {hint && <InfoHint>{hint}</InfoHint>}
      </h2>
      {children}
    </section>
  );
}

export function WritingProfile({ initial }: { initial: WritingProfileState }) {
  const [st, setSt] = useState(initial);
  const [prof, setProf] = useState<WritingProfileData>(initial.profile);
  const [notes, setNotes] = useState(initial.notes);
  const [paste, setPaste] = useState<{ name: string; text: string } | null>(null);
  const [sit, setSit] = useState<string>("general");
  const [busy, setBusy] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [pending, start] = useTransition();
  const fileRef = useRef<HTMLInputElement>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const apply = (next: WritingProfileState, keepEdits = false) => { setSt(next); if (!keepEdits) { setProf(next.profile); setDirty(false); } };
  const edit = (patch: Partial<WritingProfileData>) => { setProf({ ...prof, ...patch }); setDirty(true); };
  const run = (label: string, fn: () => Promise<void>) => start(async () => { setBusy(label); try { await fn(); } finally { setBusy(null); } });

  async function upload(files: FileList) {
    for (const f of Array.from(files)) {
      try {
        const res = await fetch(`/api/files/proposal-style/samples?name=${encodeURIComponent(f.name)}`, { method: "POST", headers: { "Content-Type": f.type || "application/octet-stream" }, body: f });
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail || "upload failed");
        apply(body, true);
      } catch (e) { toast.error(friendlyError(e, `Couldn't read ${f.name}`)); }
    }
  }

  async function speak() {
    if (rec.current) { rec.current.stop(); rec.current = null; return; }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") { toast.error("This browser can't record - type it instead."); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream);
      chunks.current = [];
      r.ondataavailable = (e) => chunks.current.push(e.data);
      r.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setBusy("transcribe");
        try {
          const blob = new Blob(chunks.current, { type: r.mimeType || "audio/webm" });
          const res = await fetch("/api/files/proposals/transcribe", { method: "POST", headers: { "Content-Type": blob.type }, body: blob });
          const body = await res.json();
          if (!res.ok) throw new Error(body.detail || "");
          setNotes((n) => (n ? `${n}\n${body.text}` : body.text));
        } catch (e) { toast.error(friendlyError(e, "Couldn't make out the recording - type it instead.")); }
        finally { setBusy(null); }
      };
      r.start();
      rec.current = r;
      setBusy("listen");
    } catch { toast.error("The microphone isn't available - type it instead."); }
  }

  const s = prof.situations[sit] ?? { include: [], opening: "", closing: "" };
  const setSitData = (patch: Partial<typeof s>) => edit({ situations: { ...prof.situations, [sit]: { ...s, ...patch } } });
  const order = [...s.include, ...(Object.keys(st.items) as StyleItem[]).filter((i) => !s.include.includes(i))];
  const move = (item: StyleItem, d: -1 | 1) => {
    const inc = [...s.include];
    const i = inc.indexOf(item);
    if (i < 0 || i + d < 0 || i + d >= inc.length) return;
    [inc[i], inc[i + d]] = [inc[i + d], inc[i]];
    setSitData({ include: inc });
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="flex min-w-0 flex-col gap-4">
        <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm ${st.status === "ready" ? "border-primary/30 bg-primary/5" : "border-border/80 bg-muted/30"}`}>
          {st.status === "ready" ? <CheckCircle2 className="size-4 text-primary" aria-hidden="true" /> : <Sparkles className="size-4 text-muted-foreground" aria-hidden="true" />}
          {st.status === "ready"
            ? <span>Your drafts are written in <strong>your own style</strong>{st.built_at ? `, set up ${fmtDate(st.built_at.slice(0, 10))}` : ""}. Change anything below and save.</span>
            : <span>Your drafts use <strong>the standard style</strong> for now. It takes about 10 minutes to teach the Brain how you write.</span>}
        </div>

        <Step n={1} title="Show it some of your past proposals" hint="Three to ten is plenty: a mix of quick replies and full proposals works best. Only the writing is used to learn your style - prices and figures in them are never copied into new drafts.">
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => fileRef.current?.click()}><FileUp className="size-3.5" /> Upload files</Button>
            <input ref={fileRef} type="file" multiple accept=".docx,.pdf,.txt,.eml,.htm,.html" className="hidden" onChange={(e) => { if (e.target.files) void upload(e.target.files); e.target.value = ""; }} />
            <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => setPaste({ name: "", text: "" })}>Paste one</Button>
            <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => run("sent", async () => {
              try { const r = await findStyleSamplesInSent(); apply(r, true); toast.success(r.found ? `Found ${r.found} in your Sent Items` : "Nothing that looked like a proposal - upload or paste a few instead"); }
              catch (e) { toast.error(friendlyError(e, "Couldn't look in your Sent Items")); }
            })}>{busy === "sent" ? <Loader2 className="size-3.5 animate-spin" /> : <Inbox className="size-3.5" />} Find them in my Sent Items</Button>
          </div>
          {paste && (
            <div className="mt-3 grid gap-2 rounded-lg border border-border/70 p-3">
              <Input value={paste.name} onChange={(e) => setPaste({ ...paste, name: e.target.value })} placeholder="What it was (e.g. Agency brief, Radisson)" className="h-8 text-sm" />
              <Textarea rows={6} value={paste.text} onChange={(e) => setPaste({ ...paste, text: e.target.value })} placeholder="Paste the email or proposal here" className="text-sm" />
              <div className="flex gap-2">
                <Button size="sm" disabled={pending || paste.text.trim().length < 80} onClick={() => run("paste", async () => {
                  try { apply(await pasteStyleSample(paste.name || "Pasted proposal", paste.text), true); setPaste(null); }
                  catch (e) { toast.error(friendlyError(e, "Couldn't add it")); }
                })}>Add it</Button>
                <Button size="sm" variant="ghost" onClick={() => setPaste(null)}>Cancel</Button>
              </div>
            </div>
          )}
          {st.samples.length > 0 ? (
            <ul className="mt-3 divide-y divide-border/60 rounded-lg border border-border/70">
              {st.samples.map((x) => (
                <li key={x.id} className="flex items-start gap-2 px-3 py-2 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{x.name} <span className="text-xs font-normal text-muted-foreground">· {SOURCE[x.source]} · {Math.round(x.chars / 100) / 10}k characters</span></p>
                    <p className="truncate text-xs text-muted-foreground">{x.preview}</p>
                  </div>
                  <Button size="icon-sm" variant="ghost" aria-label={`Remove ${x.name}`} disabled={pending} onClick={() => run("del", async () => { apply(await deleteStyleSample(x.id), true); })}><Trash2 className="size-3.5" /></Button>
                </li>
              ))}
            </ul>
          ) : <p className="mt-3 text-xs text-muted-foreground">None yet.</p>}
        </Step>

        <Step n={2} title="Tell it how you work (optional)" hint="Anything the examples don't show: who gets which prices, what you never do, how a first reply differs from a full proposal.">
          <Textarea rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} className="text-sm"
            placeholder="For example: agencies get the media pack rates, direct clients my introductory rates. I always add examples of past pages. I never send prices before a call for referrals." />
          <div className="mt-2 flex gap-2">
            <Button size="sm" variant="outline" className="gap-1.5" disabled={busy === "transcribe"} onClick={speak}>
              {busy === "listen" ? <><Square className="size-3.5" /> Stop</> : busy === "transcribe" ? <><Loader2 className="size-3.5 animate-spin" /> Writing it down…</> : <><Mic className="size-3.5" /> Speak it</>}
            </Button>
            <Button size="sm" variant="outline" disabled={pending || notes === st.notes} onClick={() => run("notes", async () => { apply(await saveStyleNotes(notes), true); toast.success("Saved"); })}>Save the note</Button>
          </div>
        </Step>

        <Step n={3} title="Let the Brain work out your style" hint="It reads your examples and note and fills in the profile below. Nothing changes in your drafts until you check it and press Use this profile.">
          <Button className="gap-1.5" disabled={pending || (!st.samples.length && !notes.trim())} onClick={() => run("build", async () => {
            try {
              if (notes !== st.notes) await saveStyleNotes(notes);
              const r = await buildStyleProfile();
              apply(r);
              setDirty(true);
              toast.success(r.built_by === "ai" ? "Done - check it below, then press Use this profile" : "The Brain isn't switched on, so the standard profile is filled in - change it below");
            } catch (e) { toast.error(friendlyError(e, "Couldn't work out your style")); }
          })}>{busy === "build" ? <Loader2 className="size-4 animate-spin" /> : <Wand2 className="size-4" />} Work out my style</Button>
          {!st.ai_on && <p className="mt-2 text-xs text-muted-foreground">The Brain isn&apos;t switched on for this account, so you&apos;ll fill the profile in yourself below - it works just the same.</p>}
        </Step>

        <section className={card} aria-labelledby="prof-h">
          <h2 id="prof-h" className="mb-3 text-sm font-bold">Your profile</h2>
          <div className="grid gap-3">
            <label className={labelCls}>In a few words, how you write<Textarea rows={2} value={prof.summary} onChange={(e) => edit({ summary: e.target.value })} className="text-sm font-normal" /></label>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className={labelCls}>Tone<Input value={prof.tone} onChange={(e) => edit({ tone: e.target.value })} className="h-8 text-sm" /></label>
              <label className={labelCls}>Length
                <select className="h-8 rounded-lg border border-input bg-background px-2 text-sm font-normal text-foreground" value={prof.length} onChange={(e) => edit({ length: e.target.value as WritingProfileData["length"] })}>
                  <option value="short">Short and to the point</option><option value="medium">Medium</option><option value="long">Long and detailed</option>
                </select></label>
              <label className={labelCls}>Usually sent
                <select className="h-8 rounded-lg border border-input bg-background px-2 text-sm font-normal text-foreground" value={prof.output} onChange={(e) => edit({ output: e.target.value as WritingProfileData["output"] })}>
                  <option value="email">As an email</option><option value="word">As a Word document</option>
                </select></label>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={labelCls}>Greeting <span className="font-normal">({"{first_name}"} is their name)</span><Input value={prof.greeting} onChange={(e) => edit({ greeting: e.target.value })} className="h-8 text-sm" /></label>
              <label className={labelCls}>Sign-off <span className="font-normal">({"{my_first_name}"} is yours)</span><Textarea rows={2} value={prof.sign_off} onChange={(e) => edit({ sign_off: e.target.value })} className="text-sm font-normal" /></label>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={labelCls}>
                <span className="flex items-center gap-1">Direct clients&apos; prices: % below the rate card <InfoHint>Agencies always get the rate card (they take their commission from it). Leave at 0 to quote the rate card to everyone.</InfoHint></span>
                <Input type="number" min={0} max={50} step={1} value={Math.round((prof.prices.direct_discount_pct || 0) * 100)}
                  onChange={(e) => edit({ prices: { ...prof.prices, direct_discount_pct: Math.min(50, Math.max(0, Number(e.target.value) || 0)) / 100 } })} className="h-8 w-28 text-sm" />
              </label>
              <label className={labelCls}>Round those prices to the nearest
                <select className="h-8 w-28 rounded-lg border border-input bg-background px-2 text-sm font-normal text-foreground" value={prof.prices.round_to} onChange={(e) => edit({ prices: { ...prof.prices, round_to: Number(e.target.value) } })}>
                  {[1, 10, 25, 50, 100].map((v) => <option key={v} value={v}>£{v}</option>)}
                </select></label>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={labelCls}>Things you always do (one per line)<Textarea rows={3} value={prof.always.join("\n")} onChange={(e) => edit({ always: e.target.value.split("\n") })} className="text-sm font-normal" /></label>
              <label className={labelCls}>Things you never do (one per line)<Textarea rows={3} value={prof.never.join("\n")} onChange={(e) => edit({ never: e.target.value.split("\n") })} className="text-sm font-normal" /></label>
            </div>

            <div className="rounded-lg border border-border/70 p-3">
              <p className="mb-2 flex items-center gap-1 text-xs font-semibold text-muted-foreground">What goes in each kind of proposal <InfoHint>Tick what you include and put it in your order. Prices, issues, numbers and examples always come from the Brain&apos;s own data.</InfoHint></p>
              <div role="tablist" aria-label="Kind of proposal" className="mb-3 flex flex-wrap gap-1">
                {Object.entries(st.situations).map(([k, label]) => (
                  <button key={k} type="button" role="tab" aria-selected={sit === k} onClick={() => setSit(k)}
                    className={`rounded-lg border px-2.5 py-1 text-xs font-medium ${sit === k ? "border-primary bg-primary/10" : "border-border text-muted-foreground hover:bg-accent/50"}`}>{label}</button>
                ))}
              </div>
              <ol className="grid gap-1">
                {order.map((item) => {
                  const on = s.include.includes(item);
                  return (
                    <li key={item} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={on} aria-label={st.items[item]} onChange={(e) => setSitData({ include: e.target.checked ? [...s.include, item] : s.include.filter((x) => x !== item) })} />
                      <span className={on ? "" : "text-muted-foreground"}>{st.items[item]}</span>
                      {on && <span className="ml-auto flex gap-0.5">
                        <Button size="icon-sm" variant="ghost" aria-label="Earlier" onClick={() => move(item, -1)}><ArrowUp className="size-3" /></Button>
                        <Button size="icon-sm" variant="ghost" aria-label="Later" onClick={() => move(item, 1)}><ArrowDown className="size-3" /></Button>
                      </span>}
                    </li>
                  );
                })}
              </ol>
              {sit !== "full_proposal" && (
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <label className={labelCls}>How you open <span className="font-normal">({"{for_client}"} names an agency&apos;s client)</span><Textarea rows={3} value={s.opening} onChange={(e) => setSitData({ opening: e.target.value })} className="text-sm font-normal" /></label>
                  <label className={labelCls}>How you close<Textarea rows={3} value={s.closing} onChange={(e) => setSitData({ closing: e.target.value })} className="text-sm font-normal" /></label>
                </div>
              )}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border/70 pt-3">
            <Button disabled={pending} onClick={() => run("save", async () => {
              try { apply(await saveStyleProfile({ ...prof, always: prof.always.filter((x) => x.trim()), never: prof.never.filter((x) => x.trim()) })); toast.success("Saved - your drafts now use it"); }
              catch (e) { toast.error(friendlyError(e, "Couldn't save the profile")); }
            })}>{busy === "save" && <Loader2 className="size-4 animate-spin" />} Use this profile</Button>
            {dirty && <span className="text-xs text-muted-foreground">Not saved yet</span>}
            {st.status === "ready" && (
              <Button variant="ghost" size="sm" className="ml-auto gap-1.5 text-muted-foreground" disabled={pending} onClick={() => {
                if (!window.confirm("Go back to the standard style? Your examples and note are kept, and you can work out your style again.")) return;
                run("reset", async () => { apply(await resetStyleProfile()); toast.success("Back to the standard style"); });
              }}><RotateCcw className="size-3.5" /> Back to the standard style</Button>
            )}
          </div>
        </section>
      </div>

      <aside className="flex flex-col gap-4">
        <section className={card} aria-labelledby="learned-h">
          <h2 id="learned-h" className="mb-2 flex items-center gap-1 text-sm font-bold">What the Brain has learned <InfoHint>Each time you send a drafted reply or proposal, it notes what you took out. Something you take out 3 times in your last 6 is left out from then on. Switch any of these off to undo it.</InfoHint></h2>
          {st.learned.length === 0
            ? <p className="text-xs text-muted-foreground">Nothing yet{st.edits ? ` - it has looked at ${st.edits} of your sent drafts so far` : ""}. It learns as you send drafted replies and proposals.</p>
            : (
              <ul className="flex flex-col gap-2">
                {st.learned.map((x) => (
                  <li key={x.key} className="flex items-start gap-2 text-sm">
                    <input type="checkbox" className="mt-1" checked={x.active} aria-label={x.text} disabled={pending}
                      onChange={(e) => run("learn", async () => { apply(await setLearned(x.key, e.target.checked), true); })} />
                    <span className={x.active ? "" : "text-muted-foreground line-through"}>{x.text}</span>
                  </li>
                ))}
              </ul>
            )}
        </section>
        <section className={`${card} text-xs text-muted-foreground`}>
          <p className="mb-1 font-semibold text-foreground">Where it&apos;s used</p>
          <ul className="list-disc space-y-1 pl-4">
            <li>Replies drafted for proposal requests in your Review Queue.</li>
            <li>New proposals: your blocks in your order, sent the way you usually send them, written in your tone.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
