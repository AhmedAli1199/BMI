"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Copy } from "lucide-react";
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
import { duplicateContact } from "@/lib/messaging-actions";
import { friendlyError } from "@/lib/errors";

/** Act!'s "Duplicate contact": a new person at the same company - keeps
 * the company, business address, main phone, database and (optionally)
 * groups; asks only for what's different about the new person. */
export function DuplicateContactDialog({
  contactId,
  name,
  companyName,
  jobTitle,
}: {
  contactId: string;
  name: string;
  companyName?: string | null;
  jobTitle?: string | null;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");
  const [email, setEmail] = useState("");
  const [title, setTitle] = useState(jobTitle ?? "");
  const [phone, setPhone] = useState("");
  const [copyGroups, setCopyGroups] = useState(true);

  function save() {
    startTransition(async () => {
      try {
        const c = await duplicateContact(contactId, {
          first_name: first.trim() || undefined,
          last_name: last.trim() || undefined,
          email: email.trim() || undefined,
          job_title: title.trim() || undefined,
          phone: phone.trim() || undefined,
          copy_groups: copyGroups,
        });
        toast.success("Contact created from a copy");
        setOpen(false);
        router.push(`/contacts/${c.id}`);
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't duplicate this contact"));
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setOpen(true)}>
        <Copy className="size-3.5" />
        Duplicate
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Duplicate {name}</DialogTitle>
            <DialogDescription>
              Creates a new contact{companyName ? ` at ${companyName}` : ""} with the same company, business
              address, main phone and database. Enter the new person&apos;s details.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="dup-first">First name</Label>
              <Input id="dup-first" value={first} onChange={(e) => setFirst(e.target.value)} autoFocus />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="dup-last">Last name</Label>
              <Input id="dup-last" value={last} onChange={(e) => setLast(e.target.value)} />
            </div>
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="dup-email">Email</Label>
              <Input id="dup-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="dup-title">Job title</Label>
              <Input id="dup-title" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="dup-phone">Direct phone</Label>
              <Input id="dup-phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <label className="col-span-2 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={copyGroups}
                onChange={(e) => setCopyGroups(e.target.checked)}
              />
              Put them in the same groups
            </label>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={save} disabled={pending || !(first.trim() || last.trim())}>
              {pending ? "Creating…" : "Create contact"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
