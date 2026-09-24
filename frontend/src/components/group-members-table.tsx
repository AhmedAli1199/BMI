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
import { removeGroupMembers } from "@/lib/actions";
import type { ContactListItem } from "@/lib/types";

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
  initialMembers,
}: {
  groupId: string;
  initialMembers: ContactListItem[];
}) {
  const [members, setMembers] = useState(initialMembers);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pending, startTransition] = useTransition();

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
    const ids = [...selected];
    if (ids.length === 0) return;
    startTransition(async () => {
      try {
        await removeGroupMembers(groupId, ids);
        setMembers((prev) => prev.filter((m) => !selected.has(m.id)));
        setSelected(new Set());
        toast.success(`Removed ${ids.length} ${ids.length === 1 ? "contact" : "contacts"} from the group`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't remove those contacts - try again");
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
      {someSelected && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-accent/40 px-3 py-2">
          <span className="text-sm font-medium">
            {selected.size} selected
          </span>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())} disabled={pending}>
              Clear
            </Button>
            <Button variant="destructive" size="sm" onClick={removeSelected} disabled={pending}>
              <X className="size-3.5" />
              {pending ? "Removing…" : `Remove ${selected.size} selected`}
            </Button>
          </div>
        </div>
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
    </div>
  );
}
