"use client";

import { useMemo, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, ExternalLink, Link2, Loader2, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import type { ExampleLibrary, ProposalExample } from "@/lib/proposals-types";
import { checkExampleLinks, saveExample } from "@/lib/proposals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { friendlyError } from "@/lib/errors";

type Draft = Omit<ProposalExample, "id" | "link_ok" | "checked_at" | "use_count">;
const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";
const selectCls = "h-8 rounded-lg border border-input bg-background px-2 text-sm font-normal text-foreground";

export function ExamplesLibrary({ lib, brand }: { lib: ExampleLibrary; brand: string }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [sector, setSector] = useState("");
  const [kind, setKind] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [editing, setEditing] = useState<{ id: string | null; d: Draft } | null>(null);
  const [pending, start] = useTransition();

  const rows = useMemo(() => lib.items.filter((x) =>
    (showArchived || !x.archived) && (!sector || x.sector === sector) && (!kind || x.kind === kind)
    && (!q.trim() || `${x.label} ${x.format ?? ""} ${x.client ?? ""}`.toLowerCase().includes(q.trim().toLowerCase()))), [lib.items, q, sector, kind, showArchived]);
  const broken = lib.items.filter((x) => x.link_ok === false && !x.archived).length;
  const set = (patch: Partial<Draft>) => setEditing((e) => (e ? { ...e, d: { ...e.d, ...patch } } : e));

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" aria-label="Brand" className="flex gap-1">
          {lib.brands.map((b) => (
            <Link key={b.key} role="tab" aria-selected={b.key === brand} href={`/sales/proposals/examples?brand=${b.key}`}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${b.key === brand ? "border-primary bg-primary/10" : "border-border text-muted-foreground hover:bg-accent/50"}`}>{b.name}</Link>
          ))}
        </div>
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => start(async () => {
            try { await checkExampleLinks(brand); toast.success("Checking every link - refresh in a minute to see the results"); }
            catch (e) { toast.error(friendlyError(e, "Couldn't start the link check")); }
          })}><Link2 className="size-3.5" /> Check the links</Button>
          <Button size="sm" className="gap-1.5" onClick={() => setEditing({ id: null, d: { brand, kind: "example", label: "", url: "", format: null, sector: null, client: null, notes: null, archived: false } })}>
            <Plus className="size-3.5" /> Add a link
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name, format or client…" className="h-8 w-64 text-sm" aria-label="Search" />
        <select className={selectCls} value={sector} onChange={(e) => setSector(e.target.value)} aria-label="Sector">
          <option value="">Every sector</option>
          {Object.entries(lib.sectors).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className={selectCls} value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Type">
          <option value="">Examples and resources</option>
          <option value="example">Examples of past pages</option>
          <option value="resource">Resources (media pack, features list...)</option>
        </select>
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground"><input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /> Show retired ones</label>
        <span className="ml-auto text-xs text-muted-foreground">
          {rows.length} shown{broken ? <> · <span className="font-semibold" style={{ color: "var(--warn)" }}>{broken} link{broken === 1 ? "" : "s"} not opening</span></> : null}
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[44rem] text-sm">
          <caption className="sr-only">Examples</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs text-muted-foreground">
              <th scope="col" className="px-4 py-2 font-semibold">What it is</th>
              <th scope="col" className="px-2 py-2 font-semibold">Format</th>
              <th scope="col" className="px-2 py-2 font-semibold">Sector</th>
              <th scope="col" className="px-2 py-2 font-semibold">Link</th>
              <th scope="col" className="px-2 py-2"><span className="sr-only">Change</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.id} className={`border-b border-border/60 last:border-0 ${x.archived ? "text-muted-foreground" : ""}`}>
                <td className="px-4 py-2">
                  <span className="font-medium">{x.label}</span>
                  {x.kind === "resource" && <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">Resource</span>}
                  {x.archived && <span className="ml-1.5 text-[11px]">retired</span>}
                  {x.client && <div className="text-[11px] text-muted-foreground">{x.client}</div>}
                </td>
                <td className="px-2 py-2 text-xs">{x.format ?? "—"}</td>
                <td className="px-2 py-2 text-xs">{x.sector ? lib.sectors[x.sector] ?? x.sector : "—"}</td>
                <td className="px-2 py-2 text-xs">
                  <a href={x.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">Open <ExternalLink className="size-3" aria-hidden="true" /></a>
                  {x.link_ok === false && <span className="ml-2 inline-flex items-center gap-1 font-semibold" style={{ color: "var(--warn)" }}><AlertTriangle className="size-3" aria-hidden="true" /> not opening</span>}
                  {x.link_ok === true && <CheckCircle2 className="ml-2 inline size-3 text-muted-foreground" aria-label="Link works" />}
                </td>
                <td className="px-2 py-2 text-right">
                  <Button size="icon-sm" variant="ghost" aria-label={`Change ${x.label}`} onClick={() => setEditing({ id: x.id, d: { brand: x.brand, kind: x.kind, label: x.label, url: x.url, format: x.format, sector: x.sector, client: x.client, notes: x.notes, archived: x.archived } })}>
                    <Pencil className="size-3.5" />
                  </Button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-muted-foreground">Nothing here yet. Add the links you send to clients most often.</td></tr>}
          </tbody>
        </table>
      </div>

      <Sheet open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-lg">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>{editing?.id ? "Change link" : "Add a link"}</SheetTitle>
            <SheetDescription>Paste the link as you&apos;d send it. Links copied from emails (with a security scanner&apos;s address wrapped round them) are cleaned up when you save.</SheetDescription>
          </SheetHeader>
          {editing && (
            <div className="flex flex-col gap-4 p-4">
              <label className={labelCls}>What it is<Input value={editing.d.label} onChange={(e) => set({ label: e.target.value })} placeholder="Spotlight on JetBlue (page 38)" className="h-8 text-sm" /></label>
              <label className={labelCls}>Link<Input value={editing.d.url} onChange={(e) => set({ url: e.target.value })} placeholder="https://issuu.com/…" className="h-8 text-sm" /></label>
              <label className={labelCls}>Type
                <select className={selectCls} value={editing.d.kind} onChange={(e) => set({ kind: e.target.value as Draft["kind"] })}>
                  <option value="example">An example of a past page</option>
                  <option value="resource">A resource (media pack, features list, website)</option>
                </select></label>
              <label className={labelCls}>Format
                <Input value={editing.d.format ?? ""} onChange={(e) => set({ format: e.target.value || null })} list="formats" placeholder="Spotlight on, Q&A, Double page sponsored…" className="h-8 text-sm" />
                <datalist id="formats">{lib.formats.map((f) => <option key={f} value={f} />)}</datalist></label>
              <label className={labelCls}>Sector (helps suggest it to similar clients)
                <select className={selectCls} value={editing.d.sector ?? ""} onChange={(e) => set({ sector: e.target.value || null })}>
                  <option value="">Any sector</option>
                  {Object.entries(lib.sectors).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select></label>
              <label className={labelCls}>Whose page it was (optional)<Input value={editing.d.client ?? ""} onChange={(e) => set({ client: e.target.value || null })} className="h-8 text-sm" /></label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={editing.d.archived} onChange={(e) => set({ archived: e.target.checked })} /> Retired - don&apos;t offer it any more</label>
            </div>
          )}
          <SheetFooter className="flex-row border-t border-border/70">
            <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
            <Button disabled={pending || !editing?.d.label.trim() || !editing?.d.url.trim()} onClick={() => editing && start(async () => {
              try { await saveExample(editing.id, editing.d); toast.success("Saved"); setEditing(null); router.refresh(); }
              catch (e) { toast.error(friendlyError(e, "Couldn't save the link")); }
            })}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
}
