"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, History, Loader2, PencilLine, Undo2 } from "lucide-react";
import { toast } from "sonner";
import type { BulkAction, BulkEdit, BulkPreview, ContactField, ContactScope } from "@/lib/contact-tools-types";
import { applyBulkUpdate, getBulkHistory, previewBulkUpdate, undoBulkUpdate } from "@/lib/contact-tools-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { InfoHint } from "@/components/sales/info-hint";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";

/** Change one field for a whole search or selection in one go (e.g. set the ABTA type for every Travel
 * Counsellor). It always shows what will change first, notes every change on each contact's history,
 * and can be undone afterwards. */
export function BulkUpdateDialog({ scope, fields, count, trigger }: { scope: ContactScope; fields: ContactField[]; count?: number; trigger?: React.ReactNode }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"change" | "history">("change");
  const [pending, start] = useTransition();
  const editable = useMemo(() => fields.filter((f) => f.bulk), [fields]);
  const groups = useMemo(() => {
    const m = new Map<string, ContactField[]>();
    for (const f of editable) m.set(f.group, [...(m.get(f.group) ?? []), f]);
    return [...m.entries()];
  }, [editable]);
  const [field, setField] = useState(editable[0]?.key ?? "");
  const [action, setAction] = useState<BulkAction>("set");
  const [value, setValue] = useState("");
  const [find, setFind] = useState("");
  const [previewed, setPreview] = useState<{ sig: string; data: BulkPreview } | null>(null);
  const [history, setHistory] = useState<BulkEdit[] | null>(null);
  const f = editable.find((x) => x.key === field);
  const isBool = f?.kind === "bool";

  // A preview only counts while the inputs are unchanged since it was made.
  const sig = JSON.stringify([field, action, value, find]);
  const preview = previewed?.sig === sig ? previewed.data : null;
  useEffect(() => { if (open && tab === "history") getBulkHistory().then(setHistory).catch(() => setHistory([])); }, [open, tab]);

  const body = () => ({ scope, field, op: action, value: action === "clear" ? undefined : isBool ? value || "yes" : value, find: action === "replace" ? find : undefined });
  const ready = !!field && (action === "clear" || (action === "set" ? (isBool || value.trim() !== "") : find.trim() !== ""));

  function runPreview() {
    start(async () => {
      try { setPreview({ sig, data: await previewBulkUpdate(body()) }); } catch (e) { toast.error(friendlyError(e, "Couldn't work out the changes")); }
    });
  }
  function apply() {
    start(async () => {
      try {
        const r = await applyBulkUpdate(body());
        toast.success(`Changed ${r.changed.toLocaleString()} contact${r.changed === 1 ? "" : "s"}`, {
          duration: 12000,
          action: { label: "Undo", onClick: () => undoBulkUpdate(r.id).then((u) => { toast.success(`Put back ${u.restored}${u.skipped ? ` (${u.skipped} had changed again, left alone)` : ""}`); router.refresh(); }).catch((e) => toast.error(friendlyError(e, "Couldn't undo"))) },
        });
        setOpen(false);
        setPreview(null);
        router.refresh();
      } catch (e) { toast.error(friendlyError(e, "Couldn't apply the change")); }
    });
  }
  function undo(id: string) {
    start(async () => {
      try {
        const u = await undoBulkUpdate(id);
        toast.success(`Put back ${u.restored}${u.skipped ? ` (${u.skipped} had changed again, left alone)` : ""}`);
        setHistory(await getBulkHistory());
        router.refresh();
      } catch (e) { toast.error(friendlyError(e, "Couldn't undo")); }
    });
  }

  const what = (e: BulkEdit) => e.op === "clear" ? `Cleared ${e.field_label}` : e.op === "replace" ? `${e.field_label}: “${e.find_text}” → “${e.new_value ?? ""}”` : `Set ${e.field_label} to “${e.new_value}”`;

  return (
    <>
      <span onClick={() => setOpen(true)} role="presentation">
        {trigger ?? <Button size="sm" variant="outline"><PencilLine className="size-3.5" /> Bulk update</Button>}
      </span>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Change many contacts at once</DialogTitle>
            <DialogDescription>
              {count !== undefined ? `${count.toLocaleString()} contact${count === 1 ? "" : "s"}` : "These contacts"} - {scope.label ?? "your selection"}. You&apos;ll see what will change before anything is saved.
            </DialogDescription>
          </DialogHeader>
          <div role="tablist" aria-label="Bulk update" className="flex gap-1 border-b border-border/70">
            {([["change", "Make a change", PencilLine], ["history", "Recent changes", History]] as const).map(([k, l, Icon]) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`-mb-px flex items-center gap-1.5 border-b-2 px-3 py-1.5 text-xs font-semibold ${tab === k ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
                <Icon className="size-3.5" /> {l}
              </button>
            ))}
          </div>

          {tab === "change" ? (
            <div className="grid gap-3">
              <label className={labelCls}>
                <span className="flex items-center gap-1">Which field? <InfoHint>Names, job details, status flags and the Act! custom fields can be changed here. Email, phone and address are edited on each contact.</InfoHint></span>
                <select className={selectCls} value={field} onChange={(e) => { setField(e.target.value); setAction("set"); setValue(""); }}>
                  {groups.map(([g, fs]) => <optgroup key={g} label={g}>{fs.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}</optgroup>)}
                </select>
              </label>
              <div role="radiogroup" aria-label="What to do" className="flex flex-wrap gap-1.5">
                {([["set", "Set it to…"], ["clear", "Clear it"], ...(isBool ? [] : [["replace", "Find and replace"]])] as [BulkAction, string][]).map(([k, l]) => (
                  <button key={k} role="radio" aria-checked={action === k} onClick={() => setAction(k)} className={`rounded-full border px-3 py-1 text-xs font-medium ${action === k ? "border-primary bg-primary/10 text-foreground" : "border-border text-muted-foreground hover:text-foreground"}`}>{l}</button>
                ))}
              </div>
              {action === "set" && (isBool ? (
                <select aria-label="New value" className={selectCls} value={value || "yes"} onChange={(e) => setValue(e.target.value)} onFocus={() => !value && setValue("yes")}>
                  <option value="yes">Yes</option><option value="no">No</option>
                </select>
              ) : (
                <label className={labelCls}>New value<Input value={value} onChange={(e) => setValue(e.target.value)} className="h-8 text-sm" placeholder="Type the new value" autoFocus /></label>
              ))}
              {action === "replace" && (
                <div className="grid grid-cols-2 gap-2">
                  <label className={labelCls}>Find<Input value={find} onChange={(e) => setFind(e.target.value)} className="h-8 text-sm" /></label>
                  <label className={labelCls}>Replace with<Input value={value} onChange={(e) => setValue(e.target.value)} className="h-8 text-sm" placeholder="(leave empty to remove it)" /></label>
                </div>
              )}
              {preview && (
                <div className="rounded-lg border border-border/80 bg-muted/30 p-3 text-sm" aria-live="polite">
                  <p className="font-semibold">{preview.will_change.toLocaleString()} of {preview.total.toLocaleString()} contacts will change{preview.unchanged ? <span className="font-normal text-muted-foreground"> ({preview.unchanged.toLocaleString()} already match)</span> : null}</p>
                  {preview.samples.length > 0 && (
                    <ul className="mt-2 flex flex-col gap-1 text-xs">
                      {preview.samples.map((s) => (
                        <li key={s.id} className="flex items-center gap-2">
                          <span className="w-32 truncate font-medium">{s.name ?? "Unnamed"}</span>
                          <span className="truncate text-muted-foreground">{s.old ?? "(empty)"}</span>
                          <ArrowRight className="size-3 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <span className="truncate font-semibold">{s.new ?? "(empty)"}</span>
                        </li>
                      ))}
                      {preview.will_change > preview.samples.length && <li className="text-muted-foreground">…and {(preview.will_change - preview.samples.length).toLocaleString()} more</li>}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="max-h-72 overflow-y-auto">
              {history === null ? <p className="py-6 text-center text-xs text-muted-foreground">Loading…</p> : history.length === 0 ? <p className="py-6 text-center text-xs text-muted-foreground">No bulk changes yet.</p> : (
                <ul className="divide-y divide-border/60">
                  {history.map((e) => (
                    <li key={e.id} className="flex items-center gap-3 py-2 text-xs">
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold">{what(e)}</p>
                        <p className="text-muted-foreground">{e.changed.toLocaleString()} contact{e.changed === 1 ? "" : "s"}{e.scope_label ? ` · ${e.scope_label}` : ""} · {e.by ?? "someone"} · {new Date(e.created_at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</p>
                      </div>
                      {e.status === "undone" ? <span className="text-muted-foreground">Undone</span> : <Button size="sm" variant="outline" disabled={pending} onClick={() => undo(e.id)} className="gap-1"><Undo2 className="size-3" /> Undo</Button>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {tab === "change" && (
            <DialogFooter>
              <DialogClose render={<Button variant="ghost" />}>Cancel</DialogClose>
              {preview ? (
                <Button onClick={apply} disabled={pending || preview.will_change === 0}>{pending && <Loader2 className="size-4 animate-spin" />} Change {preview.will_change.toLocaleString()} contact{preview.will_change === 1 ? "" : "s"}</Button>
              ) : (
                <Button onClick={runPreview} disabled={pending || !ready}>{pending && <Loader2 className="size-4 animate-spin" />} See what will change</Button>
              )}
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
