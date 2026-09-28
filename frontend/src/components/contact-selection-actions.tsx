"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Download, FolderPlus, Mail, Plus, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EntityPicker } from "@/components/entity-picker";
import { searchGroups } from "@/lib/actions";
import { addContactsToGroup, createGroupWithMembers } from "@/lib/messaging-actions";
import { downloadFile, postJson, stashMergeSelection } from "@/lib/download";

type Option = { id: string; label: string; sublabel?: string | null };

/** The action bar shown while contacts are ticked - on the contacts
 * lookup and inside a group. Builds smaller groups out of big ones
 * (Act!'s "copy to group"), exports the selection, or mail-merges it. */
export function ContactSelectionActions({
  ids,
  onClear,
  sourceDb,
  label = "Selected contacts",
  excludeGroupId,
  children,
}: {
  ids: string[];
  onClear: () => void;
  sourceDb?: string;
  /** Describes the selection in mail-merge / export ("Group: Buyers - 12 selected"). */
  label?: string;
  excludeGroupId?: string;
  children?: React.ReactNode;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [addOpen, setAddOpen] = useState(false);
  const [newOpen, setNewOpen] = useState(false);
  const [group, setGroup] = useState<Option | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const n = ids.length;
  const noun = n === 1 ? "contact" : "contacts";

  function addToGroup() {
    if (!group) return;
    startTransition(async () => {
      try {
        const r = await addContactsToGroup(group.id, ids);
        toast.success(
          `Added ${r.added} to ${group.label}` + (r.already_members ? ` (${r.already_members} already in it)` : ""),
          { action: { label: "Open group", onClick: () => router.push(`/groups/${group.id}`) } }
        );
        setAddOpen(false);
        setGroup(null);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't add them to that group");
      }
    });
  }

  function createGroup() {
    startTransition(async () => {
      try {
        const g = await createGroupWithMembers({
          name: name.trim(),
          description: description.trim() || undefined,
          source_db: sourceDb || undefined,
          contact_ids: ids,
        });
        toast.success(`Created “${g.name}” with ${n} ${noun}`, {
          action: { label: "Open group", onClick: () => router.push(`/groups/${g.id}`) },
        });
        setNewOpen(false);
        setName("");
        setDescription("");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't create the group");
      }
    });
  }

  function exportSelection() {
    startTransition(async () => {
      try {
        await downloadFile("/api/files/contacts/export", "contacts.xlsx", postJson({ ids, title: label }));
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Export failed");
      }
    });
  }

  function mailMerge() {
    stashMergeSelection(ids, label);
    router.push("/mail-merge?source=selection");
  }

  return (
    <>
      <div
        role="toolbar"
        aria-label="Selected contacts"
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2"
      >
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-semibold">
            {n.toLocaleString()} {noun} selected
          </span>
          {children}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Button size="sm" variant="outline" onClick={() => setAddOpen(true)} disabled={pending}>
            <FolderPlus className="size-3.5" />
            Add to group
          </Button>
          <Button size="sm" variant="outline" onClick={() => setNewOpen(true)} disabled={pending}>
            <Plus className="size-3.5" />
            New group
          </Button>
          <Button size="sm" variant="outline" onClick={exportSelection} disabled={pending}>
            <Download className="size-3.5" />
            Export
          </Button>
          <Button size="sm" onClick={mailMerge} disabled={pending}>
            <Mail className="size-3.5" />
            Mail merge
          </Button>
          <Button size="sm" variant="ghost" onClick={onClear} disabled={pending} aria-label="Clear selection">
            <X className="size-3.5" />
          </Button>
        </div>
      </div>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add {n.toLocaleString()} {noun} to a group</DialogTitle>
            <DialogDescription>
              Anyone already in the group is left as they are. They stay in any groups they&apos;re already in.
            </DialogDescription>
          </DialogHeader>
          <EntityPicker
            label="Group"
            placeholder="Search groups…"
            value={group}
            onChange={setGroup}
            search={async (q) =>
              (await searchGroups(q))
                .filter((g) => g.id !== excludeGroupId)
                .map((g) => ({ id: g.id, label: g.name, sublabel: `${g.member_count.toLocaleString()} members` }))
            }
          />
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={addToGroup} disabled={pending || !group}>
              {pending ? "Adding…" : "Add to group"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New group from {n.toLocaleString()} {noun}</DialogTitle>
            <DialogDescription>
              Handy for a one-off mailing: build a smaller group from a big one, send to it, delete it afterwards.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ng-name">Group name</Label>
              <Input
                id="ng-name"
                value={name}
                placeholder="e.g. Onboard buyers – October mailing"
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ng-desc">Description (optional)</Label>
              <Input id="ng-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={createGroup} disabled={pending || !name.trim()}>
              {pending ? "Creating…" : "Create group"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
