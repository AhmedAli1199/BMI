import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, CheckCircle2, Clock, Loader2, Paperclip, XCircle } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { MailMergeDetail } from "@/lib/messaging-types";
import { Badge } from "@/components/ui/badge";
import { MergeProgressControls } from "@/components/mail-merge/merge-progress-controls";

const STATUS: Record<string, { label: string; cls: string }> = {
  queued: { label: "Starting", cls: "bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30" },
  sending: { label: "Sending", cls: "bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30" },
  done: { label: "Finished", cls: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30" },
  cancelled: { label: "Cancelled", cls: "bg-muted text-muted-foreground" },
  failed: { label: "Paused", cls: "bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/30" },
};

export default async function MailMergeProgressPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const m = await backendFetch<MailMergeDetail>(`/api/mail-merge/${id}`).catch(() => null);
  if (!m) notFound();

  const done = m.sent + m.failed + m.skipped;
  const pct = m.total ? Math.round((done / m.total) * 100) : 0;
  const s = STATUS[m.status] ?? STATUS.done;
  const noEmail = m.recipients.filter((r) => r.error === "no email address").length;
  const order = { failed: 0, queued: 1, sent: 2, skipped: 3 } as Record<string, number>;
  const recipients = [...m.recipients].sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9));

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-4 sm:p-6">
      <Link href="/mail-merge/history" className="flex w-fit items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-3.5" />
        Mail merges
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/80 pb-4">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2">
            <Badge variant="outline" className={s.cls}>
              {(m.status === "sending" || m.status === "queued") && <Loader2 className="mr-1 size-3 animate-spin" />}
              {s.label}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {m.output === "email" ? `From ${m.from_email}` : m.output}
              {m.source_label ? ` · ${m.source_label}` : ""}
            </span>
          </div>
          <h1 className="editorial-title truncate text-2xl font-bold tracking-tight">{m.subject || "(no subject)"}</h1>
          {m.error && <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">{m.error}</p>}
        </div>
        <MergeProgressControls id={m.id} status={m.status} failed={m.failed} noEmailCount={noEmail} />
      </div>

      <div className="flex flex-col gap-2">
        <div className="h-2.5 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Sent", v: m.sent, cls: "text-emerald-600" },
            { label: "Waiting", v: Math.max(0, m.total - done), cls: "text-sky-600" },
            { label: "Failed", v: m.failed, cls: "text-destructive" },
            { label: "Skipped", v: m.skipped, cls: "text-muted-foreground" },
          ].map((t) => (
            <div key={t.label} className="rounded-lg border border-border bg-card p-3 shadow-2xs">
              <div className={`text-2xl font-bold tabular-nums ${t.cls}`}>{t.v.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">{t.label}</div>
            </div>
          ))}
        </div>
        {(m.status === "queued" || m.status === "sending") && (
          <p className="text-xs text-muted-foreground">
            Sending in batches to stay within Outlook&apos;s limits. You can leave this page - it carries on, and
            you&apos;ll get a notification when it&apos;s finished.
          </p>
        )}
      </div>

      {m.attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {m.attachments.map((a) => (
            <span key={a.id} className="flex items-center gap-1 rounded border border-border px-2 py-0.5">
              <Paperclip className="size-3" />
              {a.filename}
            </span>
          ))}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-card shadow-2xs">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Contact</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {recipients.map((r, i) => (
              <tr key={`${r.contact_id}-${i}`} className="border-t border-border/60">
                <td className="px-3 py-2">
                  {r.contact_id ? (
                    <Link href={`/contacts/${r.contact_id}`} className="font-medium hover:text-primary">
                      {r.name || "(no name)"}
                    </Link>
                  ) : (
                    <span className="text-muted-foreground">Deleted contact</span>
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{r.email ?? "—"}</td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-1.5 text-xs">
                    {r.status === "sent" && <CheckCircle2 className="size-3.5 text-emerald-600" />}
                    {r.status === "failed" && <XCircle className="size-3.5 text-destructive" />}
                    {r.status === "queued" && <Clock className="size-3.5 text-sky-600" />}
                    <span className="capitalize">{r.status}</span>
                    {r.error && <span className="text-muted-foreground">· {r.error}</span>}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
