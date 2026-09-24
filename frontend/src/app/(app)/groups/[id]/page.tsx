import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { GroupDetail, GroupListItem, Page } from "@/lib/types";
import { getSession } from "@/lib/session";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GroupMembersTable } from "@/components/group-members-table";
import { GroupFormDialog } from "@/components/group-form-dialog";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { deleteGroup } from "@/lib/actions";

export default async function GroupDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let group: GroupDetail;
  try {
    group = await backendFetch<GroupDetail>(`/api/groups/${id}`);
  } catch {
    notFound();
  }

  // Defense in depth against a guessed/direct URL - a group-scoped grant
  // must only let someone open their own group's subtree, not any group
  // in the database.
  const session = await getSession();
  const grant = session?.role === "admin" ? null : session?.access.find((a) => a.source_db === group.source_db);
  if (session && session.role !== "admin") {
    if (!grant) notFound();
    else if (grant.group_id) {
      const subtree = await backendFetch<Page<GroupListItem>>(
        `/api/groups?root_group_id=${grant.group_id}&page_size=500`
      );
      if (!subtree.items.some((g) => g.id === group.id)) notFound();
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{group.name}</h1>
          {group.description && <p className="text-sm text-muted-foreground">{group.description}</p>}
        </div>
        <div className="flex shrink-0 gap-2">
          <GroupFormDialog existing={group} />
          <DeleteEntityButton entityLabel={group.name} id={group.id} action={deleteGroup} redirectTo="/groups" />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Members ({group.members.length.toLocaleString()})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <GroupMembersTable groupId={group.id} initialMembers={group.members} />
        </CardContent>
      </Card>
    </div>
  );
}
