"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { Pencil, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EntityAvatar } from "@/components/entity-avatar";
import { EntityPicker } from "@/components/entity-picker";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { deleteContact, searchCompanies, updateContact } from "@/lib/actions";
import { sourceLabel } from "@/lib/sources";
import type { ContactDetail } from "@/lib/types";

/**
 * Replaces the old "Edit" button that popped a separate modal (limited to
 * name/title/department/company) with in-place editing: clicking Edit turns
 * every editable field on the page itself into an input, right where the
 * value was displayed, and Save/Cancel replace the Edit/Delete buttons -
 * closer to how a spreadsheet or Airtable-style record panel behaves than a
 * modal form. Read-only Act!-computed fields (last call/meeting/letter
 * dates) never become inputs; there's nothing in Act! itself to edit them
 * from either.
 */
export function ContactEditablePanel({ contact }: { contact: ContactDetail }) {
  const [editing, setEditing] = useState(false);
  const [pending, startTransition] = useTransition();

  const [firstName, setFirstName] = useState(contact.first_name ?? "");
  const [lastName, setLastName] = useState(contact.last_name ?? "");
  const [jobTitle, setJobTitle] = useState(contact.job_title ?? "");
  const [department, setDepartment] = useState(contact.department ?? "");
  const [category, setCategory] = useState(contact.category ?? "");
  const [referredBy, setReferredBy] = useState(contact.referred_by ?? "");
  const [birthdate, setBirthdate] = useState(contact.birthdate ?? "");
  const [company, setCompany] = useState<{ id: string; label: string } | null>(
    contact.company ? { id: contact.company.id, label: contact.company.name } : null
  );

  const name =
    contact.full_name ||
    [contact.first_name, contact.last_name].filter(Boolean).join(" ") ||
    "(no name)";

  function cancel() {
    setFirstName(contact.first_name ?? "");
    setLastName(contact.last_name ?? "");
    setJobTitle(contact.job_title ?? "");
    setDepartment(contact.department ?? "");
    setCategory(contact.category ?? "");
    setReferredBy(contact.referred_by ?? "");
    setBirthdate(contact.birthdate ?? "");
    setCompany(contact.company ? { id: contact.company.id, label: contact.company.name } : null);
    setEditing(false);
  }

  function save() {
    startTransition(async () => {
      try {
        await updateContact(contact.id, {
          first_name: firstName,
          last_name: lastName,
          job_title: jobTitle,
          department,
          category,
          referred_by: referredBy,
          birthdate,
          company_id: company?.id ?? null,
        });
        toast.success("Contact updated");
        setEditing(false);
      } catch {
        toast.error("Couldn't save changes");
      }
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <EntityAvatar name={name} className="mt-0.5 size-11 text-sm" />
          <div className="flex flex-col gap-1.5">
            {editing ? (
              <div className="flex gap-2">
                <Input
                  className="h-8 w-40 text-base font-semibold"
                  value={firstName}
                  placeholder="First name"
                  onChange={(e) => setFirstName(e.target.value)}
                />
                <Input
                  className="h-8 w-40 text-base font-semibold"
                  value={lastName}
                  placeholder="Last name"
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold">{name}</h1>
                <Badge variant="secondary">{sourceLabel(contact.source_db)}</Badge>
              </div>
            )}

            {editing ? (
              <div className="flex flex-wrap gap-2">
                <Input
                  className="h-8 w-44"
                  value={jobTitle}
                  placeholder="Job title"
                  onChange={(e) => setJobTitle(e.target.value)}
                />
                <Input
                  className="h-8 w-44"
                  value={department}
                  placeholder="Department"
                  onChange={(e) => setDepartment(e.target.value)}
                />
              </div>
            ) : (
              (contact.job_title || contact.department) && (
                <p className="text-sm text-muted-foreground">
                  {contact.job_title}
                  {contact.job_title && contact.department ? " · " : ""}
                  {contact.department}
                </p>
              )
            )}

            {editing ? (
              <div className="w-56">
                <EntityPicker
                  label="company"
                  placeholder="Search companies…"
                  search={async (q) =>
                    (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name, sublabel: c.industry }))
                  }
                  value={company}
                  onChange={setCompany}
                />
              </div>
            ) : (
              contact.company && (
                <Link href={`/companies/${contact.company.id}`} className="text-sm hover:underline">
                  {contact.company.name}
                </Link>
              )
            )}
          </div>
        </div>

        <div className="flex shrink-0 gap-2">
          {editing ? (
            <>
              <Button variant="outline" size="sm" onClick={cancel} disabled={pending}>
                <X className="size-4" />
                Cancel
              </Button>
              <Button size="sm" onClick={save} disabled={pending}>
                {pending ? "Saving…" : "Save"}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="size-4" />
                Edit
              </Button>
              <DeleteEntityButton entityLabel={name} id={contact.id} action={deleteContact} redirectTo="/contacts" />
            </>
          )}
        </div>
      </div>

      {(editing || contact.category || contact.referred_by || contact.birthdate) && (
        <div className="grid gap-3 text-sm sm:grid-cols-3">
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-muted-foreground">ID / Status</Label>
            {editing ? (
              <Input value={category} onChange={(e) => setCategory(e.target.value)} />
            ) : (
              <div>{contact.category || <span className="text-muted-foreground">—</span>}</div>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-muted-foreground">Referred by</Label>
            {editing ? (
              <Input value={referredBy} onChange={(e) => setReferredBy(e.target.value)} />
            ) : (
              <div>{contact.referred_by || <span className="text-muted-foreground">—</span>}</div>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-muted-foreground">Birthdate</Label>
            {editing ? (
              <Input type="date" value={birthdate ?? ""} onChange={(e) => setBirthdate(e.target.value)} />
            ) : (
              <div>
                {contact.birthdate ? (
                  new Date(contact.birthdate).toLocaleDateString()
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
