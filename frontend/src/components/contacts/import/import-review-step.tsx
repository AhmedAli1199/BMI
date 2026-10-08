"use client";

import { useEffect, useState, useTransition } from "react";
import { AlertTriangle, ArrowLeft, Download, ExternalLink, Loader2, Search } from "lucide-react";
import { toast } from "sonner";
import type { ContactImport, ImportRowInfo, ImportReview } from "@/lib/contact-tools-types";
import { commitImport, patchImport, reviewImport } from "@/lib/contact-tools-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { friendlyError } from "@/lib/errors";

const STATUS: Record<ImportRowInfo["status"], { label: string; cls: string }> = {
  new: { label: "Will be added", cls: "bg-primary/10 text-primary" },
  update: { label: "Will update", cls: "bg-primary/10 text-primary" },
  skip_existing: { label: "Already in CRM - skipped", cls: "bg-muted text-muted-foreground" },
  skip_repeat: { label: "Repeated in file - skipped", cls: "bg-muted text-muted-foreground" },
  error: { label: "Can't import", cls: "bg-destructive/10 text-destructive" },
  excluded: { label: "Left out by you", cls: "bg-muted text-muted-foreground" },
};

type Filter = "new" | "update" | "skip_existing" | "skip_repeat" | "error" | "warnings" | "possible" | "excluded";
const TILES: { key: Filter; label: string; total: string }[] = [
  { key: "new", label: "Will be added", total: "new" },
  { key: "update", label: "Will be updated", total: "update" },
  { key: "skip_existing", label: "Already in the CRM", total: "skip_existing" },
  { key: "skip_repeat", label: "Repeated in the file", total: "skip_repeat" },
  { key: "possible", label: "Possible duplicates", total: "possible" },
  { key: "warnings", label: "Need a look", total: "warnings" },
  { key: "error", label: "Can't import", total: "error" },
  { key: "excluded", label: "Left out", total: "excluded" },
];

