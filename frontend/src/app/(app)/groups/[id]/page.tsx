import Link from "next/link";
import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { GroupDetail } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClickableTableRow } from "@/components/clickable-table-row";
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
          {group.members.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Job title</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {group.members.map((c) => (
                  <ClickableTableRow key={c.id} href={`/contacts/${c.id}`}>
                    <TableCell>
                      <Link href={`/contacts/${c.id}`} className="hover:underline">
                        {c.full_name ||
                          [c.first_name, c.last_name].filter(Boolean).join(" ") ||
                          "(no name)"}
                      </Link>
                    </TableCell>
                    <TableCell>
                      {c.company_id ? (
                        <Link href={`/companies/${c.company_id}`} className="hover:underline">
                          {c.company_name}
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {c.job_title || <span className="text-muted-foreground">—</span>}
                    </TableCell>
                  </ClickableTableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">
              No members yet — add contacts to this group from their own contact page.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
