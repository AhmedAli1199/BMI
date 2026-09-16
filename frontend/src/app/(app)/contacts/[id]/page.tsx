import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactDetail, GroupListItem, Page } from "@/lib/types";
import { getSession } from "@/lib/session";
import { canAccessRecord } from "@/lib/access";
import { Badge } from "@/components/ui/badge";
import { sourceLabel } from "@/lib/sources";
import { ActSubbar } from "@/components/act-subbar";
import { ActContactCard } from "@/components/act-contact-card";
import { ActTabWorkstation } from "@/components/act-tab-workstation";

export default async function ContactDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let contact: ContactDetail;
  try {
    contact = await backendFetch<ContactDetail>(`/api/contacts/${id}`);
  } catch {
    notFound();
  }

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
      <ActSubbar module="contacts" />

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

          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[11px] font-mono">
              {contact.source_act_id || `ID: ${contact.id.slice(0, 8)}`}
            </Badge>
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
