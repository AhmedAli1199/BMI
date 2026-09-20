"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, PlayCircle, RotateCcw } from "lucide-react";
import { toast } from "sonner";

function flatten(detail: unknown): string {
  // Defense in depth: the backend already caps how much detail it sends
  // back for a failure, but a toast is never the right place for a raw
  // stack trace or a multi-line SQL dump - cap and flatten to one line no
  // matter what actually comes back.
  const raw = typeof detail === "string" ? detail : "That failed - check the backend logs";
  return raw.replace(/\s+/g, " ").trim().slice(0, 300);
}

/** Fires a registered scan job immediately via POST
 * /api/automations/jobs/{id}/run, bypassing its cron schedule and its
 * enabled_flag - for testing a scan (e.g. the weekly dedupe pass) without
 * waiting for Sunday or hacking the cron string. Runs synchronously on
 * the backend, so this can take a few seconds for a real mailbox/DB scan.
 *
 * When the job has a cursor (hasCursor - it remembers "since last run" per
 * mailbox), also offers "Reset & rescan": clears that cursor first, so the
 * next run re-reads everything back to the job's own initial-lookback
 * window instead of only what's arrived since the last run - for pulling
 * in a bigger sample to judge a scan's real output against, without
 * waiting for enough new mail to trickle in naturally. */
export function RunJobButton({ jobId, hasCursor = false }: { jobId: string; hasCursor?: boolean }) {
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function run(resetFirst: boolean) {
    startTransition(async () => {
      try {
        if (resetFirst) {
          const resetRes = await fetch(`/api/automations/jobs/${jobId}/reset-cursor`, { method: "POST" });
          const resetResult = await resetRes.json().catch(() => ({}));
          if (!resetRes.ok) {
            toast.error(flatten(resetResult.detail));
            return;
          }
        }
        const res = await fetch(`/api/automations/jobs/${jobId}/run`, { method: "POST" });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          toast.error(flatten(result.detail));
          return;
        }
        toast.success(
          resetFirst
            ? `${jobId} rescanned from scratch - check what it found`
            : `${jobId} ran - check the review queue for what it found`
        );
        router.refresh();
      } catch {
        toast.error("Couldn't reach the backend - try again");
      }
    });
  }

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={() => run(false)}
        disabled={pending}
        className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] font-semibold text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-60"
      >
        {pending ? <Loader2 className="size-3 animate-spin" /> : <PlayCircle className="size-3" />}
        {pending ? "Running…" : "Run now"}
      </button>
      {hasCursor && (
        <button
          type="button"
          onClick={() => run(true)}
          disabled={pending}
          title="Clears this scan's remembered position first, so it re-reads everything back to its initial lookback window instead of only what's new since last time"
          className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] font-semibold text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-60"
        >
          <RotateCcw className="size-3" />
          Reset & rescan
        </button>
      )}
    </div>
  );
}
