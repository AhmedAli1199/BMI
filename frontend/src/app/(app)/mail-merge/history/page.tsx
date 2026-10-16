import Link from "next/link";
import { FileText, Mail, Plus } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { MailMergeSummary } from "@/lib/messaging-types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";

const LABEL: Record<string, string> = {
  queued: "Starting",
  sending: "Sending",
  done: "Finished",
  cancelled: "Cancelled",
  failed: "Paused",
};

export default async function MailMergeHistoryPage() {
  const merges = await backendFetch<MailMergeSummary[]>("/api/mail-merge").catch(() => [] as MailMergeSummary[]);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-4 sm:p-6">
      <PageHeader
        title="Sent mail merges"
        crumbs={[{ label: "Mail merge", href: "/mail-merge" }]}
        description="Emails you've sent and letters you've logged, newest first."
        actions={
          <Button size="sm" nativeButton={false} render={<Link href="/mail-merge" />}>
            <Plus className="size-3.5" />
            New mail merge
          </Button>
        }
      />

      {merges.length === 0 ? (
        <EmptyState title="No mail merges yet">Press <strong>New mail merge</strong> to send your first one.</EmptyState>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border bg-card shadow-2xs">
          {merges.map((m) => {
            const Icon = m.output === "email" ? Mail : FileText;
            return (
              <li key={m.id}>
                <Link href={`/mail-merge/${m.id}`} className="flex flex-wrap items-center gap-3 px-4 py-3 hover:bg-accent/40">
                  <Icon className="size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{m.subject || "(no subject)"}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {m.source_label ?? ""}
                      {m.created_at ? ` · ${new Date(m.created_at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}` : ""}
                    </div>
                  </div>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {m.output === "email" ? `${m.sent}/${m.total - m.skipped} sent` : `${m.total} letters`}
                  </span>
                  <Badge variant="outline" className="text-[11px]">{LABEL[m.status] ?? m.status}</Badge>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
