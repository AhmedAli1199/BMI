import Link from "next/link";
import { Mic } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { LIVE_STATUSES, PLATFORM_LABEL, type Call } from "@/lib/calls-types";
import { SendNotetaker } from "@/components/calls/send-notetaker";
import { CallStatus } from "@/components/calls/call-status";
import { AutoRefresh } from "@/components/calls/auto-refresh";
import { CallsTabs } from "@/components/calls/calls-tabs";
import { EmptyState } from "@/components/empty-state";

function fmt(iso: string) {
  return new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Calls the notetaker joined, newest first. */
export default async function CallsPage() {
  const [calls, status] = await Promise.all([
    backendFetch<Call[]>("/api/calls").catch(() => [] as Call[]),
    backendFetch<{ available: boolean }>("/api/calls/status").catch(() => ({ available: false })),
  ]);
  const live = calls.some((c) => LIVE_STATUSES.includes(c.status));
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      {live && <AutoRefresh seconds={6} />}
      <div>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary"><Mic className="size-3.5" /><span>Calls</span></div>
        <h1 className="editorial-title text-2xl font-bold tracking-tight sm:text-3xl">Call notes</h1>
        <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
          Send the notetaker into a Google Meet or Teams call. When the call ends, the summary, what was agreed and who&apos;s doing what
          appear here and in your review queue, ready to save onto the contact.
        </p>
      </div>
      <CallsTabs active="calls" />
      {status.available ? (
        <SendNotetaker />
      ) : (
        <p className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">The notetaker isn&apos;t connected yet. An administrator can connect it in the server settings.</p>
      )}
      <section aria-labelledby="calls-h" className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <h2 id="calls-h" className="border-b border-border/70 px-4 py-3 text-sm font-bold">Recent calls</h2>
        {calls.length === 0 ? (
          <EmptyState compact title="No calls yet">Paste a meeting link above to send the notetaker.</EmptyState>
        ) : (
          <table className="w-full min-w-[40rem] text-sm">
            <thead>
              <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                <th scope="col" className="px-4 py-2">Call</th><th scope="col" className="px-3 py-2">With</th>
                <th scope="col" className="px-3 py-2">Status</th><th scope="col" className="px-4 py-2 text-right">When</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id} className="border-b border-border/60 last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-2.5">
                    <Link href={`/calls/${c.id}`} className="font-medium text-foreground hover:text-primary hover:underline">{c.title || "Untitled call"}</Link>
                    <div className="line-clamp-1 text-[11px] text-muted-foreground">{c.summary || PLATFORM_LABEL[c.platform ?? ""] || c.meeting_url}</div>
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    {c.contact ? <Link href={`/contacts/${c.contact.id}`} target="_blank" rel="noreferrer" className="hover:underline">{c.contact.name}</Link> : <span className="text-muted-foreground">—</span>}
                    {c.company && <div className="text-[11px] text-muted-foreground">{c.company.name}</div>}
                  </td>
                  <td className="px-3 py-2.5"><CallStatus status={c.status} label={c.status_label} /></td>
                  <td className="px-4 py-2.5 text-right text-xs text-muted-foreground tabular-nums">{fmt(c.created_at)}{c.owner ? <div>{c.owner}</div> : null}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
