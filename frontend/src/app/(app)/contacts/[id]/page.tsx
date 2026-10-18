import Link from "next/link";
import { EmailTemplateButton } from "@/components/mail-merge/email-template-button";
import { notFound } from "next/navigation";
import { Mail } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactDetail, GroupListItem, Page, RecordPosition } from "@/lib/types";
import { getSession } from "@/lib/session";
import { canAccessRecord } from "@/lib/access";
import { sourceBadgeStyle, sourceLabel } from "@/lib/sources";
import { PageHeader } from "@/components/page-header";
import { RecordPager } from "@/components/record-pager";
import { Badge } from "@/components/ui/badge";
import { ActContactCard } from "@/components/act-contact-card";
import { ActTabWorkstation } from "@/components/act-tab-workstation";
import { FieldChangeHistory } from "@/components/field-change-history";
import { getContactFieldChanges } from "@/lib/actions";
import { Button } from "@/components/ui/button";
import { RemindMeDialog } from "@/components/remind-me-dialog";
import { DuplicateContactDialog } from "@/components/duplicate-contact-dialog";
import { RecordReminders } from "@/components/record-reminders";
import type { Reminder } from "@/lib/messaging-types";

export default async function ContactDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const { id } = await params;
  const navParams = await searchParams;

  let contact: ContactDetail;
  try {
    contact = await backendFetch<ContactDetail>(`/api/contacts/${id}`);
  } catch {
    notFound();
  }

  // Record-stepper (VCR arrows) - walks the same filtered/sorted list the
  // user navigated in from (carried via the query string, see
  // InteractiveContactTable's `queryString` prop), not some other order.
  // Best-effort: if it fails, the stepper just shows disabled arrows.
  const posParams = new URLSearchParams();
  for (const k of ["q", "source_db", "group_id", "company", "city", "country", "title", "sort", "desc"]) {
    const v = navParams[k];
    if (v) posParams.set(k, v);
  }
  const position = await backendFetch<RecordPosition>(
    `/api/contacts/${id}/position?${posParams}`
  ).catch(() => undefined);
  const navSuffix = posParams.toString() ? `?${posParams}` : "";
  const hrefFor = (recordId: string | null) => (recordId ? `/contacts/${recordId}${navSuffix}` : null);

  // Defense in depth - the list page already only links to contacts
  // within a session's scope, but a direct/guessed URL must be rejected
  // too, not just hidden from the list. A group-scoped grant needs the
  // record's group memberships checked against the grant's subtree, not
  // just the database - fetched only when actually needed (an admin or
  // full-database grant never hits this).
  const session = await getSession();
  const grant = session?.role === "admin" ? null : session?.access.find((a) => a.source_db === contact.source_db);
  const needsGroupCheck = grant?.group_id != null;
  const subtreeGroupIds = needsGroupCheck
    ? (await backendFetch<Page<GroupListItem>>(
        `/api/groups?root_group_id=${grant!.group_id}&page_size=500`
      )).items.map((g) => g.id)
    : null;
  if (!canAccessRecord(session, contact.source_db, contact.groups.map((g) => g.id), subtreeGroupIds)) {
    notFound();
  }

  const name =
    contact.full_name ||
    [contact.first_name, contact.last_name].filter(Boolean).join(" ") ||
    "(no name)";
  const reminders = await backendFetch<Reminder[]>(`/api/reminders?contact_id=${contact.id}`).catch(() => [] as Reminder[]);

  return (
    <div className="flex w-full flex-col">
      {/* ACT! Sub-header Navigation & Action Ribbon */}
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-4 sm:p-6">
        <PageHeader
          crumbs={[{ label: "Contacts", href: "/contacts" }]}
          title={name}
          below={
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              {contact.job_title && <span>{contact.job_title}</span>}
              {contact.job_title && contact.company && <span aria-hidden="true">·</span>}
              {contact.company && <Link href={`/companies/${contact.company.id}`} className="font-semibold text-primary hover:underline">{contact.company.name}</Link>}
              <Badge variant="outline" className={`text-[11px] font-medium ${sourceBadgeStyle(contact.source_db)}`}>{sourceLabel(contact.source_db)}</Badge>
              {contact.has_left && <Badge variant="outline" className="text-[11px] font-medium text-muted-foreground">Left the company</Badge>}
            </div>
          }
          actions={<>
            <RemindMeDialog contactId={contact.id} about={name} />
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              nativeButton={false}
              render={<Link href={`/mail-merge?contact=${contact.id}`} />}
            >
              <Mail className="size-3.5" />
              Write
            </Button>
            <EmailTemplateButton contact={{ id: contact.id, label: name }} />
            <DuplicateContactDialog
              contactId={contact.id}
              name={name}
              companyName={contact.company?.name}
              jobTitle={contact.job_title}
            />
            <RecordPager noun="contact" position={position?.position} total={position?.total}
              prevHref={hrefFor(position?.prev_id ?? null)} nextHref={hrefFor(position?.next_id ?? null)} />
          </>}
        />

        <RecordReminders reminders={reminders} />

                <ActContactCard contact={contact} />

        <FieldChangeHistory entityId={contact.id} fetchChanges={getContactFieldChanges} />

                <ActTabWorkstation contact={contact} />
      </div>
    </div>
  );
}
