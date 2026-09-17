"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import {
  Building2,
  Check,
  Copy,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import type { AddressInput, EmailInput, PhoneInput } from "@/lib/actions";
import type { ContactDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EntityAvatar } from "@/components/entity-avatar";
import { EntityPicker } from "@/components/entity-picker";
import { AddressBlock } from "@/components/address-block";
import { ContactGroupsEditor } from "@/components/contact-groups-editor";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { sourceLabel, sourceBadgeStyle as publicationBadgeStyle } from "@/lib/sources";
import {
  deleteContact,
  removeContactAddress,
  removeContactEmail,
  removeContactPhone,
  saveContactAddress,
  saveContactEmail,
  saveContactPhone,
  searchCompanies,
  updateContact,
} from "@/lib/actions";

type Row<T> = T & { id: string; isNew?: boolean };

let tempIdCounter = 0;
function tempId() {
  tempIdCounter += 1;
  return `new-${tempIdCounter}`;
}

/**
 * The sticky identity card on the contact page - and, since the "Edit
 * Profile" tab this used to live behind was effectively unreachable (a
 * pencil icon on this same card had no handler wired to it at all), the
 * ONLY place contact editing happens now. Clicking Edit turns every field
 * here - name, job title, company, every email/phone/address row - into an
 * input in the exact spot it was displayed, with per-row add/remove for the
 * contact channels; Save/Cancel replace the pencil. Nothing opens a dialog.
 */
