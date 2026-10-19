"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, PlayCircle, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { friendlyError } from "@/lib/errors";

/** The API's error detail is a plain sentence for people; friendlyError still swaps in the fallback
 * if anything technical ever slips through. */
function problem(detail: unknown, fallback: string): string {
  return friendlyError(typeof detail === "string" ? detail : "", fallback);
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
export function RunJobButton({ jobId, label, hasCursor = false }: { jobId: string; label?: string; hasCursor?: boolean }) {
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function run(resetFirst: boolean) {
    startTransition(async () => {
      try {
        if (resetFirst) {
          const resetRes = await fetch(`/api/automations/jobs/${jobId}/reset-cursor`, { method: "POST" });
          const resetResult = await resetRes.json().catch(() => ({}));
          if (!resetRes.ok) {
            toast.error(problem(resetResult.detail, "We couldn't reset this job's place - try again."));
            return;
          }
        }
        const res = await fetch(`/api/automations/jobs/${jobId}/run`, { method: "POST" });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          toast.error(problem(result.detail, "This job stopped with a problem - try again later."));
          return;
        }
        const name: string = (typeof result.label === "string" && result.label) || label || "The job";
        if (result.skipped) {
          toast.info(`${name} is already running, so we didn't start it again. Check back in a minute.`);
        } else {
          toast.success(
            resetFirst
              ? `${name} read everything again from the start - check what it found`
              : `${name} has finished - check the review queue for what it found`
          );
        }
        router.refresh();
      } catch {
        toast.error("We couldn't reach BMI Brain - check your connection and try again.");
      }
    });
  }

  return (
    <div className="flex items-center gap-1.5">
      <Button type="button" size="sm" variant="outline" onClick={() => run(false)} disabled={pending}>
        {pending ? <Loader2 className="size-3 animate-spin" /> : <PlayCircle className="size-3" />}
        {pending ? "Running…" : "Run now"}
      </Button>
      {hasCursor && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => run(true)}
          disabled={pending}
          title="Clears this scan's remembered position first, so it re-reads everything back to its initial lookback window instead of only what's new since last time"
        >
          <RotateCcw className="size-3" />
          Reset & rescan
        </Button>
      )}
    </div>
  );
}
