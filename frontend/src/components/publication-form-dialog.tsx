"use client";

import { createElement, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
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
import { createPublication } from "@/lib/actions";
import { COLOR_OPTIONS, ICON_OPTIONS, iconForKey, styleForColor } from "@/lib/publication-style";

function slugify(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

/** "Add a database" - really: register a new source_db label. Never
 * creates an actual Postgres database; see
 * backend/app/models/publication.py. Once created it immediately shows
 * up in the publication switcher, quick filters, dashboard tiles, and as
 * a choice when adding a contact/company - all driven off the same
 * /api/publications list, nothing else needs touching. */
export function PublicationFormDialog() {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [description, setDescription] = useState("");
  const [color, setColor] = useState<string>(COLOR_OPTIONS[0]);
  const [icon, setIcon] = useState<string>(ICON_OPTIONS[0]);

  function handleNameChange(value: string) {
    setName(value);
    if (!slugTouched) setSlug(slugify(value));
  }

  function submit() {
    startTransition(async () => {
      try {
        await createPublication({ name, slug: slug || undefined, description: description || undefined, color, icon });
        toast.success(`${name} added`);
        setOpen(false);
        setName("");
        setSlug("");
        setSlugTouched(false);
        setDescription("");
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't add that database");
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Plus className="size-4" />
        Add database
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add a database</DialogTitle>
            <DialogDescription>
              A new title or list of your own — not a separate Postgres database, just a label every
              contact/company can be filed under, exactly like OnBoard, Selling Travel, and Prospects
              already are.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pub-name">Name</Label>
              <Input
                id="pub-name"
                placeholder="e.g. Airline Retail Weekly"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pub-slug">
                Internal key <span className="font-normal text-muted-foreground">(auto-filled, rarely needs changing)</span>
              </Label>
              <Input
                id="pub-slug"
                value={slug}
                onChange={(e) => {
                  setSlugTouched(true);
                  setSlug(slugify(e.target.value));
                }}
              />
              <p className="text-[11px] text-muted-foreground">
                Permanent once created — every contact/company filed under it stores this exact value.
              </p>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pub-desc">Description</Label>
              <Input
                id="pub-desc"
                placeholder="What this covers, shown under its name everywhere"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label>Color</Label>
              <div className="flex flex-wrap gap-2">
                {COLOR_OPTIONS.map((c) => {
                  const s = styleForColor(c);
                  const isSelected = c === color;
                  return (
                    <button
                      key={c}
                      type="button"
                      title={c}
                      onClick={() => setColor(c)}
                      className={`flex size-8 items-center justify-center rounded-full border-2 transition-transform ${
                        isSelected ? "scale-110 border-foreground" : "border-transparent hover:scale-105"
                      }`}
                    >
                      <span className={`size-6 rounded-full ${s.dot}`} />
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label>Icon</Label>
              <div className="flex flex-wrap gap-2">
                {ICON_OPTIONS.map((key) => {
                  const Icon = iconForKey(key);
                  const isSelected = key === icon;
                  return (
                    <button
                      key={key}
                      type="button"
                      title={key}
                      onClick={() => setIcon(key)}
                      className={`flex size-9 items-center justify-center rounded-lg border transition-colors ${
                        isSelected ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:bg-accent/40"
                      }`}
                    >
                      <Icon className="size-4" />
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Live preview so a non-technical picker isn't guessing what
                the tile will actually look like on the dashboard. */}
            <div className="flex items-center gap-3 rounded-lg border border-border/70 bg-muted/30 p-3">
              <PublicationIconChip icon={icon} color={color} />
              <div className="min-w-0">
                <div className="truncate text-sm font-bold text-foreground">{name || "Database name"}</div>
                <div className="truncate text-xs text-muted-foreground">{description || "Description preview"}</div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !name.trim() || !slug.trim()}>
              {pending ? "Adding…" : "Add database"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function PublicationIconChip({ icon, color }: { icon: string; color: string }) {
  const style = styleForColor(color);
  return (
    <span className={`flex size-9 shrink-0 items-center justify-center rounded-lg border ${style.chipBg}`}>
      {createElement(iconForKey(icon), { className: "size-4" })}
    </span>
  );
}
