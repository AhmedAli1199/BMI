"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { MergeField, TemplateKind } from "@/lib/messaging-types";
import { BRAND_LABEL, TEMPLATE_KIND_LABEL } from "@/lib/messaging-types";
import type { SalesTitle } from "@/lib/sales-types";
import { composeFromTemplate, deleteTemplate, saveTemplate } from "@/lib/messaging-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";
import { PageHeader } from "@/components/page-header";
import { ProposalIssuePicker } from "@/components/sales/proposal-issue-picker";
import { EmailBodyView, RichEmailEditor, type RichEmailEditorHandle } from "@/components/mail-merge/rich-email-editor";

const selectCls = "h-9 w-full min-w-0 truncate rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60 dark:bg-input/30";
const labelCls = "flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted-foreground";

export type TemplateDraft = { id?: string; name: string; subject: string; body: string; shared: boolean; brand: string; title_id: string; kind: TemplateKind; description: string; needs_check?: boolean };

/** The template editor, on a page of its own: details on the left, the email in a formatting editor, a live preview on the right. */
export function TemplateEditor({ draft, fields, titles }: { draft: TemplateDraft; fields: MergeField[]; titles: SalesTitle[] }) {
  const router = useRouter();
  const [d, setD] = useState(draft);
  const [pending, start] = useTransition();
  const [issueTitle, setIssueTitle] = useState(draft.title_id || titles[0]?.id || "");
  const [editionId, setEditionId] = useState("");
  const [preview, setPreview] = useState<{ subject: string; body: string; missing: string[] } | null>(null);
  const [focus, setFocus] = useState<"subject" | "body">("body");
  const [dirty, setDirty] = useState(false);
  const bodyRef = useRef<RichEmailEditorHandle>(null);
  const subjectRef = useRef<HTMLInputElement>(null);
  const change = (patch: Partial<TemplateDraft>) => { setD((x) => ({ ...x, ...patch })); setDirty(true); };

  useEffect(() => {
    let live = true;
    const t = setTimeout(() => {
      composeFromTemplate({ subject: d.subject, body: d.body, brand: d.brand || null, edition_id: editionId || null })
        .then((r) => live && setPreview({ subject: r.subject, body: r.body, missing: r.missing })).catch(() => undefined);
    }, 400);
    return () => { live = false; clearTimeout(t); };
  }, [d.subject, d.body, d.brand, editionId]);

  // Warn before leaving with unsaved changes.
  useEffect(() => {
    if (!dirty) return;
    const h = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);

  function insert(key: string) {
    const token = `{{${key}}}`;
    if (focus === "subject") {
      const el = subjectRef.current;
      const s = el?.selectionStart ?? d.subject.length, e = el?.selectionEnd ?? s;
      change({ subject: d.subject.slice(0, s) + token + d.subject.slice(e) });
      requestAnimationFrame(() => { el?.focus(); el?.setSelectionRange(s + token.length, s + token.length); });
    } else {
      bodyRef.current?.insertText(token);
    }
  }

  const groups: [string, string, MergeField[]][] = [
    ["contact", "The contact", fields.filter((f) => (f.group ?? "contact") === "contact")],
    ["brand", "The brand (from its settings)", fields.filter((f) => f.group === "brand")],
    ["issue", "The issue (chosen when you send)", fields.filter((f) => f.group === "issue")],
  ];

  const back = () => router.push("/mail-merge/templates");

  function save() {
    start(async () => {
      try {
        await saveTemplate({ name: d.name.trim(), subject: d.subject || null, body: d.body, shared: d.shared, brand: d.brand || null, title_id: d.title_id || null,
          kind: d.kind, description: d.description || null, needs_check: false }, d.id);   // saved here = read through and checked
        setDirty(false);
        toast.success("Template saved");
        router.push("/mail-merge/templates");
        router.refresh();
      } catch (e) { toast.error(friendlyError(e, "Couldn't save the template")); }
    });
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title={d.id ? (d.name || "Untitled template") : "New template"}
        crumbs={[{ label: "Email templates", href: "/mail-merge/templates" }]}
        description={<>Use merge fields for anything that changes, like the contact&apos;s name or the issue. Write {"{{first_name|there}}"} to say &quot;there&quot; when a name is missing.</>}
        below={d.needs_check ? <p className="text-xs font-medium" style={{ color: "var(--warn)" }}>Brought over from ACT - read it through and update old dates, prices or links. Saving marks it as checked.</p> : undefined}
        actions={<>
          {d.id && <Button variant="ghost" className="gap-1.5 text-destructive hover:text-destructive" disabled={pending} onClick={() => {
            if (!window.confirm(`Delete “${d.name}”?`)) return;
            start(async () => { try { await deleteTemplate(d.id!); setDirty(false); toast.success("Deleted"); back(); router.refresh(); } catch (e) { toast.error(friendlyError(e, "Couldn't delete it")); } });
          }}><Trash2 className="size-3.5" /> Delete</Button>}
          <Button variant="outline" onClick={() => { if (!dirty || window.confirm("Leave without saving your changes?")) back(); }}>Cancel</Button>
          <Button disabled={pending || !d.name.trim()} onClick={save}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
        </>}
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="flex min-w-0 flex-col gap-5">
          <section aria-labelledby="tpl-details" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
            <h2 id="tpl-details" className="mb-3 text-sm font-bold">About this template</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={`${labelCls} sm:col-span-2`}>Name<Input value={d.name} onChange={(e) => change({ name: e.target.value })} placeholder="e.g. Feature pitch: first email" /></label>
              <label className={labelCls}>Brand
                <select className={selectCls} value={d.brand} onChange={(e) => change({ brand: e.target.value })}>
                  <option value="">Any brand</option>
                  {Object.entries(BRAND_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className={labelCls}>Title (optional)
                <select className={selectCls} value={d.title_id} onChange={(e) => { change({ title_id: e.target.value }); if (e.target.value) { setIssueTitle(e.target.value); setEditionId(""); } }}>
                  <option value="">Any title</option>
                  {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </label>
              <label className={labelCls}>What it&apos;s for
                <select className={selectCls} value={d.kind} onChange={(e) => change({ kind: e.target.value as TemplateKind })}>
                  {Object.entries(TEMPLATE_KIND_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className="flex items-center gap-2 self-end pb-2 text-sm"><input type="checkbox" checked={d.shared} onChange={(e) => change({ shared: e.target.checked })} /> Everyone can use it</label>
              <label className={`${labelCls} sm:col-span-2`}>Note for the team (optional)<Input value={d.description} onChange={(e) => change({ description: e.target.value })} placeholder="When to use it, what to change first" /></label>
            </div>
          </section>

          <section aria-labelledby="tpl-email" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
            <h2 id="tpl-email" className="mb-3 text-sm font-bold">The email</h2>
            <div className="flex flex-col gap-3">
              <label className={labelCls}>Subject<Input ref={subjectRef} value={d.subject} onFocus={() => setFocus("subject")} onChange={(e) => change({ subject: e.target.value })} /></label>
              <div className={labelCls}>
                <span className="flex items-center gap-1">Message <InfoHint>Select some words, then use the buttons above the message to make them bold, italic or underlined, highlight them, colour them, or turn lines into a list. Ctrl+B, Ctrl+I and Ctrl+U work too.</InfoHint></span>
                <RichEmailEditor ref={bodyRef} value={d.body} onChange={(html) => change({ body: html })} onFocus={() => setFocus("body")} minHeight="22rem" ariaLabel="Message" />
              </div>
              <div className="flex flex-col gap-2 pt-1">
                <span className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">Insert a merge field into the {focus === "subject" ? "subject" : "message"} <InfoHint>Click to put it where the cursor is. Brand figures come from the brand&apos;s settings in the editorial plan; issue details come from the issue you choose when sending.</InfoHint></span>
                {groups.map(([k, label, fs]) => (
                  <div key={k} className="flex flex-wrap items-center gap-1">
                    <span className="w-full text-[11px] text-muted-foreground sm:w-48">{label}</span>
                    {fs.map((f) => <button key={f.key} type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => insert(f.key)} className="rounded-full border border-border px-2 py-0.5 text-[11px] hover:bg-muted" title={`e.g. ${f.example}`}>{f.label}</button>)}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        <aside aria-label="Preview" className="min-w-0 lg:sticky lg:top-4 lg:self-start">
          <section className="rounded-xl border border-border/80 bg-card shadow-2xs">
            <div className="flex flex-wrap items-end gap-2 border-b border-border/70 px-5 py-3">
              <h2 className="text-sm font-bold">How it will look</h2>
              <div className="ml-auto flex flex-wrap items-center gap-2">
                <select className={`${selectCls} !h-8 !w-40 text-xs`} value={issueTitle} onChange={(e) => { setIssueTitle(e.target.value); setEditionId(""); }} aria-label="Title for the preview">
                  {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
                <div className="w-56"><ProposalIssuePicker titleId={issueTitle || null} value={editionId} onChange={(id) => setEditionId(id)} emptyLabel="No issue (example values)" /></div>
              </div>
            </div>
            <div className="max-h-[75vh] overflow-y-auto px-5 py-4">
              {preview ? <>
                <p className="text-sm"><span className="text-muted-foreground">Subject: </span><span className="font-semibold">{preview.subject || "(no subject)"}</span></p>
                <EmailBodyView body={preview.body} className="mt-3 border-t border-border/60 pt-3 text-sm leading-relaxed" />
                {preview.missing.length > 0 && <p className="mt-3 text-xs" style={{ color: "var(--warn)" }}>Nothing to fill in yet for: {preview.missing.map((k) => fields.find((f) => f.key === k)?.label ?? k).join(", ")}. Add a fallback like {"{{feature|our next feature}}"}, or fill in the brand&apos;s settings.</p>}
              </> : <p className="text-sm text-muted-foreground">The preview appears as you write.</p>}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
