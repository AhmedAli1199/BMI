"use client";

import { useState, useTransition } from "react";
import {
  Building2,
  Check,
  ExternalLink,
  Globe,
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
import type { CompanyDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AddressBlock } from "@/components/address-block";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { sourceLabel, sourceBadgeStyle } from "@/lib/sources";
import {
  deleteCompany,
  removeCompanyAddress,
  removeCompanyEmail,
  removeCompanyPhone,
  saveCompanyAddress,
  saveCompanyEmail,
  saveCompanyPhone,
  updateCompany,
} from "@/lib/actions";

type Row<T> = T & { id: string; isNew?: boolean };

let tempIdCounter = 0;
function tempId() {
  tempIdCounter += 1;
  return `new-${tempIdCounter}`;
}

/** Same in-place editing approach as ContactDossier - see its docstring.
 * The sticky company identity card, and the only place company editing
 * happens (the old separate "Edit Account" tab is gone). */
export function CompanyDossier({ company }: { company: CompanyDetail }) {
  const [editing, setEditing] = useState(false);
  const [pending, startTransition] = useTransition();

  const [name, setName] = useState(company.name);
  const [industry, setIndustry] = useState(company.industry ?? "");
  const [category, setCategory] = useState(company.category ?? "");
  const [territory, setTerritory] = useState(company.territory ?? "");
  const [region, setRegion] = useState(company.region ?? "");
  const [website, setWebsite] = useState(company.website ?? "");
  const [description, setDescription] = useState(company.description ?? "");
  const [numEmployees, setNumEmployees] = useState(
    company.num_employees != null ? String(company.num_employees) : ""
  );

  const [emails, setEmails] = useState<Row<EmailInput>[]>(
    company.emails.map((e) => ({ id: e.id, type_label: e.type_label ?? "Business", address: e.address ?? "" }))
  );
  const [phones, setPhones] = useState<Row<PhoneInput>[]>(
    company.phones.map((p) => ({ id: p.id, type_label: p.type_label ?? "Business", number: p.number ?? "" }))
  );
  const [addresses, setAddresses] = useState<Row<AddressInput>[]>(
    company.addresses.map((a) => ({
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

  function resetToCompany() {
    setName(company.name);
    setIndustry(company.industry ?? "");
    setCategory(company.category ?? "");
    setTerritory(company.territory ?? "");
    setRegion(company.region ?? "");
    setWebsite(company.website ?? "");
    setDescription(company.description ?? "");
    setNumEmployees(company.num_employees != null ? String(company.num_employees) : "");
    setEmails(company.emails.map((e) => ({ id: e.id, type_label: e.type_label ?? "Business", address: e.address ?? "" })));
    setPhones(company.phones.map((p) => ({ id: p.id, type_label: p.type_label ?? "Business", number: p.number ?? "" })));
    setAddresses(
      company.addresses.map((a) => ({
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
    resetToCompany();
    setEditing(false);
  }

  function save() {
    startTransition(async () => {
      try {
        await updateCompany(company.id, {
          name,
          industry,
          category,
          territory,
          region,
          website,
          description,
          num_employees: numEmployees ? Number(numEmployees) : undefined,
        });

        await Promise.all([
          ...emails
            .filter((e) => e.address?.trim())
            .map((e) => saveCompanyEmail(company.id, e.isNew ? undefined : e.id, { type_label: e.type_label, address: e.address })),
          ...removedIds.emails.map((id) => removeCompanyEmail(company.id, id)),
          ...phones
            .filter((p) => p.number?.trim())
            .map((p) => saveCompanyPhone(company.id, p.isNew ? undefined : p.id, { type_label: p.type_label, number: p.number })),
          ...removedIds.phones.map((id) => removeCompanyPhone(company.id, id)),
          ...addresses
            .filter((a) => a.line1?.trim() || a.city?.trim() || a.postal_code?.trim())
            .map((a) =>
              saveCompanyAddress(company.id, a.isNew ? undefined : a.id, {
                type_label: a.type_label,
                line1: a.line1,
                line2: a.line2,
                city: a.city,
                state: a.state,
                postal_code: a.postal_code,
                country: a.country,
              })
            ),
          ...removedIds.addresses.map((id) => removeCompanyAddress(company.id, id)),
        ]);

        toast.success("Company updated");
        setEditing(false);
      } catch {
        toast.error("Couldn't save changes");
      }
    });
  }

  return (
    <Card className="editorial-card overflow-hidden">
      <div className="masthead-rule w-full bg-primary" />
      <CardHeader className="p-5 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="brand-icon size-14 text-primary">
            <Building2 className="size-6" />
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className={`text-[11px] font-medium ${sourceBadgeStyle(company.source_db)}`}>
              {sourceLabel(company.source_db)}
            </Badge>
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
              <Button size="icon-xs" variant="ghost" onClick={() => setEditing(true)} title="Edit details" className="cursor-pointer">
                <Pencil className="size-3.5 text-muted-foreground" />
              </Button>
            )}
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-1.5">
          {editing ? (
            <Input className="h-8 text-xl font-bold" value={name} onChange={(e) => setName(e.target.value)} />
          ) : (
            <h2 className="editorial-title text-xl font-bold tracking-tight text-foreground">{company.name}</h2>
          )}

          {editing ? (
            <div className="flex flex-wrap gap-1.5">
              <Input className="h-7 w-32 text-xs" placeholder="Industry" value={industry} onChange={(e) => setIndustry(e.target.value)} />
              <Input className="h-7 w-32 text-xs" placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} />
              <Input className="h-7 w-28 text-xs" placeholder="Territory" value={territory} onChange={(e) => setTerritory(e.target.value)} />
            </div>
          ) : (
            <>
              {company.industry && <p className="text-xs font-medium text-muted-foreground">{company.industry}</p>}
              {company.category && (
                <Badge variant="secondary" className="mt-1 w-fit text-[10px]">
                  {company.category}
                </Badge>
              )}
            </>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 p-5 pt-1 text-xs">
        {editing ? (
          <Textarea
            className="text-xs"
            placeholder="Description"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        ) : (
          company.description && (
            <p className="text-xs leading-relaxed text-muted-foreground border-b pb-3 italic">&ldquo;{company.description}&rdquo;</p>
          )
        )}

        {/* Company contact channels - each row edits in place */}
        <div className="flex flex-col gap-2 rounded-md border border-border/80 bg-muted/40 p-3">
          {editing ? (
            <div className="flex items-center gap-1.5">
              <Globe className="size-3.5 shrink-0 text-muted-foreground" />
              <Input className="h-7 flex-1 text-xs" placeholder="Website" value={website} onChange={(e) => setWebsite(e.target.value)} />
            </div>
          ) : (
            company.website && (
              <a
                href={company.website.startsWith("http") ? company.website : `https://${company.website}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 truncate text-foreground hover:text-primary font-medium"
              >
                <Globe className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{company.website.replace(/^https?:\/\//, "")}</span>
                <ExternalLink className="size-3 ml-auto text-muted-foreground" />
              </a>
            )
          )}

          {phones.map((p) =>
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
              <a key={p.id} href={`tel:${p.number}`} className="flex items-center gap-2 truncate text-foreground hover:text-primary">
                <Phone className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{p.number}</span>
                <span className="ml-auto text-[10px] text-muted-foreground">{p.type_label || "Phone"}</span>
              </a>
            )
          )}

          {emails.map((e) =>
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
              <a key={e.id} href={`mailto:${e.address}`} className="flex items-center gap-2 truncate text-foreground hover:text-primary">
                <Mail className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{e.address}</span>
              </a>
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

        {/* Scale stats */}
        {(editing || company.num_employees || company.region) && (
          <div className="grid grid-cols-2 gap-2 border-t pt-3 text-[11px]">
            <div className="flex flex-col gap-1">
              <span className="text-muted-foreground">Employees</span>
              {editing ? (
                <Input
                  className="h-7 text-xs"
                  type="number"
                  min={0}
                  value={numEmployees}
                  onChange={(e) => setNumEmployees(e.target.value)}
                />
              ) : (
                <span className="font-semibold text-foreground">{company.num_employees?.toLocaleString() || "—"}</span>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-muted-foreground">Region</span>
              {editing ? (
                <Input className="h-7 text-xs" value={region} onChange={(e) => setRegion(e.target.value)} />
              ) : (
                <span className="font-medium text-foreground">{company.region || "—"}</span>
              )}
            </div>
          </div>
        )}

        {!editing && (
          <div className="border-t pt-3">
            <DeleteEntityButton entityLabel={company.name} id={company.id} action={deleteCompany} redirectTo="/companies" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
