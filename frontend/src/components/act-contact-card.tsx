"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, Copy, ExternalLink, Pencil, Save, X } from "lucide-react";
import { toast } from "sonner";
import type { ContactDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EntityPicker } from "@/components/entity-picker";
import { updateContact, saveContactPhone, saveContactEmail, saveContactAddress, searchCompanies } from "@/lib/actions";
import { ReassignContactButton } from "@/components/reassign-contact-button";
import { friendlyError } from "@/lib/errors";

function websiteHref(site: string): string {
  return /^https?:\/\//i.test(site) ? site : `https://${site}`;
}

// A field row: label on the left, value next to it. Empty fields are hidden while viewing (Edit shows them all).
const ROW = "grid grid-cols-[7.5rem_minmax(0,1fr)] items-baseline gap-2";
const ROW_VIEW = `${ROW} [&:has([data-empty])]:hidden`;
const EMPTY = <span data-empty="" className="text-muted-foreground/50">—</span>;
const PHONE_TYPES = ["Business", "Mobile", "Home", "Fax", "Other"];

/** Pick what kind of phone number this is. Keeps any type that came over from Act! as an option too. */
function PhoneTypeSelect({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) {
  const options = value && !PHONE_TYPES.includes(value) ? [value, ...PHONE_TYPES] : PHONE_TYPES;
  return (
    <select
      aria-label={label}
      className="h-7 w-24 shrink-0 rounded-md border border-input bg-transparent px-1.5 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );
}

export function ActContactCard({
  contact,
}: {
  contact: ContactDetail;
}) {
  const [editing, setEditing] = useState(false);
  const [pending, startTransition] = useTransition();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const router = useRouter();

  // Editable Form State
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

  // Phone/mobile/email/address live in separate child tables (a contact can
  // have several of each) - the header/business-card view only ever shows
  // the first of each as "the" primary one, so editing here just upserts
  // that first row (or creates one if none exists yet).
  const [phone, setPhone] = useState(contact.phones[0]?.number ?? "");
  const [mobile, setMobile] = useState(contact.phones[1]?.number ?? "");
  // Each number keeps its own type (Business, Mobile, Home...) - saving never relabels it.
  const firstPhoneType = contact.phones[0]?.type_label || "Business";
  const secondPhoneType = contact.phones[1]?.type_label || "Mobile";
  const [phoneType, setPhoneType] = useState(firstPhoneType);
  const [mobileType, setMobileType] = useState(secondPhoneType);
  const [email, setEmail] = useState(contact.emails[0]?.address ?? "");
  const [addrLine1, setAddrLine1] = useState(contact.addresses[0]?.line1 ?? "");
  const [addrLine2, setAddrLine2] = useState(contact.addresses[0]?.line2 ?? "");
  const [addrCity, setAddrCity] = useState(contact.addresses[0]?.city ?? "");
  const [addrState, setAddrState] = useState(contact.addresses[0]?.state ?? "");
  const [addrPostal, setAddrPostal] = useState(contact.addresses[0]?.postal_code ?? "");
  const [addrCountry, setAddrCountry] = useState(contact.addresses[0]?.country ?? "");

  const name =
    contact.full_name ||
    [contact.first_name, contact.last_name].filter(Boolean).join(" ") ||
    "(no name)";

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
          updateContact(contact.id, {
            first_name: firstName,
            last_name: lastName,
            job_title: jobTitle,
            department,
            category,
            referred_by: referredBy,
            birthdate,
            company_id: company?.id ?? null,
          }),
          phone !== (contact.phones[0]?.number ?? "") || (contact.phones[0] && phoneType !== firstPhoneType)
            ? saveContactPhone(contact.id, contact.phones[0]?.id, { type_label: phoneType, number: phone })
            : Promise.resolve(),
          mobile !== (contact.phones[1]?.number ?? "") || (contact.phones[1] && mobileType !== secondPhoneType)
            ? saveContactPhone(contact.id, contact.phones[1]?.id, { type_label: mobileType, number: mobile })
            : Promise.resolve(),
          email !== (contact.emails[0]?.address ?? "")
            ? saveContactEmail(contact.id, contact.emails[0]?.id, { type_label: contact.emails[0]?.type_label || "Business", address: email })
            : Promise.resolve(),
          addrLine1 !== (contact.addresses[0]?.line1 ?? "") ||
          addrLine2 !== (contact.addresses[0]?.line2 ?? "") ||
          addrCity !== (contact.addresses[0]?.city ?? "") ||
          addrState !== (contact.addresses[0]?.state ?? "") ||
          addrPostal !== (contact.addresses[0]?.postal_code ?? "") ||
          addrCountry !== (contact.addresses[0]?.country ?? "")
            ? saveContactAddress(contact.id, contact.addresses[0]?.id, {
                type_label: contact.addresses[0]?.type_label || "Business",
                line1: addrLine1,
                line2: addrLine2,
                city: addrCity,
                state: addrState,
                postal_code: addrPostal,
                country: addrCountry,
              })
            : Promise.resolve(),
        ]);
        toast.success("Contact record updated");
        setEditing(false);
        // The header name (and anything else read straight off `contact`
        // rather than its own local edit-form state, like full_name) never
        // updates on its own - updateContact's revalidatePath only marks
        // the route stale for the *next* navigation, it doesn't re-render
        // this already-mounted page. Without this, clearing the name
        // fields appeared to silently do nothing: saved fine, but the
        // header kept showing the old name until a manual reload.
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "We couldn't save your changes. Please try again."));
      }
    });
  }

  function handleCancel() {
    setFirstName(contact.first_name ?? "");
    setLastName(contact.last_name ?? "");
    setJobTitle(contact.job_title ?? "");
    setDepartment(contact.department ?? "");
    setCategory(contact.category ?? "");
    setReferredBy(contact.referred_by ?? "");
    setBirthdate(contact.birthdate ?? "");
    setPhone(contact.phones[0]?.number ?? "");
    setMobile(contact.phones[1]?.number ?? "");
    setPhoneType(firstPhoneType);
    setMobileType(secondPhoneType);
    setEmail(contact.emails[0]?.address ?? "");
    setAddrLine1(contact.addresses[0]?.line1 ?? "");
    setAddrLine2(contact.addresses[0]?.line2 ?? "");
    setAddrCity(contact.addresses[0]?.city ?? "");
    setAddrState(contact.addresses[0]?.state ?? "");
    setAddrPostal(contact.addresses[0]?.postal_code ?? "");
    setAddrCountry(contact.addresses[0]?.country ?? "");
    setCompany(contact.company ? { id: contact.company.id, label: contact.company.name } : null);
    setEditing(false);
  }


  const primaryAddress = contact.addresses[0];
  const website = contact.company?.website?.trim() || null;
  const primaryPhone = contact.phones[0]?.number;
  const mobilePhone = contact.phones[1]?.number;
  const primaryEmail = contact.emails[0]?.address;
  const secondaryEmail = contact.emails[1]?.address;

  return (
    <Card className="overflow-hidden border border-border/90 bg-card shadow-2xs">
      {/* Top Identity Header Bar */}
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/80 px-5 py-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Contact details</span>

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
            <>
              <ReassignContactButton contactId={contact.id} contactName={name} />
              <Button
                size="sm"
                variant="outline"
                onClick={() => setEditing(true)}
                className="h-7 text-xs gap-1.5 cursor-pointer font-medium hover:border-primary/50"
              >
                <Pencil className="size-3 text-muted-foreground" />
                <span>Edit Record</span>
              </Button>
            </>
          )}
        </div>
      </CardHeader>

      
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6 p-5 text-xs">
        {/* COLUMN 1: Business Card Details */}
        <div className="flex flex-col gap-2.5">
          <div className="border-b pb-1.5 mb-1 flex items-center justify-between">
            <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
              Business Card
            </span>
          </div>

          {editing ? (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-muted-foreground">First Name</label>
                <Input
                  className="h-7 text-xs"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground">Last Name</label>
                <Input
                  className="h-7 text-xs"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            </div>
          ) : null}

          {/* Company */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Company</span>
            {editing ? (
              <div className="flex-1">
                <EntityPicker
                  label="company"
                  placeholder="Search companies…"
                  search={async (q) => (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name }))}
                  value={company}
                  onChange={setCompany}
                  viewHref={(id) => `/companies/${id}`}
                />
              </div>
            ) : (
              <span className="font-semibold text-foreground truncate min-w-0 text-left">
                {contact.company ? (
                  <Link
                    href={`/companies/${contact.company.id}`}
                    className="text-primary hover:underline"
                  >
                    {contact.company.name}
                  </Link>
                ) : (
                  EMPTY
                )}
              </span>
            )}
          </div>

          {/* Job Title */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Title</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {contact.job_title || EMPTY}
              </span>
            )}
          </div>

          {/* Department */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Department</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {contact.department || EMPTY}
              </span>
            )}
          </div>

          {/* Phone */}
          <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-border/40">
            {editing ? (
              <PhoneTypeSelect value={phoneType} onChange={setPhoneType} label="Type of the first phone number" />
            ) : (
              <span className="w-24 shrink-0 text-muted-foreground">{contact.phones[0]?.type_label || "Phone"}</span>
            )}
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Phone number"
                aria-label="First phone number"
              />
            ) : primaryPhone ? (
              <div className="flex items-center gap-1.5">
                <a href={`tel:${primaryPhone}`} className="font-medium text-foreground hover:text-primary">
                  {primaryPhone}
                </a>
                <button
                  type="button"
                  onClick={() => copyText(primaryPhone, "phone number", "phone-main")}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {copiedKey === "phone-main" ? (
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

          {/* Second phone - shown with its own type */}
          <div className={editing ? ROW : ROW_VIEW}>
            {editing ? (
              <PhoneTypeSelect value={mobileType} onChange={setMobileType} label="Type of the second phone number" />
            ) : (
              <span className="w-24 shrink-0 text-muted-foreground">{contact.phones[1]?.type_label || "Phone 2"}</span>
            )}
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                placeholder="Phone number"
                aria-label="Second phone number"
              />
            ) : mobilePhone ? (
              <div className="flex items-center gap-1.5">
                <a href={`tel:${mobilePhone}`} className="font-medium text-foreground hover:text-primary">
                  {mobilePhone}
                </a>
                <button
                  type="button"
                  onClick={() => copyText(mobilePhone, "phone number", "phone-mob")}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {copiedKey === "phone-mob" ? (
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
          <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-border/40">
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
                  onClick={() => copyText(primaryEmail, "email", "email-main")}
                  className="text-muted-foreground hover:text-foreground cursor-pointer shrink-0"
                >
                  {copiedKey === "email-main" ? (
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

          {/* Alt E-mail */}
          {secondaryEmail && (
            <div className={editing ? ROW : ROW_VIEW}>
              <span className="w-24 shrink-0 text-muted-foreground">Alt E-mail</span>
              <a href={`mailto:${secondaryEmail}`} className="font-mono text-[11px] text-foreground hover:text-primary truncate max-w-[200px]">
                {secondaryEmail}
              </a>
            </div>
          )}
        </div>

        {/* COLUMN 2: Address & Web Details */}
        <div className="flex flex-col gap-2.5">
          <div className="border-b pb-1.5 mb-1 flex items-center justify-between">
            <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
              Address &amp; Web
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
            <span className="w-24 shrink-0 text-muted-foreground">State / County</span>
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

          {/* Web site - the company's own site, opened in a new tab */}
          <div className={`${ROW_VIEW} pt-1 border-t border-border/40`}>
            <span className="w-24 shrink-0 text-muted-foreground">Website</span>
            {website ? (
              <a
                href={websiteHref(website)}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-primary hover:underline truncate inline-flex min-w-0 items-center gap-1"
              >
                <span className="truncate">{website.replace(/^https?:\/\//i, "").replace(/\/$/, "")}</span>
                <ExternalLink className="size-3 shrink-0" aria-hidden="true" />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            ) : (
              EMPTY
            )}
          </div>
        </div>

        {/* COLUMN 3: Status & Cadence (Act! status block) */}
        <div className="flex flex-col gap-2.5">
          <div className="border-b pb-1.5 mb-1 flex items-center justify-between">
            <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
              Status &amp; Activity
            </span>
          </div>

          {/* ID/Status */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">ID/Status</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            ) : (
              contact.category ? (
                <Badge variant="secondary" className="font-semibold text-[11px]">
                  {contact.category}
                </Badge>
              ) : (
                EMPTY
              )
            )}
          </div>

          {/* Referred By */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Referred By</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={referredBy}
                onChange={(e) => setReferredBy(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {contact.referred_by || EMPTY}
              </span>
            )}
          </div>

          {/* Birthdate */}
          <div className={editing ? ROW : ROW_VIEW}>
            <span className="w-24 shrink-0 text-muted-foreground">Birthdate</span>
            {editing ? (
              <Input
                type="date"
                className="h-7 text-xs flex-1"
                value={birthdate}
                onChange={(e) => setBirthdate(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate min-w-0 text-left">
                {contact.birthdate ? new Date(contact.birthdate).toLocaleDateString("en-GB", { timeZone: "Europe/London" }) : EMPTY}
              </span>
            )}
          </div>

          {/* Activity Cadence Stats */}
          <div className="flex flex-col gap-1.5 pt-2 border-t border-border/40 text-[11px]">
            <div className="flex justify-between [&:has([data-empty])]:hidden">
              <span className="text-muted-foreground">Last Meeting</span>
              <span className="font-semibold text-foreground">
                {contact.last_meet_date
                  ? new Date(contact.last_meet_date).toLocaleDateString("en-GB", { timeZone: "Europe/London" })
                  : EMPTY}
              </span>
            </div>
            <div className="flex justify-between [&:has([data-empty])]:hidden">
              <span className="text-muted-foreground">Last Reach</span>
              <span className="font-semibold text-foreground">
                {contact.last_reach_date
                  ? new Date(contact.last_reach_date).toLocaleDateString("en-GB", { timeZone: "Europe/London" })
                  : EMPTY}
              </span>
            </div>
            <div className="flex justify-between [&:has([data-empty])]:hidden">
              <span className="text-muted-foreground">Last Attempt</span>
              <span className="font-semibold text-foreground">
                {contact.last_attempt_date
                  ? new Date(contact.last_attempt_date).toLocaleDateString("en-GB", { timeZone: "Europe/London" })
                  : EMPTY}
              </span>
            </div>
            <div className="flex justify-between [&:has([data-empty])]:hidden">
              <span className="text-muted-foreground">Letter Sent</span>
              <span className="font-semibold text-foreground">
                {contact.last_letter_date
                  ? new Date(contact.last_letter_date).toLocaleDateString("en-GB", { timeZone: "Europe/London" })
                  : EMPTY}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
