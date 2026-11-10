"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EntityPicker } from "@/components/entity-picker";
import { addContactToGroup, browseGroups, removeContactFromGroup, searchGroups } from "@/lib/actions";

export function ContactGroupsEditor({
  contactId,
  groups,
  sourceDb,
}: {
  contactId: string;
  groups: { id: string; name: string }[];
  /** The contact's database: its groups are listed first when the picker opens. */
  sourceDb?: string | null;
}) {
  const memberOf = new Set(groups.map((g) => g.id));
  const asOption = (g: { id: string; name: string; member_count: number; hier_level: number | null }) => ({
    id: g.id,
    label: g.name,
    sublabel: memberOf.has(g.id) ? "already in this group" : `${g.member_count.toLocaleString()} member${g.member_count === 1 ? "" : "s"}`,
    indent: Math.max(0, (g.hier_level ?? 1) - 1),
    disabled: memberOf.has(g.id),
  });
  const [adding, setAdding] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function remove(groupId: string) {
    startTransition(async () => {
      try {
        await removeContactFromGroup(contactId, groupId);
        router.refresh();
      } catch {
        toast.error("Couldn't remove from group");
      }
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {groups.map((g) => (
          <Badge key={g.id} className="gap-1 pr-1">
            {g.name}
            <button
              type="button"
              onClick={() => remove(g.id)}
              disabled={pending}
              className="rounded-full p-0.5 hover:bg-foreground/10"
              aria-label={`Remove from ${g.name}`}
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        {groups.length === 0 && !adding && (
          <span className="text-sm text-muted-foreground">No group memberships.</span>
        )}
      </div>
      {adding ? (
        <div className="max-w-xs">
          <EntityPicker
            label="group"
            placeholder="Pick a group, or type to search…"
            search={async (q) => (await searchGroups(q)).map(asOption)}
            browse={async () => {
              const { items, total } = await browseGroups(sourceDb);
              return {
                options: items.map(asOption),
                note: total > items.length ? `Showing ${items.length} of ${total.toLocaleString()} groups - type to find the rest.` : undefined,
              };
            }}
            value={null}
            onChange={(v) => {
              if (!v) return;
              setAdding(false);
              startTransition(async () => {
                try {
                  await addContactToGroup(contactId, v.id);
                  router.refresh();
                } catch {
                  toast.error("Couldn't add to group");
                }
              });
            }}
          />
        </div>
      ) : (
        <Button variant="outline" size="sm" className="w-fit" onClick={() => setAdding(true)}>
          <Plus className="size-4" />
          Add to group
        </Button>
      )}
    </div>
  );
}
