import Link from "next/link";
import { notFound } from "next/navigation";
import { CheckCircle2, Clock, Loader2, Paperclip, XCircle } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { friendlyError } from "@/lib/errors";
import type { MailMergeDetail } from "@/lib/messaging-types";
import { Badge } from "@/components/ui/badge";
import { MergeProgressControls } from "@/components/mail-merge/merge-progress-controls";
import { PageHeader } from "@/components/page-header";

const STATUS: Record<string, { label: string; cls: string }> = {
  queued: { label: "Starting", cls: "border-primary/30 bg-primary/10 text-primary" },
  sending: { label: "Sending", cls: "border-primary/30 bg-primary/10 text-primary" },
  done: { label: "Finished", cls: "border-[var(--ok)]/30 bg-[var(--ok-tint)] text-[var(--ok)]" },
  cancelled: { label: "Cancelled", cls: "bg-muted text-muted-foreground" },
  failed: { label: "Paused", cls: "border-[var(--warn)]/30 bg-[var(--warn-tint)] text-[var(--warn)]" },
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
      <PageHeader
        title={m.subject || "(no subject)"}
        crumbs={[{ label: "Mail merge", href: "/mail-merge" }, { label: "Sent mail merges", href: "/mail-merge/history" }]}
        below={<>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={s.cls}>
              {(m.status === "sending" || m.status === "queued") && <Loader2 className="mr-1 size-3 animate-spin" />}
              {s.label}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {m.output === "email" ? `From ${m.from_email}` : m.output}
              {m.source_label ? ` · ${m.source_label}` : ""}
            </span>
          </div>
          {m.error && (
            <p className="mt-1 text-sm" style={{ color: "var(--warn)" }}>
              {friendlyError(m.error, "This mail merge stopped with a problem. Check your Outlook connection in Settings, then resume.")}
            </p>
          )}
        </>}
        actions={<MergeProgressControls id={m.id} status={m.status} failed={m.failed} noEmailCount={noEmail}
          unsent={Math.max(0, m.total - m.sent - m.failed - m.skipped)} />}
      />

      <div className="flex flex-col gap-2">
        <div className="h-2.5 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Sent", v: m.sent, cls: "text-[var(--ok)]" },
            { label: "Waiting", v: Math.max(0, m.total - done), cls: "text-primary" },
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
                    {r.status === "sent" && <CheckCircle2 className="size-3.5 text-[var(--ok)]" />}
                    {r.status === "failed" && <XCircle className="size-3.5 text-destructive" />}
                    {r.status === "queued" && <Clock className="size-3.5 text-primary" />}
                    <span className="capitalize">{r.status}</span>
                    {r.error && <span className="text-muted-foreground">· {friendlyError(r.error, "Outlook couldn't send this one.")}</span>}
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
