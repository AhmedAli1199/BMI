import Link from "next/link";
import { FileText, History, Mail } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { MailStatus, MailTemplate, MergeField, RecipientSource } from "@/lib/messaging-types";import { MailMergeWizard, type InitialSource } from "@/components/mail-merge/mail-merge-wizard";
import type { CompanyDetail, ContactDetail, GroupDetail } from "@/lib/types";
import type { SalesTitle } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";

/** Act!'s Write > Mail Merge. Arrives with its contacts already chosen from
 * wherever it was opened (a contact, a company, a group, the current
 * lookup or a ticked selection) - all changeable in step 2. */
export default async function MailMergePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const [status, fields, templates, meta] = await Promise.all([
    backendFetch<MailStatus>("/api/mail/status").catch(() => null),
    backendFetch<MergeField[]>("/api/mail/fields").catch(() => [] as MergeField[]),
    backendFetch<MailTemplate[]>("/api/mail/templates").catch(() => [] as MailTemplate[]),
    backendFetch<{ titles: SalesTitle[] }>("/api/sales/meta").catch(() => ({ titles: [] as SalesTitle[] })),
  ]);

  let initial: InitialSource = { source: null, label: "" };
  if (sp.source === "lookup") {
    // `company_name` (not `company`, which is a company id below) = the
    // lookup's "company contains" field.
    const src: RecipientSource = {
      kind: "lookup",
      q: sp.q,
      source_db: sp.source_db,
      company: sp.company_name,
      city: sp.city,
      country: sp.country,
      title: sp.title,
      sort: sp.sort,
      desc: sp.desc === "1" || sp.desc === "true",
      conds: sp.conds,
      match: sp.match,
    };
    initial = { source: src, label: "Current lookup" };
  } else if (sp.contact) {
    const c = await backendFetch<ContactDetail>(`/api/contacts/${sp.contact}`).catch(() => null);
    if (c) {
      const name = c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "this contact";
      initial = { source: { kind: "contacts", contact_ids: [c.id] }, label: name };
    }
  } else if (sp.company) {
    const co = await backendFetch<CompanyDetail>(`/api/companies/${sp.company}`).catch(() => null);
    if (co) initial = { source: { kind: "company", company_id: co.id }, label: co.name };
  } else if (sp.group) {
    const g = await backendFetch<GroupDetail>(`/api/groups/${sp.group}`).catch(() => null);
    if (g) initial = { source: { kind: "group", group_id: g.id }, label: g.name };
  } else if (sp.source === "selection") {
    initial = { source: null, label: "", fromSelection: true };
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-4">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <Mail className="size-3.5" />
            <span>Write</span>
          </div>
          <h1 className="editorial-title text-2xl font-bold tracking-tight sm:text-3xl">Mail merge</h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
            One personalised message to many people - as emails from your own Outlook, Word letters, address
            labels, or a data file for Mailchimp.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/mail-merge/templates" />}>
            <FileText className="size-3.5" />
            Email templates
          </Button>
          <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/mail-merge/history" />}>
            <History className="size-3.5" />
            Sent mail merges
          </Button>
        </div>
      </div>

      <MailMergeWizard status={status} fields={fields} templates={templates} initial={initial} titles={meta.titles} />
    </div>
  );
}