/** Step 3: what will happen to every row. Nothing is saved until "Import". */
export function ImportReviewStep({ imp, onChange, onBack }: { imp: ContactImport; onChange: (i: ContactImport) => void; onBack: () => void }) {
  const [filter, setFilter] = useState<Filter | null>(null);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ key: string; review: ImportReview } | null>(null);
  const [pending, start] = useTransition();
  const [confirm, setConfirm] = useState(false);
  const key = JSON.stringify([filter, query, page, imp.excluded, imp.options, imp.columns.map((c) => `${c.field}:${c.name ?? ""}`)]);

  useEffect(() => {
    let alive = true;
    reviewImport(imp.id, { status: filter, q: query, page, page_size: 50 })
      .then((review) => alive && setData({ key, review }))
      .catch((e) => alive && toast.error(friendlyError(e, "Couldn't prepare the review")));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, imp.id]);

  const review = data?.review;
  const loading = !data || data.key !== key;
  const t = review?.totals ?? {};
  const willImport = (t.new ?? 0) + (t.update ?? 0);
  const total = review?.total_rows ?? 0;
  const pages = Math.max(1, Math.ceil(total / 50));

  function toggle(row: ImportRowInfo) {
    const cur = new Set(imp.excluded);
    if (cur.has(row.n)) cur.delete(row.n); else cur.add(row.n);
    start(async () => { try { onChange(await patchImport(imp.id, { excluded: [...cur] })); } catch (e) { toast.error(friendlyError(e, "Couldn't save that")); } });
  }
  function run() {
    start(async () => {
      try {
        const r = await commitImport(imp.id);
        setConfirm(false);
        onChange(r);
      } catch (e) {
        setConfirm(false);
        toast.error(friendlyError(e, "The import didn't go through - nothing was saved."));
      }
    });
  }

  return (
    <div className="flex flex-col gap-5">
      <section aria-label="Summary" className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        {TILES.map((tile) => {
          const n = t[tile.total] ?? 0;
          if (n === 0 && tile.key !== "new") return null;
          const active = filter === tile.key;
          return (
            <button key={tile.key} type="button" aria-pressed={active} onClick={() => { setFilter(active ? null : tile.key); setPage(1); }}
              className={`flex h-full flex-col justify-between gap-1 rounded-xl border p-3 text-left transition-colors ${active ? "border-primary bg-primary/5" : "border-border/80 bg-card hover:bg-muted/40"}`}>
              <span className={`block text-xl font-bold tabular-nums ${tile.key === "error" && n ? "text-destructive" : tile.key === "warnings" && n ? "text-[var(--warn)]" : ""}`}>{n.toLocaleString()}</span>
              <span className="text-[11px] font-medium text-muted-foreground">{tile.label}</span>
            </button>
          );
        })}
      </section>

      <section className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs" aria-label="Rows">
        <div className="flex flex-wrap items-center gap-2 border-b border-border/70 px-4 py-2.5">
          <form className="relative min-w-48 flex-1 sm:max-w-xs" onSubmit={(e) => { e.preventDefault(); setQuery(q); setPage(1); }} role="search">
            <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" aria-hidden="true" />
            <Input aria-label="Search these rows" value={q} onChange={(e) => setQ(e.target.value)} onBlur={() => { if (q !== query) { setQuery(q); setPage(1); } }} placeholder="Search name, email, company…" className="h-8 pl-8 text-xs" />
          </form>
          {filter && <button type="button" onClick={() => setFilter(null)} className="text-xs font-semibold text-primary hover:underline">Show all rows</button>}
          <span className="ml-auto text-xs text-muted-foreground">{loading ? "Checking…" : `${total.toLocaleString()} row${total === 1 ? "" : "s"}`}</span>
          <a href={`/api/files/contact-imports/${imp.id}/report.xlsx`} download className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"><Download className="size-3.5" /> Download as Excel</a>
        </div>
        <div className={`overflow-x-auto ${loading ? "opacity-60" : ""}`}>
          <table className="w-full min-w-[44rem] text-sm">
            <caption className="sr-only">What will happen to each row of your file</caption>
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th scope="col" className="w-10 px-4 py-2"><span className="sr-only">Include</span></th>
                <th scope="col" className="w-12 px-1 py-2 font-semibold">Row</th>
                <th scope="col" className="px-2 py-2 font-semibold">Contact</th>
                <th scope="col" className="px-2 py-2 font-semibold">What happens</th>
                <th scope="col" className="px-4 py-2 font-semibold">Notes</th>
              </tr>
            </thead>
            <tbody>
              {(review?.rows ?? []).map((r) => {
                const togglable = r.status === "new" || r.status === "update" || r.status === "excluded";
                const st = STATUS[r.status];
                return (
                  <tr key={r.n} className={`border-t border-border/60 align-top ${r.status === "excluded" || r.status.startsWith("skip") ? "text-muted-foreground" : ""}`}>
                    <td className="px-4 py-2">{togglable && <input type="checkbox" aria-label={`Include row ${r.n}`} checked={r.status !== "excluded"} disabled={pending} onChange={() => toggle(r)} className="size-4 accent-[var(--primary)]" />}</td>
                    <td className="px-1 py-2 text-xs tabular-nums text-muted-foreground">{r.n}</td>
                    <td className="px-2 py-2">
                      <p className="font-medium text-foreground">{r.name ?? <span className="font-normal text-muted-foreground">(no name)</span>}</p>
                      <p className="text-xs text-muted-foreground">{[r.email, r.company, r.phone].filter(Boolean).join(" · ")}</p>
                    </td>
                    <td className="px-2 py-2">
                      <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ${st.cls}`}>{st.label}</span>
                      {r.match && (
                        <p className="mt-1 text-xs">
                          <a href={`/contacts/${r.match.id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">
                            {r.match.kind === "possible" ? "Possibly the same as" : "Already in the CRM as"} {r.match.name ?? "this contact"}
                            <ExternalLink className="size-3" aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span>
                          </a>
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2 text-xs">
                      {r.issues.map((i, k) => (
                        <p key={k} className={`flex items-start gap-1 ${i.level === "error" ? "font-medium text-destructive" : "text-[var(--warn)]"}`}>
                          <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden="true" />{i.text}
                        </p>
                      ))}
                    </td>
                  </tr>
                );
              })}
              {!loading && (review?.rows.length ?? 0) === 0 && <tr><td colSpan={5} className="px-4 py-10 text-center text-xs text-muted-foreground">No rows match.</td></tr>}
            </tbody>
          </table>
        </div>
        {pages > 1 && (
          <div className="flex items-center justify-between border-t border-border/70 px-4 py-2 text-xs text-muted-foreground">
            <span>Page {page} of {pages}</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          </div>
        )}
      </section>

      <div className="sticky bottom-0 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/80 bg-card/95 p-3 shadow-md backdrop-blur">
        <Button variant="ghost" size="sm" className="gap-1.5" onClick={onBack} disabled={pending}><ArrowLeft className="size-4" /> Back to matching</Button>
        <div className="flex items-center gap-3">
          <p className="hidden text-xs text-muted-foreground sm:block">Nothing is saved until you press Import. You can undo it afterwards.</p>
          <Button onClick={() => setConfirm(true)} disabled={pending || loading || willImport === 0}>
            Import {willImport.toLocaleString()} contact{willImport === 1 ? "" : "s"}
          </Button>
        </div>
      </div>

      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import {willImport.toLocaleString()} contact{willImport === 1 ? "" : "s"}?</DialogTitle>
            <DialogDescription>
              {(t.new ?? 0).toLocaleString()} will be added{(t.update ?? 0) > 0 && <> and {(t.update ?? 0).toLocaleString()} existing contact{t.update === 1 ? "" : "s"} updated</>}.
              {" "}{((t.skip_existing ?? 0) + (t.skip_repeat ?? 0) + (t.error ?? 0) + (t.excluded ?? 0)).toLocaleString()} row{((t.skip_existing ?? 0) + (t.skip_repeat ?? 0) + (t.error ?? 0) + (t.excluded ?? 0)) === 1 ? " is" : "s are"} left out. You&apos;ll be able to undo this.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" disabled={pending} />}>Not yet</DialogClose>
            <Button onClick={run} disabled={pending}>{pending && <Loader2 className="size-4 animate-spin" />} {pending ? "Importing…" : "Import them"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
