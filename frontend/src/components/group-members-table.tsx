"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { X } from "lucide-react";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ClickableTableRow } from "@/components/clickable-table-row";
import { ContactSelectionActions } from "@/components/contact-selection-actions";
import { getGroupMembersPage, removeGroupMembers } from "@/lib/actions";
import type { GroupMember } from "@/lib/types";
import { friendlyError } from "@/lib/errors";
import { Badge } from "@/components/ui/badge";

/** The group member list, with multi-select bulk removal.
 *
 * BMI's #1 complaint about the old system: removing several contacts from
 * a group (routine before a mailing) meant removing them one at a time,
 * and every single removal reset their scroll position back to the top of
 * the list - on a long group, that turned a two-minute cleanup into
 * scrolling past the same hundred names over and over.
 *
 * Fixed two ways at once: the removal itself is one request for the whole
 * selection (see removeGroupMembers), and - just as important - this
 * component holds its own local copy of the member list and removes the
 * selected rows from it directly on success, rather than waiting on a
 * fresh server fetch. Nothing here ever re-renders the whole list from
 * scratch, so there's no scroll position to lose in the first place.
 */
export function GroupMembersTable({
  groupId,
  groupName,
  sourceDb,
  initialMembers,
  total,
  pageSize,
}: {
  groupId: string;
  groupName?: string;
  sourceDb?: string;
  initialMembers: GroupMember[];
  /** Everyone in the group and its sub-groups; the list loads a page at a time. */
  total?: number;
  pageSize?: number;
}) {
  const [members, setMembers] = useState(initialMembers);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pending, startTransition] = useTransition();
  const [loadingMore, startLoadingMore] = useTransition();
  const [removedCount, setRemovedCount] = useState(0);
  const remaining = Math.max(0, (total ?? members.length) - removedCount - members.length);

  function loadMore() {
    startLoadingMore(async () => {
      try {
        // Removed people are gone from the group, so the ones shown are exactly where the next lot starts.
        const next = await getGroupMembersPage(groupId, members.length);
        setMembers((prev) => {
          const have = new Set(prev.map((m) => m.id));
          return [...prev, ...next.filter((m) => !have.has(m.id))];
        });
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't load more members - try again"));
      }
    });
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === members.length ? new Set() : new Set(members.map((m) => m.id))));
  }

  function removeSelected() {
    const picked = members.filter((m) => selected.has(m.id));
    // People who are only in a sub-group have to be taken out of that sub-group.
    const ids = picked.filter((m) => !m.via_group_id).map((m) => m.id);
    const inSubGroups = picked.length - ids.length;
    if (ids.length === 0) {
      if (inSubGroups) toast.error(`${inSubGroups === 1 ? "That person is" : "Those people are"} in a sub-group, not this group itself - open the sub-group to remove them.`);
      return;
    }
    const gone = new Set(ids);
    startTransition(async () => {
      try {
        await removeGroupMembers(groupId, ids);
        setMembers((prev) => prev.filter((m) => !gone.has(m.id)));
        setRemovedCount((n) => n + ids.length);
        setSelected(new Set());
        toast.success(
          `Removed ${ids.length} ${ids.length === 1 ? "contact" : "contacts"} from the group` +
            (inSubGroups ? `. ${inSubGroups} in a sub-group ${inSubGroups === 1 ? "was" : "were"} left - open the sub-group to remove them.` : ""),
        );
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't remove those contacts - try again"));
      }
    });
  }

  if (members.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No members yet — add contacts to this group from their own contact page.
      </p>
    );
  }

  const allSelected = selected.size === members.length;
  const someSelected = selected.size > 0;

  return (
    <div className="flex flex-col gap-3">
      {someSelected ? (
        <ContactSelectionActions
          ids={[...selected]}
          onClear={() => setSelected(new Set())}
          sourceDb={sourceDb}
          excludeGroupId={groupId}
          label={`Group: ${groupName ?? "group"} – ${selected.size} selected`}
        >
          <Button variant="destructive" size="sm" className="h-7" onClick={removeSelected} disabled={pending}>
            <X className="size-3.5" />
            {pending ? "Removing…" : "Remove from this group"}
          </Button>
        </ContactSelectionActions>
      ) : (
        <p className="text-xs text-muted-foreground">
          Tick members to copy them into another group, start a new (smaller) group, export them, or remove
          them. To leave a few people out of one mailing only, untick them in the mail merge instead.
          {remaining > 0 && " Ticking the top box ticks only the members shown below."}
        </p>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8">
              <input
                type="checkbox"
                className="size-3.5"
                checked={allSelected}
                onChange={toggleAll}
                aria-label="Select all members"
              />
            </TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Job title</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.map((c) => (
            <ClickableTableRow key={c.id} href={`/contacts/${c.id}`}>
              <TableCell onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  className="size-3.5"
                  checked={selected.has(c.id)}
                  onChange={() => toggle(c.id)}
                  aria-label={`Select ${c.full_name || "this contact"}`}
                />
              </TableCell>
              <TableCell>
                <Link href={`/contacts/${c.id}`} className="hover:underline">
                  {c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "(no name)"}
                </Link>
                {c.via_group_id && (
                  <Link href={`/groups/${c.via_group_id}`} onClick={(e) => e.stopPropagation()} className="ml-2 inline-flex">
                    <Badge variant="outline" className="text-[10px] font-medium text-muted-foreground hover:text-foreground">
                      in {c.via_group_name || "a sub-group"}
                    </Badge>
                  </Link>
                )}
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
              <TableCell>{c.job_title || <span className="text-muted-foreground">—</span>}</TableCell>
            </ClickableTableRow>
          ))}
        </TableBody>
      </Table>
      {remaining > 0 && (
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>
            Showing {members.length.toLocaleString()} of {(members.length + remaining).toLocaleString()}
          </span>
          <Button variant="outline" size="sm" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? "Loading…" : `Show ${Math.min(remaining, pageSize ?? 200).toLocaleString()} more`}
          </Button>
        </div>
      )}
    </div>
  );
}
