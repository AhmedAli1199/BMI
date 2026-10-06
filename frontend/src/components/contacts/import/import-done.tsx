"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { CheckCircle2, Download, Undo2, Upload, Users } from "lucide-react";
import { toast } from "sonner";
import type { ContactImport } from "@/lib/contact-tools-types";
import { getImport, undoImport } from "@/lib/contact-tools-actions";
import { Button } from "@/components/ui/button";

/** Step 4: what happened, with a way back. */
export function ImportDone({ imp, onChange }: { imp: ContactImport; onChange: (i: ContactImport) => void }) {
  const [pending, start] = useTransition();
  const [undone, setUndone] = useState<string | null>(null);
  const r = imp.result ?? {};
  const undid = imp.status === "undone";

  function undo() {
    if (!window.confirm("Undo this import? The contacts it added are removed (any you've since worked on are kept) and updated ones go back to how they were.")) return;
    start(async () => {
      try {
        const u = await undoImport(imp.id);
        setUndone(`Removed ${u.deleted} contact${u.deleted === 1 ? "" : "s"}${u.reverted ? `, put ${u.reverted} back as they were` : ""}${u.kept ? `, kept ${u.kept} you've worked on since` : ""}.`);
        onChange(await getImport(imp.id));
      } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't undo the import"); }
    });
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-5 py-6 text-center">
      <div className={`flex size-14 items-center justify-center rounded-full ${undid ? "bg-muted text-muted-foreground" : "bg-primary/10 text-primary"}`}>
        {undid ? <Undo2 className="size-7" aria-hidden="true" /> : <CheckCircle2 className="size-7" aria-hidden="true" />}
      </div>
      <div>
        <h2 className="text-xl font-bold">{undid ? "This import was undone" : "Import complete"}</h2>
        <p className="mt-1 text-sm text-muted-foreground" role="status">{undone ?? (undid ? "Nothing from this file is in the CRM now." : `Your file “${imp.filename}” has been added to the CRM.`)}</p>
      </div>
      {!undid && (
        <div className="grid w-full grid-cols-2 gap-2 sm:grid-cols-4">
          {[["Added", r.created ?? 0], ["Updated", r.updated ?? 0], ["Left out", r.skipped ?? 0], ["Already complete", r.unchanged ?? 0]].map(([l, n]) => (
            <div key={l as string} className="rounded-xl border border-border/80 bg-card p-3"><p className="text-2xl font-bold tabular-nums">{(n as number).toLocaleString()}</p><p className="text-[11px] font-medium text-muted-foreground">{l}</p></div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center justify-center gap-2">
        {!undid && <Button nativeButton={false} render={<Link href="/contacts?sort=added&desc=1" />} className="gap-1.5"><Users className="size-4" /> See the contacts</Button>}
        <Button variant="outline" nativeButton={false} render={<Link href="/contacts/import" />} className="gap-1.5"><Upload className="size-4" /> Import another file</Button>
        <Button variant="outline" nativeButton={false} render={<a href={`/api/files/contact-imports/${imp.id}/report.xlsx`} download />} className="gap-1.5"><Download className="size-4" /> Download the report</Button>
        {!undid && <Button variant="ghost" onClick={undo} disabled={pending} className="gap-1.5 text-muted-foreground"><Undo2 className="size-4" /> Undo this import</Button>}
      </div>
    </div>
  );
}
