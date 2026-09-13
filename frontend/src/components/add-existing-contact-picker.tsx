"use client";

import { useState, useTransition } from "react";
import { UserPlus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EntityPicker } from "@/components/entity-picker";
import { searchContacts, updateContact } from "@/lib/actions";

/** Links an existing contact to this company (sets their company_id) -
 * distinct from "New contact", which creates a brand new person. Answers
 * the ask for "adding a contact to a company" when the person is already
 * in the CRM under a different or no company. */
export function AddExistingContactPicker({ companyId, companyName }: { companyId: string; companyName: string }) {
  const [open, setOpen] = useState(false);
  const [contact, setContact] = useState<{ id: string; label: string } | null>(null);
  const [pending, startTransition] = useTransition();

  function save() {
    if (!contact) return;
    startTransition(async () => {
      try {
        await updateContact(contact.id, { company_id: companyId });
        toast.success(`Added ${contact.label} to ${companyName}`);
        setContact(null);
        setOpen(false);
      } catch {
        toast.error("Couldn't add contact to company");
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <UserPlus className="size-4" />
        Add existing contact
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add existing contact to {companyName}</DialogTitle>
          </DialogHeader>
          <EntityPicker
            label="contact"
            placeholder="Search contacts by name or email…"
            search={async (q) =>
              (await searchContacts(q)).map((c) => ({
                id: c.id,
                label: c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "(no name)",
                sublabel: c.company_name,
              }))
            }
            value={contact}
            onChange={setContact}
          />
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={save} disabled={pending || !contact}>
              {pending ? "Adding…" : "Add to company"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
