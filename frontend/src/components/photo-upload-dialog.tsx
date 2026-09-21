"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Camera, ImagePlus, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { SOURCE_LABELS } from "@/lib/sources";
import { confirmBusinessCardBatch } from "@/lib/actions";

type Kind = "business-card" | "returned-copy";

const COPY: Record<
  Kind,
  { title: string; description: string; icon: typeof Camera; resultLabel: (r: Record<string, unknown>) => string }
> = {
  "business-card": {
    title: "Upload business card(s)",
    description: "One photo can hold several cards - each one becomes its own review item.",
    icon: Camera,
    resultLabel: (r) => {
      const cardsFound = Number(r.cards_found ?? 0);
      return cardsFound === 0
        ? "No readable cards found in that photo."
        : `Found ${cardsFound} card${cardsFound === 1 ? "" : "s"} - ${r.queued} queued for review.`;
    },
  },
  "returned-copy": {
    title: "Upload returned copy label",
    description: "A photo of the undeliverable-mail label the post office sent back.",
    icon: ImagePlus,
    resultLabel: (r) =>
      r.matched ? "Matched to an existing record - queued for review." : "No match found - queued for review anyway.",
  },
};

/** Shared upload entry point for the two photo-triggered automations
 * (SALES-001/002 business cards, CS-005 returned copies) - same shape
 * (pick a publication, optionally add context, pick a file, POST it) with
 * just the copy and extra field differing by kind. */
export function PhotoUploadDialog({ kind, publications }: { kind: Kind; publications: string[] }) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [sourceDb, setSourceDb] = useState(publications[0] ?? "");
  const [showContext, setShowContext] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const copy = COPY[kind];
  const Icon = copy.icon;

  function reset() {
    setFile(null);
    setShowContext("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function submit() {
    if (!file || !sourceDb) return;
    startTransition(async () => {
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("source_db", sourceDb);
        if (kind === "business-card" && showContext.trim()) {
          formData.append("show_context", showContext.trim());
        }
        const res = await fetch(`/api/automations/upload?kind=${kind}`, { method: "POST", body: formData });
        const result = await res.json();
        if (!res.ok || result.error) {
          toast.error(result.error ?? "Couldn't process that photo - try again");
          return;
        }
        const queued = Number(result.queued ?? 0);
        const skippedDuplicates = Number(result.skipped_duplicates ?? 0);
        toast.success(
          copy.resultLabel(result) + (skippedDuplicates > 0 ? ` (${skippedDuplicates} within-batch duplicate${skippedDuplicates === 1 ? "" : "s"} merged)` : ""),
          kind === "business-card" && queued > 0 && result.batch_id
            ? {
                action: {
                  label: "Confirm all now",
                  onClick: () => {
                    confirmBusinessCardBatch(result.batch_id as string)
                      .then((r) => {
                        toast.success(`Batch confirmed: ${r.added} added, ${r.updated} updated, ${r.logged} logged, ${r.failed} failed`);
                        router.refresh();
                      })
                      .catch((e) => toast.error(e instanceof Error ? e.message : "Couldn't confirm that batch"));
                  },
                },
              }
            : undefined
        );
        reset();
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Upload failed - check your connection and try again");
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Icon className="size-4" />
        {copy.title}
      </Button>
      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Icon className="size-4 text-primary" />
              {copy.title}
            </DialogTitle>
            <DialogDescription>{copy.description}</DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Publication</Label>
              <select
                className="h-9 rounded-md border border-input bg-background px-2.5 text-sm"
                value={sourceDb}
                onChange={(e) => setSourceDb(e.target.value)}
              >
                {publications.map((p) => (
                  <option key={p} value={p}>{SOURCE_LABELS[p] ?? p}</option>
                ))}
              </select>
            </div>

            {kind === "business-card" && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="pu-show">Show / event (optional)</Label>
                <Input
                  id="pu-show"
                  value={showContext}
                  onChange={(e) => setShowContext(e.target.value)}
                  placeholder="e.g. WTM London 2026"
                />
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pu-file">Photo</Label>
              <input
                ref={fileInputRef}
                id="pu-file"
                type="file"
                accept="image/*"
                capture="environment"
                className="rounded-md border border-input bg-background px-2.5 py-1.5 text-sm file:mr-3 file:rounded file:border-0 file:bg-muted file:px-2 file:py-1 file:text-xs file:font-semibold"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>

          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !file || !sourceDb}>
              {pending ? <Loader2 className="size-4 animate-spin" /> : <Icon className="size-4" />}
              {pending ? "Processing…" : "Upload"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
