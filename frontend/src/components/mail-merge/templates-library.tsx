"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Copy, Loader2, Mail, Pencil, Plus, Trash2, Wand2 } from "lucide-react";
import { toast } from "sonner";
import type { MailTemplate, MergeField, TemplateKind } from "@/lib/messaging-types";
import { BRAND_LABEL, TEMPLATE_KIND_LABEL } from "@/lib/messaging-types";
import type { SalesTitle } from "@/lib/sales-types";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import { composeFromTemplate, deleteTemplate, loadActTemplates, saveTemplate } from "@/lib/messaging-actions";
import { ClientDataView } from "@/components/data-view/client-data-view";
import { DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips } from "@/components/data-view/toolbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { ProposalIssuePicker } from "@/components/sales/proposal-issue-picker";
import { EmailFromTemplate } from "@/components/mail-merge/email-from-template";
import { fmtDate } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-8 w-full min-w-0 truncate rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60 dark:bg-input/30";
const labelCls = "flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted-foreground";
const DEFAULT_SORT: SortState = { key: "name", dir: "asc" };

const ACCESSORS = {
  q: (t: MailTemplate) => [t.name, t.subject, t.body, t.description, t.owner_name, t.title_name],
  brand: (t: MailTemplate) => t.brand ?? "none",
  kind: (t: MailTemplate) => t.kind ?? "general",
  check: (t: MailTemplate) => !!t.needs_check,
  mine: (t: MailTemplate) => (t.mine ? "1" : "0"),
};
const SORTS = {
  name: (t: MailTemplate) => t.name.toLowerCase(),
  used: (t: MailTemplate) => t.use_count ?? 0,
  updated: (t: MailTemplate) => t.updated_at ?? "",
};

type Draft = { id?: string; name: string; subject: string; body: string; shared: boolean; brand: string; title_id: string; kind: TemplateKind; description: string };

