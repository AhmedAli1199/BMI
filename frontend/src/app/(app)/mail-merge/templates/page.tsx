import Link from "next/link";
import { FileText, Mail } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { MailTemplate, MergeField } from "@/lib/messaging-types";
import type { SalesMeta } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";
import { TemplatesLibrary } from "@/components/mail-merge/templates-library";

/** The team's email templates: by brand, title and purpose, with merge fields for the contact, the brand's figures and the issue. */
export default async function TemplatesPage() {
  const [templates, fields, meta, session] = await Promise.all([
    backendFetch<MailTemplate[]>("/api/mail/templates").catch(() => [] as MailTemplate[]),
    backendFetch<MergeField[]>("/api/mail/fields").catch(() => [] as MergeField[]),
    backendFetch<SalesMeta>("/api/sales/meta").catch(() => null),
    getSession(),
  ]);
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary"><FileText className="size-3.5" /><span>Write</span></div>
          <h1 className="editorial-title text-2xl font-bold tracking-tight sm:text-3xl">Email templates</h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
            Pitches, follow-ups, event invitations and launches for each brand. The contact&apos;s name, the brand&apos;s figures (print run, email list, media pack)
            and the issue&apos;s date, deadline and feature are filled in for you, so one template works all year.
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" nativeButton={false} render={<Link href="/mail-merge" />}><Mail className="size-3.5" /> Mail merge</Button>
      </div>
      <TemplatesLibrary templates={templates} fields={fields} titles={meta?.titles ?? []} canLoad={canUseAutomations(session)} />
    </div>
  );
}
