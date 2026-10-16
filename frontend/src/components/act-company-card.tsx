"use client";

import { useState, useTransition } from "react";
import { Check, Copy, ExternalLink, Pencil, Save, X } from "lucide-react";
import { toast } from "sonner";
import type { CompanyDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { updateCompany, saveCompanyPhone, saveCompanyEmail, saveCompanyAddress } from "@/lib/actions";

// A field row: label on the left, value next to it. Empty fields are hidden while viewing (Edit shows them all).
const ROW = "grid grid-cols-[7.5rem_minmax(0,1fr)] items-baseline gap-2";
const ROW_VIEW = `${ROW} [&:has([data-empty])]:hidden`;
const EMPTY = <span data-empty="" className="text-muted-foreground/50">—</span>;

export function ActCompanyCard({ company }: { company: CompanyDetail }) {
  const [editing, setEditing] = useState(false);
  const [pending, startTransition] = useTransition();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Editable Form State
  const [name, setName] = useState(company.name);
  const [industry, setIndustry] = useState(company.industry ?? "");
  const [category, setCategory] = useState(company.category ?? "");
  const [territory, setTerritory] = useState(company.territory ?? "");
  const [region, setRegion] = useState(company.region ?? "");
  const [website, setWebsite] = useState(company.website ?? "");
  const [numEmployees, setNumEmployees] = useState(
    company.num_employees != null ? String(company.num_employees) : ""
  );

  // Phone/email/address live in separate child tables - the header card
  // only ever shows the first of each as "the" primary one, mirroring
  // ActContactCard's approach.
  const [phone, setPhone] = useState(company.phones[0]?.number ?? "");
  const [email, setEmail] = useState(company.emails[0]?.address ?? "");
  const [addrLine1, setAddrLine1] = useState(company.addresses[0]?.line1 ?? "");
  const [addrLine2, setAddrLine2] = useState(company.addresses[0]?.line2 ?? "");
  const [addrCity, setAddrCity] = useState(company.addresses[0]?.city ?? "");
  const [addrState, setAddrState] = useState(company.addresses[0]?.state ?? "");
  const [addrPostal, setAddrPostal] = useState(company.addresses[0]?.postal_code ?? "");
  const [addrCountry, setAddrCountry] = useState(company.addresses[0]?.country ?? "");

  function copyText(text: string, label: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success(`Copied ${label} to clipboard`);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  function handleSave() {
    startTransition(async () => {
      try {
        await Promise.all([
          updateCompany(company.id, {
            name,
            industry,
            category,
            territory,
            region,
            website,
            num_employees: numEmployees ? Number(numEmployees) : undefined,
          }),
          phone !== (company.phones[0]?.number ?? "")
            ? saveCompanyPhone(company.id, company.phones[0]?.id, { type_label: "Business", number: phone })
            : Promise.resolve(),
          email !== (company.emails[0]?.address ?? "")
            ? saveCompanyEmail(company.id, company.emails[0]?.id, { type_label: "Business", address: email })
            : Promise.resolve(),
          addrLine1 !== (company.addresses[0]?.line1 ?? "") ||
          addrLine2 !== (company.addresses[0]?.line2 ?? "") ||
          addrCity !== (company.addresses[0]?.city ?? "") ||
          addrState !== (company.addresses[0]?.state ?? "") ||
          addrPostal !== (company.addresses[0]?.postal_code ?? "") ||
          addrCountry !== (company.addresses[0]?.country ?? "")
            ? saveCompanyAddress(company.id, company.addresses[0]?.id, {
                type_label: "Business",
                line1: addrLine1,
                line2: addrLine2,
                city: addrCity,
                state: addrState,
                postal_code: addrPostal,
                country: addrCountry,
              })
            : Promise.resolve(),
        ]);
        toast.success("Company record updated");
        setEditing(false);
      } catch {
        toast.error("Failed to save company changes");
      }
    });
  }

  function handleCancel() {
    setName(company.name);
    setIndustry(company.industry ?? "");
    setCategory(company.category ?? "");
    setTerritory(company.territory ?? "");
    setRegion(company.region ?? "");
    setWebsite(company.website ?? "");
    setNumEmployees(company.num_employees != null ? String(company.num_employees) : "");
    setPhone(company.phones[0]?.number ?? "");
    setEmail(company.emails[0]?.address ?? "");
    setAddrLine1(company.addresses[0]?.line1 ?? "");
    setAddrLine2(company.addresses[0]?.line2 ?? "");
    setAddrCity(company.addresses[0]?.city ?? "");
    setAddrState(company.addresses[0]?.state ?? "");
    setAddrPostal(company.addresses[0]?.postal_code ?? "");
    setAddrCountry(company.addresses[0]?.country ?? "");
    setEditing(false);
  }

  const primaryAddress = company.addresses[0];
  const primaryPhone = company.phones[0]?.number;
  const primaryEmail = company.emails[0]?.address;

  return (
    <Card className="overflow-hidden border border-border/90 bg-card shadow-2xs">
      {/* Identity Header Bar */}
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/80 px-5 py-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Company details</span>

        {/* Action Controls (Edit / Save / Cancel) */}
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancel}
                disabled={pending}
                className="h-7 text-xs gap-1 cursor-pointer"
              >
                <X className="size-3" />
                <span>Cancel</span>
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={pending}
                className="h-7 text-xs gap-1 cursor-pointer font-semibold"
              >
                <Save className="size-3" />
                <span>{pending ? "Saving..." : "Save Changes"}</span>
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setEditing(true)}
              className="h-7 text-xs gap-1.5 cursor-pointer font-medium hover:border-primary/50"
            >
              <Pencil className="size-3 text-muted-foreground" />
              <span>Edit Company</span>
            </Button>
          )}
        </div>
      </CardHeader>

      
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6 p-5 text-xs">
        {/* COLUMN 1: Company Profile & Web */}
        <div className="flex flex-col gap-2.5">
          <div className="border-b pb-1.5 mb-1 flex items-center justify-between">
            <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
              Company Profile
            </span>
          </div>

          {/* Company Name */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Name</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            ) : (
              <span className="font-semibold text-foreground truncate min-w-0 text-left">
                {company.name}
              </span>
            )}
          </div>

          {/* Industry */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Industry</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {company.industry || EMPTY}
              </span>
            )}
          </div>

          {/* Phone */}
          <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-border/40">
            <span className="w-24 shrink-0 text-muted-foreground">Phone</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Business phone"
              />
            ) : primaryPhone ? (
              <div className="flex items-center gap-1.5">
                <a href={`tel:${primaryPhone}`} className="font-medium text-foreground hover:text-primary">
                  {primaryPhone}
                </a>
                <button
                  type="button"
                  onClick={() => copyText(primaryPhone, "phone", "comp-phone")}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {copiedKey === "comp-phone" ? (
                    <Check className="size-3 text-[var(--ok)]" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </button>
              </div>
            ) : (
              EMPTY
            )}
          </div>

          {/* E-mail */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">E-mail</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Business email"
              />
            ) : primaryEmail ? (
              <div className="flex items-center gap-1.5 max-w-[200px] truncate">
                <a href={`mailto:${primaryEmail}`} className="font-mono text-[11px] text-foreground hover:text-primary truncate">
                  {primaryEmail}
                </a>
                <button
                  type="button"
                  onClick={() => copyText(primaryEmail, "email", "comp-email")}
                  className="text-muted-foreground hover:text-foreground cursor-pointer shrink-0"
                >
                  {copiedKey === "comp-email" ? (
                    <Check className="size-3 text-[var(--ok)]" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </button>
              </div>
            ) : (
              EMPTY
            )}
          </div>

          {/* Web Site */}
          <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-border/40">
            <span className="w-24 shrink-0 text-muted-foreground">Web Site</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                placeholder="www.example.com"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
              />
            ) : website ? (
              <a
                href={website.startsWith("http") ? website : `https://${website}`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-primary hover:underline truncate inline-flex items-center gap-1"
              >
                <span>{website.replace(/^https?:\/\//, "")}</span>
                <ExternalLink className="size-3" />
              </a>
            ) : (
              EMPTY
            )}
          </div>
        </div>

        {/* COLUMN 2: Headquarters Address */}
        <div className="flex flex-col gap-2.5">
          <div className="border-b pb-1.5 mb-1 flex items-center justify-between">
            <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
              Headquarters Address
            </span>
          </div>

          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Address 1</span>
            {editing ? (
              <Input className="h-7 text-xs flex-1" value={addrLine1} onChange={(e) => setAddrLine1(e.target.value)} />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {primaryAddress?.line1 || EMPTY}
              </span>
            )}
          </div>

          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Address 2</span>
            {editing ? (
              <Input className="h-7 text-xs flex-1" value={addrLine2} onChange={(e) => setAddrLine2(e.target.value)} />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {primaryAddress?.line2 || EMPTY}
              </span>
            )}
          </div>

          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">City</span>
            {editing ? (
              <Input className="h-7 text-xs flex-1" value={addrCity} onChange={(e) => setAddrCity(e.target.value)} />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {primaryAddress?.city || EMPTY}
              </span>
            )}
          </div>

          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">County / State</span>
            {editing ? (
              <Input className="h-7 text-xs flex-1" value={addrState} onChange={(e) => setAddrState(e.target.value)} />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {primaryAddress?.state || EMPTY}
              </span>
            )}
          </div>

          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Postal Code</span>
            {editing ? (
              <Input className="h-7 text-xs flex-1 font-mono" value={addrPostal} onChange={(e) => setAddrPostal(e.target.value)} />
            ) : (
              <span className="font-mono font-medium text-foreground truncate min-w-0 text-left">
                {primaryAddress?.postal_code || EMPTY}
              </span>
            )}
          </div>

          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Country</span>
            {editing ? (
              <Input className="h-7 text-xs flex-1" value={addrCountry} onChange={(e) => setAddrCountry(e.target.value)} />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {primaryAddress?.country || EMPTY}
              </span>
            )}
          </div>
        </div>

        {/* COLUMN 3: Commercial Status & Territory */}
        <div className="flex flex-col gap-2.5">
          <div className="border-b pb-1.5 mb-1 flex items-center justify-between">
            <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
              Account Status &amp; Scope
            </span>
          </div>

          {/* Category */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Category</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            ) : (
              <Badge variant="secondary" className="font-semibold text-[11px]">
                {company.category || "Standard"}
              </Badge>
            )}
          </div>

          {/* Territory */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Territory</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={territory}
                onChange={(e) => setTerritory(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {company.territory || EMPTY}
              </span>
            )}
          </div>

          {/* Region */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Region</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {company.region || EMPTY}
              </span>
            )}
          </div>

          {/* Employees */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Employees</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                type="number"
                value={numEmployees}
                onChange={(e) => setNumEmployees(e.target.value)}
              />
            ) : (
              <span className="font-semibold text-foreground">
                {company.num_employees ? company.num_employees.toLocaleString() : EMPTY}
              </span>
            )}
          </div>

          {/* Linked Contacts Count */}
          <div className="flex items-baseline justify-between gap-2 pt-2 border-t border-border/40 text-[11px]">
            <span className="text-muted-foreground">Linked Contacts</span>
            <span className="font-bold text-primary">
              {company.contacts.length} people
            </span>
          </div>

          <div className="flex items-baseline justify-between text-[11px]">
            <span className="text-muted-foreground">Logged Notes</span>
            <span className="font-semibold text-foreground">
              {company.notes.length} entries
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
