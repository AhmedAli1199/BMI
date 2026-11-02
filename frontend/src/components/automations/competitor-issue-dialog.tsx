"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { FileSearch, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { friendlyError } from "@/lib/errors";

export type CompetitorOptions = { titles: { id: string; label: string }[]; competitors: string[]; max_mb: number };

/** SALES-006/007: upload a competitor's issue (PDF). The Brain reads it after the upload is answered, and the card
 * arrives in the Review Queue with a bell notification - see backend competitor_issues.py. */
export function CompetitorIssueDialog({ options }: { options: CompetitorOptions }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [titleId, setTitleId] = useState(options.titles[0]?.id ?? "");
  const [competitor, setCompetitor] = useState("");
  const [issue, setIssue] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const tooBig = !!file && file.size > options.max_mb * 1024 * 1024;

  function reset() {
    setFile(null);
    setIssue("");
    if (fileRef.current) fileRef.current.value = "";
  }

  function submit() {
    if (!file || !titleId || !competitor.trim() || tooBig) return;
    start(async () => {
      try {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("title_id", titleId);
        fd.append("competitor", competitor.trim());
        fd.append("issue", issue.trim());
        const res = await fetch("/api/automations/upload?kind=competitor-issue", { method: "POST", body: fd });
        const r = await res.json().catch(() => ({}));
        if (!res.ok || r.error) {
          toast.error(friendlyError(typeof r.detail === "string" ? r.detail : typeof r.error === "string" ? r.error : "", "Couldn't upload that issue"));
          return;
        }
        toast.success(r.message ?? "Reading it now. A card arrives in your Review Queue in a minute or two.");
        reset();
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("The upload didn't go through. Check your connection and try again.");
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <FileSearch className="size-4" />
        Read a competitor&apos;s issue
      </Button>
      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><FileSearch className="size-4 text-primary" /> Read a competitor&apos;s issue</DialogTitle>
            <DialogDescription>
              Upload the issue as a PDF. The Brain lists the companies advertising in it, checks who already advertises with us,
              and drafts an approach to the rest. The card arrives in your Review Queue in a minute or two. The PDF isn&apos;t kept.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ci-competitor">Competitor magazine</Label>
              <Input id="ci-competitor" list="ci-competitors" value={competitor} onChange={(e) => setCompetitor(e.target.value)} placeholder="e.g. Travel Weekly" />
              <datalist id="ci-competitors">{options.competitors.map((c) => <option key={c} value={c} />)}</datalist>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ci-issue">Which issue (optional)</Label>
              <Input id="ci-issue" value={issue} onChange={(e) => setIssue(e.target.value)} placeholder="e.g. 30 October 2026" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ci-title">Compare with</Label>
              <select id="ci-title" className="h-9 rounded-md border border-input bg-background px-2.5 text-sm" value={titleId} onChange={(e) => setTitleId(e.target.value)}>
                {options.titles.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ci-file">The issue (PDF, up to {options.max_mb} MB)</Label>
              <input ref={fileRef} id="ci-file" type="file" accept="application/pdf,.pdf"
                className="rounded-md border border-input bg-background px-2.5 py-1.5 text-sm file:mr-3 file:rounded file:border-0 file:bg-muted file:px-2 file:py-1 file:text-xs file:font-semibold"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              {tooBig && <span className="text-xs text-destructive">That file is over {options.max_mb} MB. Upload a smaller PDF of the issue.</span>}
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !file || !titleId || !competitor.trim() || tooBig}>
              {pending ? <Loader2 className="size-4 animate-spin" /> : <FileSearch className="size-4" />}
              {pending ? "Uploading…" : "Read it"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
