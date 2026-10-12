"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, Copy, Mail, Pencil, Plus } from "lucide-react";
import type { MailTemplate } from "@/lib/messaging-types";
import { BRAND_LABEL, TEMPLATE_KIND_LABEL } from "@/lib/messaging-types";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import { htmlToText } from "@/lib/rich-text";
import { ClientDataView } from "@/components/data-view/client-data-view";
import { DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips } from "@/components/data-view/toolbar";
import { Button } from "@/components/ui/button";
import { EmailFromTemplate } from "@/components/mail-merge/email-from-template";
import { fmtDate } from "@/components/sales/sales-ui";

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

export function TemplatesLibrary({ templates }: { templates: MailTemplate[] }) {
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
              <Button size="sm" className="gap-1.5" nativeButton={false} render={<Link href="/mail-merge/templates/new" />}>
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
                {templates.length ? "No templates match these filters." : "No templates yet. Write the first one."}
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
                    <p className="mt-1 line-clamp-3 whitespace-pre-line text-xs text-muted-foreground">{htmlToText(t.body)}</p>
                    {t.description && <p className="mt-2 text-[11px] italic text-muted-foreground">{t.description}</p>}
                    <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-3">
                      <Button size="xs" className="gap-1" onClick={() => setUseT(t)}><Mail className="size-3" /> Email someone</Button>
                      {t.can_edit && <Button size="xs" variant="outline" className="gap-1" nativeButton={false} render={<Link href={`/mail-merge/templates/${t.id}`} />}><Pencil className="size-3" /> Change</Button>}
                      <Button size="xs" variant="ghost" className="gap-1" nativeButton={false} render={<Link href={`/mail-merge/templates/new?copy=${t.id}`} />}><Copy className="size-3" /> Copy</Button>
                      <span className="ml-auto text-[11px] text-muted-foreground">{t.owner_name ? `${t.owner_name} · ` : ""}{t.use_count ? `used ${t.use_count}×` : "not used yet"}{t.last_used_at ? `, last ${fmtDate(t.last_used_at.slice(0, 10))}` : ""}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </DataViewLayout>
        )}
      </ClientDataView>

      {useT && <EmailFromTemplate open={!!useT} onOpenChange={(o) => !o && setUseT(null)} templates={[useT]} initialTemplateId={useT.id} />}
    </>
  );
}
