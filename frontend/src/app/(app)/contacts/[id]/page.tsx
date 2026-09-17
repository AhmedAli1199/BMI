import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactDetail, GroupListItem, Page, RecordPosition } from "@/lib/types";
import { getSession } from "@/lib/session";
import { canAccessRecord } from "@/lib/access";
import { sourceLabel } from "@/lib/sources";
import { ActSubbar } from "@/components/act-subbar";
import { ActContactCard } from "@/components/act-contact-card";
import { ActTabWorkstation } from "@/components/act-tab-workstation";

export default async function ContactDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ q?: string; source_db?: string; group_id?: string }>;
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
  if (navParams.q) posParams.set("q", navParams.q);
  if (navParams.source_db) posParams.set("source_db", navParams.source_db);
  if (navParams.group_id) posParams.set("group_id", navParams.group_id);
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

  return (
    <div className="flex w-full flex-col">
      {/* ACT! Sub-header Navigation & Action Ribbon */}
      <ActSubbar
        module="contacts"
        currentRecordIndex={position?.position ?? undefined}
        totalRecords={position?.total}
        firstHref={position && position.position && position.position > 1 ? hrefFor(position.first_id) : null}
        prevHref={hrefFor(position?.prev_id ?? null)}
        nextHref={hrefFor(position?.next_id ?? null)}
        lastHref={
          position && position.position && position.position < position.total ? hrefFor(position.last_id) : null
        }
      />

      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-4 sm:p-6">
        {/* Editorial Breadcrumb & Status */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex items-center gap-2">
            <Link
              href="/contacts"
              className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="size-3.5" />
              <span>Back to Contacts</span>
            </Link>
            <span className="text-muted-foreground/50">/</span>
            <span className="text-xs font-medium text-muted-foreground">
              {sourceLabel(contact.source_db)}
            </span>
            <span className="text-muted-foreground/50">/</span>
            <span className="text-xs font-bold text-foreground truncate max-w-[240px]">
              {name}
            </span>
          </div>
        </div>

        {/* Tier 1: ACT! Authentic 3-Column Upper Form Card */}
        <ActContactCard contact={contact} />

        {/* Tier 2: ACT! Full-Width Bottom Sub-Workstation Tabs */}
        <ActTabWorkstation contact={contact} />
      </div>
    </div>
  );
}
