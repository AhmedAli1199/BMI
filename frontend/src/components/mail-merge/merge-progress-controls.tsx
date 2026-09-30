"use client";

import { useEffect, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Ban, FileText, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { cancelMerge, resumeMerge } from "@/lib/messaging-actions";
import { downloadFile } from "@/lib/download";

/** Live-refreshes the progress page while a merge is sending, plus its
 * Cancel / Resume / "letters for the rest" buttons. */
export function MergeProgressControls({
  id,
  status,
  failed,
  noEmailCount,
}: {
  id: string;
  status: string;
  failed: number;
  noEmailCount: number;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const live = status === "queued" || status === "sending";

  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => router.refresh(), 5000);
    return () => clearInterval(t);
  }, [live, router]);

  function act(fn: () => Promise<unknown>, ok: string) {
    start(async () => {
      try {
        await fn();
        toast.success(ok);
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "That didn't work");
      }
    });
  }

  return (
    <div className="flex flex-wrap gap-2">
      {live && (
        <Button variant="outline" size="sm" disabled={pending} onClick={() => act(() => cancelMerge(id), "Cancelled - nothing more will be sent")}>
          <Ban className="size-3.5" />
          Cancel the rest
        </Button>
      )}
      {(status === "failed" || (status === "done" && failed > 0)) && (
        <Button size="sm" disabled={pending} onClick={() => act(() => resumeMerge(id), "Resumed")}>
          <RotateCcw className="size-3.5" />
          {status === "failed" ? "Resume sending" : `Retry ${failed} failed`}
        </Button>
      )}
      {noEmailCount > 0 && (
        <Button
          variant="outline"
          size="sm"
          disabled={pending}
          onClick={() =>
            start(async () => {
              try {
                await downloadFile(`/api/files/mail-merge/${id}/letters`, "letters-no-email.docx", { method: "POST" });
              } catch (e) {
                toast.error(e instanceof Error ? e.message : "Couldn't make the letters");
              }
            })
          }
        >
          <FileText className="size-3.5" />
          Letters for the {noEmailCount} without email
        </Button>
      )}
    </div>
  );
}
