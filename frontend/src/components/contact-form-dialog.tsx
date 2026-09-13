"use client";

import { useState, useTransition } from "react";
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
import { EntityPicker } from "@/components/entity-picker";
import { createContact, searchCompanies, updateContact, type ContactFormInput } from "@/lib/actions";

type Existing = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  job_title: string | null;
  department: string | null;
  company: { id: string; name: string } | null;
};

export function ContactFormDialog({ existing }: { existing?: Existing }) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  const [firstName, setFirstName] = useState(existing?.first_name ?? "");
  const [lastName, setLastName] = useState(existing?.last_name ?? "");
  const [jobTitle, setJobTitle] = useState(existing?.job_title ?? "");
  const [department, setDepartment] = useState(existing?.department ?? "");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState<{ id: string; label: string } | null>(
    existing?.company ? { id: existing.company.id, label: existing.company.name } : null
  );

  function submit() {
    const payload: ContactFormInput = {
      first_name: firstName,
      last_name: lastName,
      job_title: jobTitle,
      department,
      company_id: company?.id ?? null,
      ...(existing ? {} : { email, phone }),
    };
    startTransition(async () => {
      try {
        if (existing) {
          await updateContact(existing.id, payload);
          toast.success("Contact updated");
        } else {
          const created = await createContact(payload);
          toast.success("Contact added");
          setOpen(false);
          router.push(`/contacts/${created.id}`);
          return;
        }
        setOpen(false);
        router.refresh();
      } catch {
        toast.error(existing ? "Couldn't update contact" : "Couldn't add contact");
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
          Add contact
        </Button>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{existing ? "Edit contact" : "Add contact"}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cf-first">First name</Label>
                <Input id="cf-first" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cf-last">Last name</Label>
                <Input id="cf-last" value={lastName} onChange={(e) => setLastName(e.target.value)} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cf-title">Job title</Label>
              <Input id="cf-title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cf-dept">Department</Label>
              <Input id="cf-dept" value={department} onChange={(e) => setDepartment(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Company</Label>
              <EntityPicker
                label="company"
                placeholder="Search companies…"
                search={async (q) => (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name, sublabel: c.industry }))}
                value={company ? { id: company.id, label: company.label } : null}
                onChange={(v) => setCompany(v)}
              />
            </div>
            {!existing && (
              <>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="cf-email">Email</Label>
                  <Input id="cf-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="cf-phone">Phone</Label>
                  <Input id="cf-phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || (!firstName && !lastName)}>
              {pending ? "Saving…" : existing ? "Save changes" : "Add contact"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
