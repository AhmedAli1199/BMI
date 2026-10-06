"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Download, FileSpreadsheet, Loader2, ShieldCheck, Sparkles, Undo2, UploadCloud } from "lucide-react";
import { toast } from "sonner";

const ACCEPT = ".xlsx,.xls,.csv,.pdf";

/** Step 1: drop a file. The browser sends it through our file bridge (the API key never reaches the browser),
 * then we open the matching screen for it. */
export function ImportUpload() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const [name, setName] = useState<string | null>(null);

  async function send(file: File) {
    setBusy(true);
    setName(file.name);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/files/contact-imports", { method: "POST", body: form });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "We couldn't read that file.");
      router.push(`/contacts/import/${body.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "We couldn't read that file.");
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files?.[0]; if (f && !busy) send(f); }}
        className={`flex min-h-64 flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${over ? "border-primary bg-primary/5" : "border-border/80 bg-card"}`}
      >
        {busy ? (
          <>
            <Loader2 className="size-8 animate-spin text-primary" aria-hidden="true" />
            <p className="text-sm font-semibold" role="status">Reading {name}…</p>
            <p className="text-xs text-muted-foreground">Matching the columns - this takes a few seconds for big files.</p>
          </>
        ) : (
          <>
            <UploadCloud className="size-9 text-muted-foreground" aria-hidden="true" />
            <p className="text-base font-semibold">Drop your file here</p>
            <p className="text-xs text-muted-foreground">Excel (.xlsx, .xls), CSV or PDF, up to 15&nbsp;MB and 20,000 rows</p>
            <button type="button" onClick={() => input.current?.click()} className="mt-1 inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
              <FileSpreadsheet className="size-4" /> Choose a file
            </button>
            <input ref={input} type="file" accept={ACCEPT} className="sr-only" aria-label="Choose a contacts file" onChange={(e) => { const f = e.target.files?.[0]; if (f) send(f); e.target.value = ""; }} />
            <a href="/api/files/contact-imports/template.xlsx" download className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline">
              <Download className="size-3.5" /> Download an example sheet
            </a>
          </>
        )}
      </div>

      <aside className="flex flex-col gap-3 rounded-xl border border-border/80 bg-card p-4 text-sm shadow-2xs" aria-label="How importing works">
        <h2 className="text-sm font-bold">What happens next</h2>
        <ul className="flex flex-col gap-3 text-xs text-muted-foreground">
          <li className="flex gap-2"><Sparkles className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" /><span><strong className="text-foreground">Columns are matched for you.</strong> “First Name”, “Forename”, “Mobile”, “Post code”… we recognise the usual headings and the data itself. You can change any of them.</span></li>
          <li className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" /><span><strong className="text-foreground">You see every row first.</strong> Bad emails, missing names and people already in the CRM are flagged before anything is saved.</span></li>
          <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" /><span><strong className="text-foreground">Nothing is overwritten</strong> unless you choose that - by default we only fill in what&apos;s missing.</span></li>
          <li className="flex gap-2"><Undo2 className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" /><span><strong className="text-foreground">You can undo it</strong> afterwards if it wasn&apos;t what you wanted.</span></li>
        </ul>
      </aside>
    </div>
  );
}