export function TemplatesLibrary({ templates, fields, titles, canLoad }: { templates: MailTemplate[]; fields: MergeField[]; titles: SalesTitle[]; canLoad: boolean }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [useT, setUseT] = useState<MailTemplate | null>(null);
  const defs: FilterDef[] = [
    { kind: "search", key: "q", label: "Search templates", placeholder: "Name, words in the email, who wrote it…" },
    { kind: "multi", key: "brand", label: "Brand", section: "Template", options: [...Object.entries(BRAND_LABEL).map(([value, label]) => ({ value, label })), { value: "none", label: "Any brand" }] },
    { kind: "multi", key: "kind", label: "What it's for", section: "Template", options: Object.entries(TEMPLATE_KIND_LABEL).map(([value, label]) => ({ value, label })) },
    { kind: "tristate", key: "check", label: "Needs a check", section: "Template", yes: "Needs a check", no: "Checked" },
    { kind: "single", key: "mine", label: "Whose", section: "Template", options: [{ value: "1", label: "Only mine" }] },
  ];
  const needCheck = templates.filter((t) => t.needs_check).length;

  return (
    <>
      <ClientDataView rows={templates} defs={defs} defaultSort={DEFAULT_SORT} accessors={ACCESSORS} sortAccessors={SORTS}>
        {(rows) => (
          <DataViewLayout sidebar={<FilterSidebar title="Filter templates" />}>
            <div className="flex flex-wrap items-center gap-2">
              <DataSearch />
              {canLoad && (
                <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => start(async () => {
                  try { const r = await loadActTemplates(); toast.success(r.added ? `${r.added} templates loaded from ACT - check each before use` : "Clare's ACT templates are already here"); router.refresh(); }
                  catch (e) { toast.error(friendlyError(e, "Couldn't load the templates")); }
                })}><Wand2 className="size-3.5" /> Load Clare&apos;s ACT templates</Button>
              )}
              <Button size="sm" className="gap-1.5" onClick={() => setDraft({ name: "", subject: "", body: "Hi {{salutation|there}},\n\n\n\nKind regards\n{{my_name}}", shared: true, brand: "", title_id: "", kind: "pitch", description: "" })}>
                <Plus className="size-3.5" /> New template
              </Button>
            </div>
            <FilterChips />
            {needCheck > 0 && (
              <p className="flex items-start gap-2 rounded-lg border px-3 py-2 text-xs" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
                {needCheck} template{needCheck === 1 ? " was" : "s were"} brought over and need{needCheck === 1 ? "s" : ""} reading through - some mention old dates, prices or links. Open one, update it and save, and it&apos;s marked as checked.
              </p>
            )}
            {rows.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                {templates.length ? "No templates match these filters." : "No templates yet. Write one, or load Clare's templates from ACT."}
              </p>
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {rows.map((t) => (
                  <li key={t.id} className="flex flex-col rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-bold">{t.name}</h3>
                        <p className="text-[11px] text-muted-foreground">
                          {[t.brand ? BRAND_LABEL[t.brand] : null, t.title_name && t.title_name !== BRAND_LABEL[t.brand ?? ""] ? t.title_name : null, t.kind_label].filter(Boolean).join(" · ")}
                        </p>
                      </div>
                      {t.needs_check && <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ color: "var(--warn)", background: "color-mix(in oklab, var(--warn) 14%, transparent)" }}>Needs a check</span>}
                    </div>
                    {t.subject && <p className="mt-2 truncate text-xs"><span className="text-muted-foreground">Subject: </span>{t.subject}</p>}
                    <p className="mt-1 line-clamp-3 whitespace-pre-line text-xs text-muted-foreground">{t.body}</p>
                    {t.description && <p className="mt-2 text-[11px] italic text-muted-foreground">{t.description}</p>}
                    <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-3">
                      <Button size="xs" className="gap-1" onClick={() => setUseT(t)}><Mail className="size-3" /> Email someone</Button>
                      {t.can_edit && <Button size="xs" variant="outline" className="gap-1" onClick={() => setDraft({ id: t.id, name: t.name, subject: t.subject ?? "", body: t.body, shared: t.shared, brand: t.brand ?? "", title_id: t.title_id ?? "", kind: t.kind ?? "general", description: t.description ?? "" })}><Pencil className="size-3" /> Change</Button>}
                      <Button size="xs" variant="ghost" className="gap-1" onClick={() => setDraft({ name: `${t.name} (my copy)`, subject: t.subject ?? "", body: t.body, shared: false, brand: t.brand ?? "", title_id: t.title_id ?? "", kind: t.kind ?? "general", description: "" })}><Copy className="size-3" /> Copy</Button>
                      <span className="ml-auto text-[11px] text-muted-foreground">{t.owner_name ? `${t.owner_name} · ` : ""}{t.use_count ? `used ${t.use_count}×` : "not used yet"}{t.last_used_at ? `, last ${fmtDate(t.last_used_at.slice(0, 10))}` : ""}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </DataViewLayout>
        )}
      </ClientDataView>

      <Sheet open={!!draft} onOpenChange={(o) => !o && setDraft(null)}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-2xl">
          {draft && <TemplateEditor key={draft.id ?? "new"} draft={draft} fields={fields} titles={titles} onDone={() => { setDraft(null); router.refresh(); }} />}
        </SheetContent>
      </Sheet>
      {useT && <EmailFromTemplate open={!!useT} onOpenChange={(o) => !o && setUseT(null)} templates={[useT]} initialTemplateId={useT.id} />}
    </>
  );
}

function TemplateEditor({ draft, fields, titles, onDone }: { draft: Draft; fields: MergeField[]; titles: SalesTitle[]; onDone: () => void }) {
  const [d, setD] = useState(draft);
  const [pending, start] = useTransition();
  const [issueTitle, setIssueTitle] = useState(draft.title_id || titles[0]?.id || "");
  const [editionId, setEditionId] = useState("");
  const [preview, setPreview] = useState<{ subject: string; body: string; missing: string[] } | null>(null);
  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const set = (k: keyof Draft) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setD({ ...d, [k]: e.target.value });

  useEffect(() => {
    let live = true;
    const t = setTimeout(() => {
      composeFromTemplate({ subject: d.subject, body: d.body, brand: d.brand || null, edition_id: editionId || null })
        .then((r) => live && setPreview({ subject: r.subject, body: r.body, missing: r.missing })).catch(() => undefined);
    }, 400);
    return () => { live = false; clearTimeout(t); };
  }, [d.subject, d.body, d.brand, editionId]);

  function insert(key: string) {
    const el = bodyRef.current;
    const token = `{{${key}}}`;
    if (!el) return setD({ ...d, body: d.body + token });
    const s = el.selectionStart ?? d.body.length, e = el.selectionEnd ?? s;
    setD({ ...d, body: d.body.slice(0, s) + token + d.body.slice(e) });
    requestAnimationFrame(() => { el.focus(); el.setSelectionRange(s + token.length, s + token.length); });
  }

  const groups: [string, string, MergeField[]][] = [
    ["contact", "The contact", fields.filter((f) => (f.group ?? "contact") === "contact")],
    ["brand", "The brand (from its settings)", fields.filter((f) => f.group === "brand")],
    ["issue", "The issue (chosen when you send)", fields.filter((f) => f.group === "issue")],
  ];

  return (
    <>
      <SheetHeader className="border-b border-border/70">
        <SheetTitle>{d.id ? "Change template" : "New template"}</SheetTitle>
        <SheetDescription>Use merge fields for anything that changes: the contact&apos;s name, the brand&apos;s figures, the issue and feature. Write {"{{first_name|there}}"} to say &quot;there&quot; when a name is missing.</SheetDescription>
      </SheetHeader>
      <div className="flex flex-col gap-4 p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className={`${labelCls} sm:col-span-2`}>Name<Input value={d.name} onChange={set("name")} placeholder="e.g. Feature pitch: first email" className="h-8 text-sm" /></label>
          <label className={labelCls}>Brand
            <select className={selectCls} value={d.brand} onChange={set("brand")}>
              <option value="">Any brand</option>
              {Object.entries(BRAND_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className={labelCls}>Title (optional)
            <select className={selectCls} value={d.title_id} onChange={(e) => { setD({ ...d, title_id: e.target.value }); if (e.target.value) setIssueTitle(e.target.value); }}>
              <option value="">Any title</option>
              {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
          <label className={labelCls}>What it&apos;s for
            <select className={selectCls} value={d.kind} onChange={set("kind")}>
              {Object.entries(TEMPLATE_KIND_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 self-end pb-1.5 text-sm"><input type="checkbox" checked={d.shared} onChange={(e) => setD({ ...d, shared: e.target.checked })} /> Everyone can use it</label>
          <label className={`${labelCls} sm:col-span-2`}>Note for the team (optional)<Input value={d.description} onChange={set("description")} placeholder="When to use it, what to change first" className="h-8 text-sm" /></label>
          <label className={`${labelCls} sm:col-span-2`}>Subject<Input value={d.subject} onChange={set("subject")} className="h-8 text-sm" /></label>
          <label className={`${labelCls} sm:col-span-2`}>Email<Textarea ref={bodyRef} rows={14} value={d.body} onChange={set("body")} className="font-mono text-xs" /></label>
        </div>
        <div className="flex flex-col gap-2">
          <span className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">Insert a merge field <InfoHint>Click to put it where the cursor is. Brand figures come from the brand&apos;s settings in the editorial plan; issue details come from the issue you choose when sending.</InfoHint></span>
          {groups.map(([k, label, fs]) => (
            <div key={k} className="flex flex-wrap items-center gap-1">
              <span className="w-full text-[11px] text-muted-foreground sm:w-44">{label}</span>
              {fs.map((f) => <button key={f.key} type="button" onClick={() => insert(f.key)} className="rounded-full border border-border px-2 py-0.5 text-[11px] hover:bg-muted" title={`e.g. ${f.example}`}>{f.label}</button>)}
            </div>
          ))}
        </div>
        <section className="rounded-lg border border-border/70 bg-muted/20 p-3" aria-label="Preview">
          <div className="mb-2 flex flex-wrap items-end gap-2">
            <span className="text-xs font-bold">Preview</span>
            <label className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground">for
              <select className={`${selectCls} !h-7 !w-40 text-xs`} value={issueTitle} onChange={(e) => { setIssueTitle(e.target.value); setEditionId(""); }} aria-label="Title for the preview">
                {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <div className="w-56"><ProposalIssuePicker titleId={issueTitle || null} value={editionId} onChange={(id) => setEditionId(id)} emptyLabel="No issue (example values)" /></div>
          </div>
          {preview && <>
            <p className="text-xs"><span className="text-muted-foreground">Subject: </span>{preview.subject}</p>
            <p className="mt-2 whitespace-pre-line text-xs">{preview.body}</p>
            {preview.missing.length > 0 && <p className="mt-2 text-[11px]" style={{ color: "var(--warn)" }}>Nothing to fill in yet for: {preview.missing.map((k) => fields.find((f) => f.key === k)?.label ?? k).join(", ")}. Add a fallback like {"{{feature|our next feature}}"}, or fill in the brand&apos;s settings.</p>}
          </>}
        </section>
      </div>
      <SheetFooter className="flex-row border-t border-border/70">
        {d.id && <Button variant="ghost" className="mr-auto gap-1.5 text-destructive hover:text-destructive" disabled={pending} onClick={() => {
          if (!window.confirm(`Delete “${d.name}”?`)) return;
          start(async () => { try { await deleteTemplate(d.id!); toast.success("Deleted"); onDone(); } catch (e) { toast.error(friendlyError(e, "Couldn't delete it")); } });
        }}><Trash2 className="size-3.5" /> Delete</Button>}
        <Button variant="ghost" onClick={onDone}>Cancel</Button>
        <Button disabled={pending || !d.name.trim()} onClick={() => start(async () => {
          try {
            await saveTemplate({ name: d.name.trim(), subject: d.subject || null, body: d.body, shared: d.shared, brand: d.brand || null, title_id: d.title_id || null,
              kind: d.kind, description: d.description || null }, d.id);
            toast.success("Template saved"); onDone();
          } catch (e) { toast.error(friendlyError(e, "Couldn't save the template")); }
        })}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
      </SheetFooter>
    </>
  );
}
