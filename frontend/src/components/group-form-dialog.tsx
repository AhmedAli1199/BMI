"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus, Pencil } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { createGroup, listPublications, updateGroup } from "@/lib/actions";
import { iconForKey, styleForColor } from "@/lib/publication-style";
import type { Publication } from "@/lib/types";

type Existing = { id: string; name: string; description: string | null };

export function GroupFormDialog({ existing, defaultSourceDb }: { existing?: Existing; defaultSourceDb?: string }) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  const [name, setName] = useState(existing?.name ?? "");
  const [description, setDescription] = useState(existing?.description ?? "");
  const [publications, setPublications] = useState<Publication[]>([]);
  const [sourceDb, setSourceDb] = useState(defaultSourceDb ?? "");

  useEffect(() => {
    if (existing || open === false) return;
    listPublications().then((pubs) => {
      setPublications(pubs);
      if (!sourceDb && pubs.length > 0) setSourceDb(defaultSourceDb || pubs[0].slug);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function submit() {
    startTransition(async () => {
      try {
        if (existing) {
          await updateGroup(existing.id, { name, description });
          toast.success("Group updated");
          setOpen(false);
          router.refresh();
        } else {
          const created = await createGroup({ name, description, source_db: sourceDb });
          toast.success("Group created");
          setOpen(false);
          router.push(`/groups/${created.id}`);
        }
      } catch {
        toast.error(existing ? "Couldn't update group" : "Couldn't create group");
      }
    });
  }

  return (
    <>
      {existing ? (
        <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
          <Pencil className="size-4" />
          Edit
        </Button>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plus className="size-4" />
          New group
        </Button>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{existing ? "Edit group" : "New group"}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            {!existing && publications.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <Label>Database</Label>
                <div className="flex flex-wrap gap-1.5">
                  {publications.map((pub) => {
                    const style = styleForColor(pub.color);
                    const Icon = iconForKey(pub.icon);
                    const isSelected = sourceDb === pub.slug;
                    return (
                      <button
                        key={pub.slug}
                        type="button"
                        onClick={() => setSourceDb(pub.slug)}
                        className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                          isSelected ? `${style.chipBg} border-current` : "border-border text-muted-foreground hover:bg-accent/40"
                        }`}
                      >
                        <Icon className="size-3.5" />
                        {pub.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="gf-name">Name</Label>
              <Input id="gf-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="gf-desc">Description</Label>
              <Input id="gf-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !name.trim()}>
              {pending ? "Saving…" : existing ? "Save changes" : "Create group"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
