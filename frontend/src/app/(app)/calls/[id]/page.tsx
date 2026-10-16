import { notFound } from "next/navigation";
import { ExternalLink } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { LIVE_STATUSES, PLATFORM_LABEL, type Call } from "@/lib/calls-types";
import { CallStatus } from "@/components/calls/call-status";
import { AutoRefresh } from "@/components/calls/auto-refresh";
import { CallActions } from "@/components/calls/call-actions";
import { PageHeader } from "@/components/page-header";

function clock(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function List({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <h3 className="mb-1 text-xs font-bold uppercase tracking-wider text-muted-foreground">{title}</h3>
      <ul className="list-disc space-y-0.5 pl-5 text-sm">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}

const INTEREST: Record<string, string> = { positive: "Interested", neutral: "Neutral", negative: "Not keen" };

export default async function CallPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = await backendFetch<Call>(`/api/calls/${id}`).catch(() => null);
  if (!c) notFound();
  const n = c.notes;
  const live = LIVE_STATUSES.includes(c.status);
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      {live && <AutoRefresh seconds={5} />}
      <PageHeader
        title={c.title || n?.title || "Call"}
        crumbs={[{ label: "Call notes", href: "/calls" }]}
        below={
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <CallStatus status={c.status} label={c.status_label} />
            {c.status_detail && <span>{c.status_detail}</span>}
            <span>· {PLATFORM_LABEL[c.platform ?? ""] ?? "Call"}</span>
            <a href={c.meeting_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 hover:underline">meeting link <ExternalLink className="size-3" /></a>
            {c.participants.length > 0 && <span>· {c.participants.join(", ")}</span>}
          </div>
        }
        actions={<CallActions call={c} />}
      />

      {live && (
        <p className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
          {c.status === "waiting_room" ? "The notetaker is waiting to be let in - accept it in the meeting." :
           c.status === "processing" ? "The call has ended. The notes are being written up - this usually takes under a minute." :
           c.status === "recording" ? "The notetaker is in the call and recording. The notes appear here when the call ends." :
           "The notetaker is on its way into the call."}
        </p>
      )}

      {n && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <section aria-labelledby="sum-h" className="flex flex-col gap-4 rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
            <div>
              <h2 id="sum-h" className="mb-1 text-sm font-bold">Summary</h2>
              <p className="text-sm leading-relaxed">{n.summary}</p>
            </div>
            {n.next_step && <p className="rounded-lg border px-3 py-2 text-sm" style={{ borderColor: "color-mix(in oklab, var(--primary) 30%, transparent)" }}><span className="font-semibold">Next step:</span> {n.next_step}</p>}
            <List title="Key points" items={n.key_points} />
            <List title="Decisions" items={n.decisions} />
            <List title="Money mentioned" items={n.money_mentioned} />
            <List title="Dates mentioned" items={n.dates_mentioned} />
          </section>
          <section aria-labelledby="todo-h" className="flex flex-col gap-3 self-start rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
            <h2 id="todo-h" className="text-sm font-bold">Who&apos;s doing what</h2>
            {n.action_items.length ? (
              <ul className="space-y-2 text-sm">
                {n.action_items.map((a, i) => (
                  <li key={i} className="rounded-lg border border-border/70 px-3 py-2">
                    <div className="font-medium">{a.task}</div>
                    <div className="text-[11px] text-muted-foreground">{[a.owner, a.due].filter(Boolean).join(" · ") || "No one named"}</div>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-muted-foreground">Nothing was agreed.</p>}
            <p className="text-xs text-muted-foreground">Their interest: <span className="font-semibold text-foreground">{INTEREST[n.sentiment] ?? "Neutral"}</span></p>
          </section>
        </div>
      )}

      {c.transcript && c.transcript.length > 0 && (
        <section aria-labelledby="tr-h" className="rounded-xl border border-border/80 bg-card shadow-2xs">
          <h2 id="tr-h" className="border-b border-border/70 px-5 py-3 text-sm font-bold">Transcript</h2>
          <ol className="max-h-[32rem] space-y-2 overflow-y-auto px-5 py-4 text-sm">
            {c.transcript.map((u, i) => (
              <li key={i} className="grid grid-cols-[3.5rem_1fr] gap-2">
                <span className="text-[11px] tabular-nums text-muted-foreground">{clock(u.start_ms)}</span>
                <span><span className="font-semibold text-primary">{u.speaker}:</span> {u.text}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
