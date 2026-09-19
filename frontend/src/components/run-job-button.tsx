"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, PlayCircle } from "lucide-react";
import { toast } from "sonner";

/** Fires a registered scan job immediately via POST
 * /api/automations/jobs/{id}/run, bypassing its cron schedule and its
 * enabled_flag - for testing a scan (e.g. the weekly dedupe pass) without
 * waiting for Sunday or hacking the cron string. Runs synchronously on
 * the backend, so this can take a few seconds for a real mailbox/DB scan. */
export function RunJobButton({ jobId }: { jobId: string }) {
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function run() {
    startTransition(async () => {
      try {
        const res = await fetch(`/api/automations/jobs/${jobId}/run`, { method: "POST" });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          toast.error(result.detail ?? "That job failed - check the backend logs");
          return;
        }
        toast.success(`${jobId} ran - check the review queue for what it found`);
        router.refresh();
      } catch {
        toast.error("Couldn't reach the backend - try again");
      }
    });
  }

  return (
    <button
      type="button"
      onClick={run}
      disabled={pending}
      className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] font-semibold text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-60"
    >
      {pending ? <Loader2 className="size-3 animate-spin" /> : <PlayCircle className="size-3" />}
      {pending ? "Running…" : "Run now"}
    </button>
  );
}