export function ContactDossier({ contact }: { contact: ContactDetail }) {
  const [editing, setEditing] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const name =
    contact.full_name ||
    [contact.first_name, contact.last_name].filter(Boolean).join(" ") ||
    "(no name)";

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

  const [emails, setEmails] = useState<Row<EmailInput>[]>(
    contact.emails.map((e) => ({ id: e.id, type_label: e.type_label ?? "Business", address: e.address ?? "" }))
  );
  const [phones, setPhones] = useState<Row<PhoneInput>[]>(
    contact.phones.map((p) => ({ id: p.id, type_label: p.type_label ?? "Business", number: p.number ?? "" }))
  );
  const [addresses, setAddresses] = useState<Row<AddressInput>[]>(
    contact.addresses.map((a) => ({
      id: a.id,
      type_label: a.type_label ?? "Business",
      line1: a.line1 ?? "",
      line2: a.line2 ?? "",
      city: a.city ?? "",
      state: a.state ?? "",
      postal_code: a.postal_code ?? "",
      country: a.country ?? "",
    }))
  );
  const [removedIds, setRemovedIds] = useState<{ emails: string[]; phones: string[]; addresses: string[] }>({
    emails: [],
    phones: [],
    addresses: [],
  });

  function resetToContact() {
    setFirstName(contact.first_name ?? "");
    setLastName(contact.last_name ?? "");
    setJobTitle(contact.job_title ?? "");
    setDepartment(contact.department ?? "");
    setCategory(contact.category ?? "");
    setReferredBy(contact.referred_by ?? "");
    setBirthdate(contact.birthdate ?? "");
    setCompany(contact.company ? { id: contact.company.id, label: contact.company.name } : null);
    setEmails(contact.emails.map((e) => ({ id: e.id, type_label: e.type_label ?? "Business", address: e.address ?? "" })));
    setPhones(contact.phones.map((p) => ({ id: p.id, type_label: p.type_label ?? "Business", number: p.number ?? "" })));
    setAddresses(
      contact.addresses.map((a) => ({
        id: a.id,
        type_label: a.type_label ?? "Business",
        line1: a.line1 ?? "",
        line2: a.line2 ?? "",
        city: a.city ?? "",
        state: a.state ?? "",
        postal_code: a.postal_code ?? "",
        country: a.country ?? "",
      }))
    );
    setRemovedIds({ emails: [], phones: [], addresses: [] });
  }

  function cancel() {
    resetToContact();
    setEditing(false);
  }

  function copyText(text: string, label: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success(`Copied ${label} to clipboard`);
    setTimeout(() => setCopiedKey(null), 2000);
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

        await Promise.all([
          ...emails
            .filter((e) => e.address?.trim())
            .map((e) => saveContactEmail(contact.id, e.isNew ? undefined : e.id, { type_label: e.type_label, address: e.address })),
          ...removedIds.emails.map((id) => removeContactEmail(contact.id, id)),
          ...phones
            .filter((p) => p.number?.trim())
            .map((p) => saveContactPhone(contact.id, p.isNew ? undefined : p.id, { type_label: p.type_label, number: p.number })),
          ...removedIds.phones.map((id) => removeContactPhone(contact.id, id)),
          ...addresses
            .filter((a) => a.line1?.trim() || a.city?.trim() || a.postal_code?.trim())
            .map((a) =>
              saveContactAddress(contact.id, a.isNew ? undefined : a.id, {
                type_label: a.type_label,
                line1: a.line1,
                line2: a.line2,
                city: a.city,
                state: a.state,
                postal_code: a.postal_code,
                country: a.country,
              })
            ),
          ...removedIds.addresses.map((id) => removeContactAddress(contact.id, id)),
        ]);

        toast.success("Contact updated");
        setEditing(false);
      } catch {
        toast.error("Couldn't save changes");
      }
    });
  }


  return (
    <div className="flex flex-col gap-4">
      <Card className="editorial-card overflow-hidden">
        <div className="h-2 w-full bg-gradient-to-r from-amber-600/60 via-primary to-amber-700/60" />

        <CardHeader className="p-5 pb-4">
          <div className="flex items-start justify-between gap-3">
            <EntityAvatar
              name={name}
              className="size-14 text-base font-semibold border-2 border-background shadow-xs ring-1 ring-border"
            />
            <div className="flex items-center gap-1.5">
              <Badge variant="outline" className={`text-[11px] font-medium ${publicationBadgeStyle(contact.source_db)}`}>
                {sourceLabel(contact.source_db)}
              </Badge>
              {contact.is_unsubscribed && (
                <Badge variant="outline" className="text-[11px] font-medium border-destructive/30 bg-destructive/10 text-destructive">
                  Unsubscribed
                </Badge>
              )}
              {editing ? (
                <>
                  <Button size="icon-xs" variant="ghost" onClick={cancel} disabled={pending} title="Cancel" className="cursor-pointer">
                    <X className="size-3.5 text-muted-foreground" />
                  </Button>
                  <Button size="icon-xs" variant="ghost" onClick={save} disabled={pending} title="Save" className="cursor-pointer">
                    <Check className="size-3.5 text-emerald-600" />
                  </Button>
                </>
              ) : (
                <Button
                  size="icon-xs"
                  variant="ghost"
                  onClick={() => setEditing(true)}
                  title="Edit details"
                  className="cursor-pointer"
                >
                  <Pencil className="size-3.5 text-muted-foreground" />
                </Button>
              )}
            </div>
          </div>

          <div className="mt-3 flex flex-col gap-1.5">
            {editing ? (
              <div className="flex gap-2">
                <Input
                  className="h-8 text-base font-semibold"
                  placeholder="First name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
                <Input
                  className="h-8 text-base font-semibold"
                  placeholder="Last name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            ) : (
              <h2 className="editorial-title text-xl font-bold tracking-tight text-foreground">{name}</h2>
            )}

            {editing ? (
              <div className="flex gap-2">
                <Input className="h-7 text-xs" placeholder="Job title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} />
                <Input
                  className="h-7 text-xs"
                  placeholder="Department"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                />
              </div>
            ) : (
              contact.job_title && <p className="text-xs font-medium text-muted-foreground">{contact.job_title}</p>
            )}

            {editing ? (
              <EntityPicker
                label="company"
                placeholder="Search companies…"
                search={async (q) => (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name, sublabel: c.industry }))}
                value={company}
                onChange={setCompany}
              />
            ) : (
              contact.company && (
                <Link
                  href={`/companies/${contact.company.id}`}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline mt-1"
                >
                  <Building2 className="size-3.5 shrink-0" />
                  <span>{contact.company.name}</span>
                </Link>
              )
            )}
          </div>
        </CardHeader>

        <CardContent className="flex flex-col gap-4 p-5 pt-0 text-xs">
          {/* Contact channels - each row edits in place; add/remove per row */}
          <div className="flex flex-col gap-2 rounded-md border border-border/80 bg-muted/40 p-3">
            {emails.map((e, idx) =>
              editing ? (
                <div key={e.id} className="flex items-center gap-1.5">
                  <Mail className="size-3.5 shrink-0 text-muted-foreground" />
                  <Input
                    className="h-7 w-20 text-[11px]"
                    value={e.type_label}
                    onChange={(v) => setEmails((rows) => rows.map((r) => (r.id === e.id ? { ...r, type_label: v.target.value } : r)))}
                  />
                  <Input
                    className="h-7 flex-1 text-xs"
                    placeholder="Email address"
                    value={e.address}
                    onChange={(v) => setEmails((rows) => rows.map((r) => (r.id === e.id ? { ...r, address: v.target.value } : r)))}
                  />
                  <button
                    type="button"
                    className="shrink-0 text-muted-foreground hover:text-destructive cursor-pointer"
                    onClick={() => {
                      setEmails((rows) => rows.filter((r) => r.id !== e.id));
                      if (!e.isNew) setRemovedIds((r) => ({ ...r, emails: [...r.emails, e.id] }));
                    }}
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ) : (
                <div key={e.id || idx} className="group flex items-center justify-between gap-2">
                  <a href={`mailto:${e.address}`} className="flex items-center gap-2 truncate text-foreground hover:text-primary">
                    <Mail className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{e.address}</span>
                  </a>
                  <button
                    type="button"
                    onClick={() => copyText(e.address ?? "", "email", `email-${idx}`)}
                    className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 cursor-pointer"
                    title="Copy email"
                  >
                    {copiedKey === `email-${idx}` ? <Check className="size-3 text-emerald-600" /> : <Copy className="size-3" />}
                  </button>
                </div>
              )
            )}

            {phones.map((p, idx) =>
              editing ? (
                <div key={p.id} className="flex items-center gap-1.5">
                  <Phone className="size-3.5 shrink-0 text-muted-foreground" />
                  <Input
                    className="h-7 w-20 text-[11px]"
                    value={p.type_label}
                    onChange={(v) => setPhones((rows) => rows.map((r) => (r.id === p.id ? { ...r, type_label: v.target.value } : r)))}
                  />
                  <Input
                    className="h-7 flex-1 text-xs"
                    placeholder="Phone number"
                    value={p.number}
                    onChange={(v) => setPhones((rows) => rows.map((r) => (r.id === p.id ? { ...r, number: v.target.value } : r)))}
                  />
                  <button
                    type="button"
                    className="shrink-0 text-muted-foreground hover:text-destructive cursor-pointer"
                    onClick={() => {
                      setPhones((rows) => rows.filter((r) => r.id !== p.id));
                      if (!p.isNew) setRemovedIds((r) => ({ ...r, phones: [...r.phones, p.id] }));
                    }}
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ) : (
                <div key={p.id || idx} className="group flex items-center justify-between gap-2">
                  <a href={`tel:${p.number}`} className="flex items-center gap-2 truncate text-foreground hover:text-primary">
                    <Phone className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{p.number}</span>
                  </a>
                  <button
                    type="button"
                    onClick={() => copyText(p.number ?? "", "phone", `phone-${idx}`)}
                    className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 cursor-pointer"
                    title="Copy phone"
                  >
                    {copiedKey === `phone-${idx}` ? <Check className="size-3 text-emerald-600" /> : <Copy className="size-3" />}
                  </button>
                </div>
              )
            )}

            {addresses.map((a) =>
              editing ? (
                <div key={a.id} className="flex flex-col gap-1.5 border-t border-border/60 pt-2 first:border-t-0 first:pt-0">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="size-3.5 shrink-0 text-muted-foreground" />
                    <Input
                      className="h-7 w-20 text-[11px]"
                      value={a.type_label}
                      onChange={(v) => setAddresses((rows) => rows.map((r) => (r.id === a.id ? { ...r, type_label: v.target.value } : r)))}
                    />
                    <button
                      type="button"
                      className="ml-auto shrink-0 text-muted-foreground hover:text-destructive cursor-pointer"
                      onClick={() => {
                        setAddresses((rows) => rows.filter((r) => r.id !== a.id));
                        if (!a.isNew) setRemovedIds((r) => ({ ...r, addresses: [...r.addresses, a.id] }));
                      }}
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 pl-5">
                    <Input
                      className="col-span-2 h-7 text-xs"
                      placeholder="Address line 1"
                      value={a.line1}
                      onChange={(v) => setAddresses((rows) => rows.map((r) => (r.id === a.id ? { ...r, line1: v.target.value } : r)))}
                    />
                    <Input
                      className="col-span-2 h-7 text-xs"
                      placeholder="Address line 2"
                      value={a.line2}
                      onChange={(v) => setAddresses((rows) => rows.map((r) => (r.id === a.id ? { ...r, line2: v.target.value } : r)))}
                    />
                    <Input
                      className="h-7 text-xs"
                      placeholder="City"
                      value={a.city}
                      onChange={(v) => setAddresses((rows) => rows.map((r) => (r.id === a.id ? { ...r, city: v.target.value } : r)))}
                    />
                    <Input
                      className="h-7 text-xs"
                      placeholder="County"
                      value={a.state}
                      onChange={(v) => setAddresses((rows) => rows.map((r) => (r.id === a.id ? { ...r, state: v.target.value } : r)))}
                    />
                    <Input
                      className="h-7 text-xs"
                      placeholder="Postcode"
                      value={a.postal_code}
                      onChange={(v) => setAddresses((rows) => rows.map((r) => (r.id === a.id ? { ...r, postal_code: v.target.value } : r)))}
                    />
                    <Input
                      className="h-7 text-xs"
                      placeholder="Country"
                      value={a.country}
                      onChange={(v) => setAddresses((rows) => rows.map((r) => (r.id === a.id ? { ...r, country: v.target.value } : r)))}
                    />
                  </div>
                </div>
              ) : (
                <div key={a.id} className="flex items-start gap-2 pt-1">
                  <MapPin className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                  <div className="flex-1 text-[11px] text-muted-foreground">
                    <AddressBlock
                      address={{
                        id: a.id,
                        type_label: a.type_label ?? null,
                        line1: a.line1 ?? null,
                        line2: a.line2 ?? null,
                        line3: null,
                        city: a.city ?? null,
                        state: a.state ?? null,
                        postal_code: a.postal_code ?? null,
                        country: a.country ?? null,
                      }}
                    />
                  </div>
                </div>
              )
            )}

            {!editing && emails.length === 0 && phones.length === 0 && addresses.length === 0 && (
              <span className="text-muted-foreground italic">No contact channels on file.</span>
            )}

            {editing && (
              <div className="flex flex-wrap gap-3 border-t border-border/60 pt-2 text-[11px] font-semibold text-primary">
                <button
                  type="button"
                  className="flex items-center gap-1 cursor-pointer hover:underline"
                  onClick={() => setEmails((rows) => [...rows, { id: tempId(), type_label: "Business", address: "", isNew: true }])}
                >
                  <Plus className="size-3" /> Email
                </button>
                <button
                  type="button"
                  className="flex items-center gap-1 cursor-pointer hover:underline"
                  onClick={() => setPhones((rows) => [...rows, { id: tempId(), type_label: "Business", number: "", isNew: true }])}
                >
                  <Plus className="size-3" /> Phone
                </button>
                <button
                  type="button"
                  className="flex items-center gap-1 cursor-pointer hover:underline"
                  onClick={() =>
                    setAddresses((rows) => [
                      ...rows,
                      { id: tempId(), type_label: "Business", line1: "", line2: "", city: "", state: "", postal_code: "", country: "", isNew: true },
                    ])
                  }
                >
                  <Plus className="size-3" /> Address
                </button>
              </div>
            )}
          </div>

          {/* Status fields - editable alongside everything else */}
          {(editing || contact.category || contact.referred_by || contact.birthdate) && (
            <div className="grid grid-cols-2 gap-2 border-t pt-3 text-[11px]">
              <div className="flex flex-col gap-1">
                <Label className="text-[10px] text-muted-foreground">ID / Status</Label>
                {editing ? (
                  <Input className="h-7 text-xs" value={category} onChange={(e) => setCategory(e.target.value)} />
                ) : (
                  <span className="font-medium text-foreground">{contact.category || "—"}</span>
                )}
              </div>
              <div className="flex flex-col gap-1">
                <Label className="text-[10px] text-muted-foreground">Referred by</Label>
                {editing ? (
                  <Input className="h-7 text-xs" value={referredBy} onChange={(e) => setReferredBy(e.target.value)} />
                ) : (
                  <span className="font-medium text-foreground">{contact.referred_by || "—"}</span>
                )}
              </div>
              <div className="flex flex-col gap-1">
                <Label className="text-[10px] text-muted-foreground">Birthdate</Label>
                {editing ? (
                  <Input className="h-7 text-xs" type="date" value={birthdate ?? ""} onChange={(e) => setBirthdate(e.target.value)} />
                ) : (
                  <span className="font-medium text-foreground">
                    {contact.birthdate ? new Date(contact.birthdate).toLocaleDateString() : "—"}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Activity Cadence Stats - read-only, Act!-computed */}
          {(contact.last_meet_date || contact.last_reach_date || contact.last_attempt_date) && (
            <div className="grid grid-cols-2 gap-2 border-t pt-3 text-[11px]">
              {contact.last_reach_date && (
                <div>
                  <span className="text-muted-foreground">Last Reach: </span>
                  <span className="font-medium text-foreground">{new Date(contact.last_reach_date).toLocaleDateString()}</span>
                </div>
              )}
              {contact.last_meet_date && (
                <div>
                  <span className="text-muted-foreground">Last Meeting: </span>
                  <span className="font-medium text-foreground">{new Date(contact.last_meet_date).toLocaleDateString()}</span>
                </div>
              )}
              {contact.last_attempt_date && (
                <div>
                  <span className="text-muted-foreground">Last Attempt: </span>
                  <span className="font-medium text-foreground">{new Date(contact.last_attempt_date).toLocaleDateString()}</span>
                </div>
              )}
            </div>
          )}

          {/* Group Memberships - already independently editable, left as-is */}
          <div className="border-t pt-3">
            <span className="text-[11px] font-semibold text-muted-foreground block mb-2">Groups</span>
            <ContactGroupsEditor contactId={contact.id} groups={contact.groups} />
          </div>

          {!editing && (
            <div className="border-t pt-3">
              <DeleteEntityButton entityLabel={name} id={contact.id} action={deleteContact} redirectTo="/contacts" />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
