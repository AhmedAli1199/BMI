"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, Sparkles, Square, Undo2 } from "lucide-react";
import { toast } from "sonner";
import type { ProposalSection } from "@/lib/proposals-types";
import { reviseProposal, saveProposal } from "@/lib/proposals-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const EXAMPLES = ["Make it shorter and friendlier", "Add a section about the Onboard Awards", "Rename the headings to sound less formal", "Lead with the sustainability feature"];

/** "Tell the AI what to change": typed or spoken, applied to the whole proposal (headings, text, sections), with Undo. */
export function ProposalAiRevise({ proposalId, sections, onApplied, onBeforeApply }: {
  proposalId: string;
  sections: ProposalSection[];
  onApplied: (sections: ProposalSection[]) => void;
  onBeforeApply?: () => Promise<void>;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<"revise" | "listen" | "transcribe" | null>(null);
  const [last, setLast] = useState<{ summary: string; previous: ProposalSection[] } | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stopTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { rec.current?.stream.getTracks().forEach((t) => t.stop()); if (stopTimer.current) clearTimeout(stopTimer.current); }, []);

  async function apply() {
    const instruction = text.trim();
    if (instruction.length < 3) return toast.error("Say what you'd like changed first");
    setBusy("revise");
    try {
      await onBeforeApply?.();
      const r = await reviseProposal(proposalId, instruction, sections);
      onApplied(r.proposal.sections);
      setLast({ summary: r.summary, previous: r.previous_sections });
      setText("");
      toast.success(r.summary);
    } catch (e) {
      toast.error(friendlyError(e, "Couldn't change the proposal. Try again, or say it a different way."));
    } finally {
      setBusy(null);
    }
  }

  async function undo() {
    if (!last) return;
    setBusy("revise");
    try {
      const p = await saveProposal(proposalId, { sections: last.previous });
      onApplied(p.sections);
      setLast(null);
      toast.success("Back to how it was");
    } catch (e) {
      toast.error(friendlyError(e, "Couldn't undo"));
    } finally {
      setBusy(null);
    }
  }

  async function startListening() {
    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      return toast.error("This browser can't record sound. Type the change instead.");
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      return toast.error("We need permission to use your microphone. Allow it in the browser, then try again.");
    }
    const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"].find((t) => MediaRecorder.isTypeSupported?.(t)) ?? "";
    const r = type ? new MediaRecorder(stream, { mimeType: type }) : new MediaRecorder(stream);
    chunks.current = [];
    r.ondataavailable = (ev) => { if (ev.data.size) chunks.current.push(ev.data); };
    r.onstop = () => { stream.getTracks().forEach((t) => t.stop()); void transcribe(new Blob(chunks.current, { type: r.mimeType || "audio/webm" })); };
    rec.current = r;
    r.start();
    setBusy("listen");
    stopTimer.current = setTimeout(() => stopListening(), 120_000); // two minutes at most
  }

  function stopListening() {
    if (stopTimer.current) clearTimeout(stopTimer.current);
    if (rec.current && rec.current.state !== "inactive") rec.current.stop();
  }

  async function transcribe(blob: Blob) {
    if (blob.size < 1000) { setBusy(null); return toast.error("We didn't catch that. Hold the button a little longer while you speak."); }
    setBusy("transcribe");
    try {
      const res = await fetch("/api/files/proposals/transcribe", { method: "POST", headers: { "Content-Type": blob.type || "audio/webm" }, body: blob });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.text) throw new Error(typeof data?.detail === "string" ? data.detail : "");
      setText((t) => (t.trim() ? `${t.trim()} ${data.text}` : data.text));
    } catch (e) {
      toast.error(friendlyError(e, "We couldn't make out the recording. Try again, or type the change instead."));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section aria-labelledby="ai-h" className="print-hide rounded-xl border border-primary/30 bg-primary/5 p-3">
      <h3 id="ai-h" className="flex items-center gap-1.5 text-sm font-bold"><Sparkles className="size-4 text-primary" aria-hidden="true" /> Change it with AI</h3>
      <p className="mt-0.5 text-xs text-muted-foreground">Say or type what you&apos;d like different: headings, tone, length, new or removed sections. Prices and figures still only come from the rate card and booking history.</p>
      <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} disabled={busy === "revise"}
        placeholder="e.g. Make the introduction warmer and shorter, add a section about the Awards, and end with a clear call to book by the deadline"
        className="mt-2 bg-background text-sm" aria-label="What to change"
        onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void apply(); }} />
      <div className="mt-1.5 flex flex-wrap gap-1">
        {EXAMPLES.map((x) => (
          <button key={x} type="button" className="rounded-full border border-border/80 bg-background px-2 py-0.5 text-[11px] text-muted-foreground hover:text-foreground" onClick={() => setText(x)}>{x}</button>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {busy === "listen" ? (
          <Button type="button" size="sm" variant="outline" className="gap-1.5" onClick={stopListening} style={{ borderColor: "var(--bad)", color: "var(--bad)" }}>
            <Square className="size-3.5" /> Stop recording
          </Button>
        ) : (
          <Button type="button" size="sm" variant="outline" className="gap-1.5" disabled={busy !== null} onClick={startListening}>
            {busy === "transcribe" ? <Loader2 className="size-3.5 animate-spin" /> : <Mic className="size-3.5" />} {busy === "transcribe" ? "Writing it down…" : "Speak"}
          </Button>
        )}
        {busy === "listen" && <span className="text-xs" style={{ color: "var(--bad)" }}>Listening… press Stop when you&apos;ve finished.</span>}
        <Button type="button" size="sm" className="ml-auto gap-1.5" disabled={busy !== null || text.trim().length < 3} onClick={apply}>
          {busy === "revise" ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />} {busy === "revise" ? "Changing…" : "Apply"}
        </Button>
      </div>
      {last && (
        <div className="mt-2 flex items-center gap-2 rounded-lg border border-border/70 bg-background px-2.5 py-1.5 text-xs">
          <span className="min-w-0 flex-1 text-muted-foreground">{last.summary}</span>
          <Button type="button" size="xs" variant="ghost" className="gap-1" disabled={busy !== null} onClick={undo}><Undo2 className="size-3" /> Undo</Button>
        </div>
      )}
    </section>
  );
}
