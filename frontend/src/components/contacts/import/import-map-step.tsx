"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowRight, Check, CircleHelp, EyeOff, Loader2, RefreshCw, Sparkles, Trash2, Wand2 } from "lucide-react";
import { toast } from "sonner";
import type { ContactImport, ImportColumn, ImportOptions, ImportTarget } from "@/lib/contact-tools-types";
import { autoMapImport, discardImport, patchImport } from "@/lib/contact-tools-actions";
import { searchGroups } from "@/lib/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EntityPicker } from "@/components/entity-picker";
import { InfoHint } from "@/components/sales/info-hint";

const selectCls = "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const GROUP_ORDER = ["Name", "Job", "Company", "Email", "Phone", "Address", "Other", "Custom fields"];

export function colLetter(i: number): string {
  let s = "";
  let n = i + 1;
  while (n) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

type Mapping = Record<string, { field: string; name?: string | null; type?: string | null }>;

function Status({ col }: { col: ImportColumn }) {
  const base = "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold";
  if (col.field === "skip") return <span className={`${base} bg-muted text-muted-foreground`}><EyeOff className="size-3" aria-hidden="true" /> {col.level === "empty" ? "Empty" : "Not imported"}</span>;
  if (col.level === "manual") return <span className={`${base} bg-primary/10 text-primary`}><Check className="size-3" aria-hidden="true" /> Your choice</span>;
  if (col.level === "high") return <span className={`${base} bg-primary/10 text-primary`}><Sparkles className="size-3" aria-hidden="true" /> Matched</span>;
  return <span className={`${base} bg-amber-500/15 text-amber-700 dark:text-amber-400`}><CircleHelp className="size-3" aria-hidden="true" /> Check this</span>;
}

/** Step 2: every column of the file next to the field it was matched to. Matched ones are filled in; anything
 * we aren't sure of is flagged, and every choice can be changed. */
export function ImportMapStep({ imp, targets, publications, onChange, onNext }: {
  imp: ContactImport; targets: ImportTarget[]; publications: { slug: string; name: string }[]; onChange: (i: ContactImport) => void; onNext: () => void;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [showFile, setShowFile] = useState(false);
  const [groupMode, setGroupMode] = useState<"none" | "new" | "existing">(imp.options.group_id ? "existing" : imp.options.new_group_name ? "new" : "none");
  const [groupPick, setGroupPick] = useState<{ id: string; label: string } | null>(null);
  const groups = useMemo(() => {
    const m = new Map<string, ImportTarget[]>();
    for (const t of targets) m.set(t.group, [...(m.get(t.group) ?? []), t]);
    return GROUP_ORDER.filter((g) => m.has(g)).map((g) => [g, m.get(g)!] as const);
  }, [targets]);
  const label = (key: string) => targets.find((t) => t.key === key)?.label ?? key;

  const unmatched = imp.columns.filter((c) => c.field === "skip" && (c.level === "none" || c.level === "ambiguous"));
  const check = imp.columns.filter((c) => c.field !== "skip" && (c.level === "medium"));
  const matched = imp.columns.filter((c) => c.field !== "skip").length;
  const opts = imp.options;

  function run(fn: () => Promise<ContactImport>, error = "Couldn't save that") {
    start(async () => { try { onChange(await fn()); } catch (e) { toast.error(e instanceof Error ? e.message : error); } });
  }
  const setMapping = (m: Mapping) => run(() => patchImport(imp.id, { mapping: m }));
  const setOptions = (o: Partial<ImportOptions>) => run(() => patchImport(imp.id, { options: o }));
  const choose = (col: ImportColumn, field: string) => setMapping({ [col.index]: { field, name: field === "new_custom" ? col.header : null } });

  // The preview shows how the first rows would look as contacts.
  const previews = useMemo(() => imp.preview_rows.slice(0, 3).map((row) => {
    const get = (...keys: string[]) => keys.map((k) => { const c = imp.columns.find((x) => x.field === k); return c ? row[c.index] ?? "" : ""; }).filter(Boolean);
    const name = [...get("first_name"), ...get("last_name")].join(" ") || get("full_name")[0] || "";
    const emails = get("email", "email_2", "email_3");
    const phones = get("phone", "mobile", "home_phone", "other_phone");
    const address = get("address_line1", "address_line2", "address_line3", "city", "state", "postcode", "country").join(", ");
    return { name, sub: [get("job_title")[0], get("company")[0]].filter(Boolean).join(" · "), emails, phones, address, more: imp.columns.filter((c) => c.field.startsWith("custom:") || c.field === "new_custom").map((c) => `${c.name || label(c.field)}: ${row[c.index] ?? ""}`) };
  }), [imp.preview_rows, imp.columns]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="flex min-w-0 flex-col gap-5">
        {/* summary */}
        <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs" aria-label="Matching summary">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary"><Wand2 className="size-5" aria-hidden="true" /></div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold">{matched} of {imp.columns.length} columns matched to a contact field</p>
              <p className="text-xs text-muted-foreground">
                {imp.row_count.toLocaleString()} {imp.row_count === 1 ? "row" : "rows"}
                {check.length > 0 && <> · <span className="font-semibold text-amber-700 dark:text-amber-400">{check.length} to check</span></>}
                {unmatched.length > 0 && <> · <span className="font-semibold text-foreground">{unmatched.length} we couldn&apos;t place</span></>}
              </p>
            </div>
            <Button size="sm" variant="outline" disabled={pending} className="gap-1.5" onClick={() => { if (window.confirm("Match the columns again? Changes you made here will be lost.")) run(() => autoMapImport(imp.id)); }}>
              <RefreshCw className="size-3.5" /> Match again
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowFile(!showFile)} aria-expanded={showFile}>File settings</Button>
          </div>
          {imp.notes.map((n) => <p key={n} className="mt-2 flex items-start gap-1.5 text-xs text-muted-foreground"><AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600" aria-hidden="true" />{n}</p>)}
          {showFile && (
            <div className="mt-3 grid gap-3 border-t border-border/70 pt-3 sm:grid-cols-3">
              {imp.sheets.length > 1 && (
                <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Sheet
                  <select className={selectCls} value={imp.sheet_name ?? ""} onChange={(e) => run(() => patchImport(imp.id, { sheet: e.target.value }))}>
                    {imp.sheets.map((s) => <option key={s.name} value={s.name}>{s.name} ({s.rows} rows)</option>)}
                  </select>
                </label>
              )}
              <label className="flex items-center gap-2 text-xs font-semibold text-muted-foreground sm:pt-5">
                <input type="checkbox" checked={imp.has_header} onChange={(e) => run(() => patchImport(imp.id, { has_header: e.target.checked }))} className="size-4 accent-[var(--primary)]" /> The file has a heading row
              </label>
              {imp.has_header && (
                <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Which line has the headings?
                  <select className={selectCls} value={imp.header_row} onChange={(e) => run(() => patchImport(imp.id, { header_row: Number(e.target.value) }))}>
                    {imp.raw_top.map((r, i) => <option key={i} value={i}>Row {i + 1}: {r.filter(Boolean).slice(0, 3).join(", ").slice(0, 40) || "(blank)"}</option>)}
                  </select>
                </label>
              )}
            </div>
          )}
        </section>

        {/* columns */}
        <section aria-label="Columns" className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
          <div className="hidden grid-cols-[minmax(0,1fr)_1.5rem_minmax(0,1fr)] items-center gap-3 border-b border-border/70 bg-muted/30 px-4 py-2 text-xs font-semibold text-muted-foreground md:grid">
            <span>Column in your file</span><span /><span className="flex items-center gap-1">Goes into this contact field <InfoHint>Pick “Don&apos;t import” to leave a column out, or “Import as a new custom field” to keep it as an extra field on each contact.</InfoHint></span>
          </div>
          <ul className="divide-y divide-border/60">
            {imp.columns.map((c) => {
              const unsure = c.field === "skip" && (c.level === "none" || c.level === "ambiguous");
              return (
                <li key={c.index} className={`grid gap-2 px-4 py-3 md:grid-cols-[minmax(0,1fr)_1.5rem_minmax(0,1fr)] md:items-start md:gap-3 ${unsure ? "bg-amber-500/5" : ""}`}>
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 text-sm font-semibold"><span className="truncate">{c.header}</span><span className="shrink-0 rounded bg-muted px-1.5 py-px text-[10px] font-medium text-muted-foreground">Column {colLetter(c.index)}</span></p>
                    <p className="mt-1 flex flex-wrap gap-1" aria-label="Examples from this column">
                      {c.samples.slice(0, 3).map((s) => <span key={s} className="max-w-40 truncate rounded-md border border-border/70 bg-background px-1.5 py-0.5 text-[11px] text-muted-foreground" title={s}>{s}</span>)}
                      {c.samples.length === 0 && <span className="text-[11px] text-muted-foreground">(empty)</span>}
                    </p>
                  </div>
                  <ArrowRight className="hidden size-4 self-center text-muted-foreground md:block" aria-hidden="true" />
                  <div className="flex min-w-0 flex-col gap-1.5">
                    <div className="flex items-center gap-2">
                      <select aria-label={`Field for column ${c.header}`} className={selectCls} value={c.field} onChange={(e) => choose(c, e.target.value)}>
                        <option value="skip">Don&apos;t import this column</option>
                        {groups.map(([g, ts]) => <optgroup key={g} label={g}>{ts.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</optgroup>)}
                        <option value="new_custom">＋ Import as a new custom field…</option>
                      </select>
                      <Status col={c} />
                    </div>
                    {c.field === "new_custom" && (
                      <Input aria-label="Name of the new field" defaultValue={c.name ?? c.header} onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== c.name) setMapping({ [c.index]: { field: "new_custom", name: v } }); }} placeholder="Name this field, e.g. ABTA number" className="h-8 text-sm" />
                    )}
                    <p className="text-[11px] leading-snug text-muted-foreground">{c.level === "manual" ? "You chose this." : c.reason}</p>
                    {c.warning && <p className="flex items-center gap-1 text-[11px] font-medium text-amber-700 dark:text-amber-400"><AlertTriangle className="size-3" aria-hidden="true" />{c.warning}</p>}
                    {c.field === "skip" && c.candidates.length > 0 && (
                      <p className="flex flex-wrap items-center gap-1 text-[11px]">
                        <span className="text-muted-foreground">Maybe:</span>
                        {c.candidates.map((k) => <button key={k.field} type="button" onClick={() => choose(c, k.field)} className="rounded-full border border-primary/40 px-2 py-0.5 font-semibold text-primary hover:bg-primary/10">Use {k.label}</button>)}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          {unmatched.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 border-t border-border/70 bg-muted/30 px-4 py-2 text-xs">
              <span className="text-muted-foreground">{unmatched.length} column{unmatched.length === 1 ? "" : "s"} not matched - they&apos;re left out unless you choose a field.</span>
              <Button size="sm" variant="ghost" className="h-7 text-xs" disabled={pending} onClick={() => setMapping(Object.fromEntries(unmatched.map((c) => [c.index, { field: "new_custom", name: c.header }])))}>Keep them all as custom fields</Button>
            </div>
          )}
        </section>

        {/* options */}
        <section aria-label="Import options" className="grid gap-5 rounded-xl border border-border/80 bg-card p-4 shadow-2xs md:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
            <span className="flex items-center gap-1">Which database do they belong to? <InfoHint>Each BMI title keeps its own contact book. The people you import are added to the one you pick, and we only look for duplicates there.</InfoHint></span>
            <select className={selectCls} value={opts.source_db ?? ""} onChange={(e) => setOptions({ source_db: e.target.value || null })}>
              <option value="">Choose a database…</option>
              {publications.map((p) => <option key={p.slug} value={p.slug}>{p.name}</option>)}
            </select>
          </label>
          <div className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
            Add everyone to a group (optional)
            <div className="flex gap-2">
              <select aria-label="Group" className={`${selectCls} !w-36 shrink-0`} value={groupMode}
                onChange={(e) => {
                  const m = e.target.value as typeof groupMode;
                  setGroupMode(m);
                  setOptions(m === "none" ? { group_id: null, new_group_name: null } : m === "new" ? { group_id: null, new_group_name: `Import ${imp.filename.replace(/\.[^.]+$/, "")}` } : { new_group_name: null, group_id: groupPick?.id ?? null });
                }}>
                <option value="none">No group</option><option value="new">A new group</option><option value="existing">An existing group</option>
              </select>
              {groupMode === "existing" && (
                <div className="min-w-0 flex-1"><EntityPicker label="" placeholder="Search groups…" search={async (q) => (await searchGroups(q)).map((g) => ({ id: g.id, label: g.name }))} value={groupPick} onChange={(g) => { setGroupPick(g); setOptions({ group_id: g?.id ?? null }); }} /></div>
              )}
              {groupMode === "new" && <Input aria-label="New group name" defaultValue={opts.new_group_name ?? ""} onBlur={(e) => setOptions({ new_group_name: e.target.value.trim() || null })} className="h-9 min-w-0 flex-1 text-sm" />}
            </div>
            {groupMode === "none" && <span className="text-[11px] font-normal">A group makes it easy to find this batch later.</span>}
          </div>
          <fieldset className="md:col-span-2">
            <legend className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-muted-foreground">If someone is already in the CRM <InfoHint>We recognise people by email address, or by name plus company. Changes made here can be undone from the import&apos;s page.</InfoHint></legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {([
                ["fill_blanks", "Fill in what's missing", "Keeps what's there, adds new emails, phones and details."],
                ["skip", "Leave them alone", "Skip anyone who's already in the CRM."],
                ["overwrite", "Update with the file", "Replace their details with what's in your file."],
                ["create", "Add them again anyway", "Creates a second record (not usually wanted)."],
              ] as const).map(([v, t, d]) => (
                <label key={v} className={`flex cursor-pointer gap-2.5 rounded-lg border p-2.5 text-xs ${opts.on_duplicate === v ? "border-primary bg-primary/5" : "border-border/80 hover:bg-muted/40"}`}>
                  <input type="radio" name="dup" checked={opts.on_duplicate === v} onChange={() => setOptions({ on_duplicate: v })} className="mt-0.5 size-4 accent-[var(--primary)]" />
                  <span><span className="block font-semibold text-foreground">{t}</span><span className="text-muted-foreground">{d}</span></span>
                </label>
              ))}
            </div>
          </fieldset>
          <label className="flex items-center gap-2 text-xs font-semibold text-muted-foreground md:col-span-2">
            <input type="checkbox" checked={opts.create_companies} onChange={(e) => setOptions({ create_companies: e.target.checked })} className="size-4 accent-[var(--primary)]" />
            Create companies that aren&apos;t in the CRM yet <span className="font-normal">(companies already there are linked, even if spelled “Ltd” or “Limited”)</span>
          </label>
        </section>

        {/* footer */}
        <div className="sticky bottom-0 z-10 -mx-1 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/80 bg-card/95 p-3 shadow-md backdrop-blur">
          <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground" disabled={pending} onClick={() => { if (window.confirm("Discard this import?")) start(async () => { await discardImport(imp.id); router.push("/contacts/import"); }); }}>
            <Trash2 className="size-3.5" /> Discard
          </Button>
          <div className="flex min-w-0 flex-1 items-center justify-end gap-3">
            {imp.problems.length > 0 && <p role="alert" className="min-w-0 flex-1 text-right text-xs font-medium text-destructive">{imp.problems[0]}{imp.problems.length > 1 ? ` (+${imp.problems.length - 1} more)` : ""}</p>}
            <Button onClick={onNext} disabled={pending || imp.problems.length > 0} className="gap-1.5">
              {pending ? <Loader2 className="size-4 animate-spin" /> : null} Review {imp.row_count.toLocaleString()} {imp.row_count === 1 ? "row" : "rows"} <ArrowRight className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* live preview */}
      <aside aria-label="Preview" className="lg:sticky lg:top-4 lg:self-start">
        <div className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
          <h2 className="mb-1 flex items-center gap-1.5 text-sm font-bold">How your first rows will look <InfoHint>Updates as you change the matching.</InfoHint></h2>
          <ul className="mt-3 flex flex-col gap-3">
            {previews.map((p, i) => (
              <li key={i} className="rounded-lg border border-border/70 bg-background p-3 text-xs">
                <p className="text-sm font-semibold">{p.name || <span className="font-normal text-muted-foreground">No name matched</span>}</p>
                {p.sub && <p className="text-muted-foreground">{p.sub}</p>}
                {p.emails.map((e) => <p key={e} className="truncate">{e}</p>)}
                {p.phones.map((e) => <p key={e} className="text-muted-foreground">{e}</p>)}
                {p.address && <p className="mt-1 text-muted-foreground">{p.address}</p>}
                {p.more.map((m) => <p key={m} className="mt-1 text-muted-foreground">{m}</p>)}
              </li>
            ))}
            {previews.length === 0 && <li className="text-xs text-muted-foreground">No rows to show.</li>}
          </ul>
        </div>
      </aside>
    </div>
  );
}
