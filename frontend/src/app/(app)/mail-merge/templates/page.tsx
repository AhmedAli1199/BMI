import Link from "next/link";
import { Mail } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { MailTemplate } from "@/lib/messaging-types";
import { Button } from "@/components/ui/button";
import { TemplatesLibrary } from "@/components/mail-merge/templates-library";
import { PageHeader } from "@/components/page-header";
import { LoadActTemplatesButton } from "@/components/mail-merge/load-act-templates-button";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";

/** The team's email templates: by brand, title and purpose, with merge fields for the contact, the brand's figures and the issue. */
export default async function TemplatesPage() {
  const [templates, session] = await Promise.all([
    backendFetch<MailTemplate[]>("/api/mail/templates").catch(() => [] as MailTemplate[]),
    getSession(),
  ]);
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Email templates"
        section="Outreach"
        description="Pitches, follow-ups, invitations and launches for each brand. Names, brand figures and issue details are filled in for you, so one template works all year."
        actions={<>
          {/* Administrators and data managers only - the server checks this too. */}
          {canUseAutomations(session) && <LoadActTemplatesButton />}
          <Button variant="outline" size="sm" className="gap-1.5" nativeButton={false} render={<Link href="/mail-merge" />}><Mail className="size-3.5" /> Mail merge</Button>
        </>}
      />
      <TemplatesLibrary templates={templates} />
    </div>
  );
}
