"use client";

import { useState, useTransition } from "react";
import { GitMerge, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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
import { companyUsage, deleteCompanyChoosing, mergeCompany, searchCompaniesWithSimilar } from "@/lib/actions";
import { friendlyError } from "@/lib/errors";

type Usage = { contacts: number; bookings: number; deals: number; proposals: number };
const plural = (n: number, w: string) => `${n.toLocaleString()} ${w}${n === 1 ? "" : "s"}`;

/** Merge into another company, and Delete (Craig, feedback #11 and #12). Anyone who can see the company. */
export function CompanyDeleteMerge({ companyId, name }: { companyId: string; name: string }) {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [mode, setMode] = useState<"delete" | "merge" | null>(null);
  const [contacts, setContacts] = useState<"keep" | "delete">("keep");
  const [into, setInto] = useState<{ id: string; label: string } | null>(null);
  const [pending, start] = useTransition();

  function openAs(m: "delete" | "merge") {
    setMode(m);
    setUsage(null);
    setInto(null);
    setContacts("keep");
    companyUsage(companyId).then(setUsage).catch(() => setUsage({ contacts: 0, bookings: 0, deals: 0, proposals: 0 }));
  }

  const held = usage ? [usage.bookings && plural(usage.bookings, "booking"), usage.deals && plural(usage.deals, "deal"), usage.proposals && plural(usage.proposals, "proposal")].filter(Boolean) : [];

  function doDelete() {
    start(async () => {
      try {
        const r = await deleteCompanyChoosing(companyId, contacts);
        toast.success(
          `${name} deleted` + (r.contacts_deleted ? ` with ${plural(r.contacts_deleted, "contact")}` : r.contacts_kept ? ` - ${plural(r.contacts_kept, "contact")} kept, now without a company` : "")
        );
        // A full load, like DeleteEntityButton: the client cache can still hold the deleted company.
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.assign("/companies");
      } catch (e) {
        toast.error(friendlyError(e, "We couldn't delete the company. Please try again."));
      }
    });
  }

  function doMerge() {
    if (!into) return;
    start(async () => {
      try {
        const r = await mergeCompany(companyId, into.id);
        toast.success(`Merged into ${r.into_name}`);
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.assign(`/companies/${r.into_id}`);
      } catch (e) {
        toast.error(friendlyError(e, "We couldn't merge the companies. Please try again."));
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => openAs("merge")}>
        <GitMerge className="size-3.5" /> Merge into…
      </Button>
      <Button variant="outline" size="sm" className="gap-1.5 text-destructive hover:text-destructive" onClick={() => openAs("delete")}>
        <Trash2 className="size-3.5" /> Delete
      </Button>

      <Dialog open={mode === "delete"} onOpenChange={(o) => !o && setMode(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete {name}?</DialogTitle>
            <DialogDescription>It can&apos;t be undone. Its notes, history, addresses and phone numbers go with it.</DialogDescription>
          </DialogHeader>
          {!usage ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Checking what&apos;s linked to it…</p>
          ) : held.length ? (
            <p className="rounded-md bg-[color-mix(in_oklab,var(--warn)_12%,transparent)] px-3 py-2 text-sm">
              {name} has {held.join(", ")}, so it can&apos;t be deleted - that would lose sales history. If it&apos;s a duplicate, use
              <strong> Merge into…</strong> to move everything to the right company instead.
            </p>
          ) : usage.contacts === 0 ? (
            <p className="text-sm text-muted-foreground">No contacts are linked to it.</p>
          ) : (
            <fieldset className="flex flex-col gap-2 text-sm">
              <legend className="mb-1 font-medium">It has {plural(usage.contacts, "contact")}. What should happen to them?</legend>
              <label className="flex items-start gap-2">
                <input type="radio" name="contacts" className="mt-1 accent-primary" checked={contacts === "keep"} onChange={() => setContacts("keep")} />
                <span><strong>Keep them</strong> - they stay in the CRM with no company. (Recommended)</span>
              </label>
              <label className="flex items-start gap-2">
                <input type="radio" name="contacts" className="mt-1 accent-primary" checked={contacts === "delete"} onChange={() => setContacts("delete")} />
                <span><strong>Delete them too</strong> - with their notes, history and group memberships.</span>
              </label>
            </fieldset>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            {held.length ? (
              <Button onClick={() => openAs("merge")}><GitMerge className="size-4" /> Merge into…</Button>
            ) : (
              <Button variant="destructive" onClick={doDelete} disabled={pending || !usage}>
                {pending ? "Deleting…" : contacts === "delete" && usage?.contacts ? `Delete company and ${plural(usage.contacts, "contact")}` : "Delete company"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={mode === "merge"} onOpenChange={(o) => !o && setMode(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Merge {name} into another company</DialogTitle>
            <DialogDescription>
              For duplicates. Everything moves to the company you pick - contacts, notes, history, bookings, deals, proposals,
              addresses and phone numbers - and then {name} is deleted.
            </DialogDescription>
          </DialogHeader>
          <EntityPicker
            label="company"
            placeholder="Search for the company to keep…"
            value={into}
            onChange={setInto}
            viewHref={(id) => `/companies/${id}`}
            search={async (q) =>
              (await searchCompaniesWithSimilar(q))
                .filter((c) => c.id !== companyId)
                .map((c) => ({ id: c.id, label: c.name, sublabel: c.similar ? "similar name" : c.industry }))
            }
          />
          {usage && (
            <p className="text-xs text-muted-foreground">
              Moving: {[plural(usage.contacts, "contact"), plural(usage.bookings, "booking"), usage.deals ? plural(usage.deals, "deal") : null].filter(Boolean).join(", ")}.
            </p>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={doMerge} disabled={pending || !into}>{pending ? "Merging…" : into ? `Merge into ${into.label}` : "Merge"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
