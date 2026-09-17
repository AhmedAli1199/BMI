"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import {
  Building2,
  Calendar,
  Check,
  Copy,
  ExternalLink,
  Globe,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Save,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import type { ContactDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EntityAvatar } from "@/components/entity-avatar";
import { sourceLabel, sourceBadgeStyle as publicationBadgeStyle } from "@/lib/sources";
import { updateContact } from "@/lib/actions";

export function ActContactCard({
  contact,
}: {
  contact: ContactDetail;
}) {
  const [editing, setEditing] = useState(false);
  const [pending, startTransition] = useTransition();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Editable Form State
  const [firstName, setFirstName] = useState(contact.first_name ?? "");
  const [lastName, setLastName] = useState(contact.last_name ?? "");
  const [jobTitle, setJobTitle] = useState(contact.job_title ?? "");
  const [department, setDepartment] = useState(contact.department ?? "");
  const [category, setCategory] = useState(contact.category ?? "");
  const [referredBy, setReferredBy] = useState(contact.referred_by ?? "");
  const [birthdate, setBirthdate] = useState(contact.birthdate ?? "");

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
        await updateContact(contact.id, {
          first_name: firstName,
          last_name: lastName,
          job_title: jobTitle,
          department,
          category,
          referred_by: referredBy,
          birthdate,
        });
        toast.success("Contact record updated");
        setEditing(false);
      } catch {
        toast.error("Failed to save changes");
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
    setEditing(false);
  }


  const primaryAddress = contact.addresses[0];
  const primaryPhone = contact.phones[0]?.number;
  const mobilePhone = contact.phones[1]?.number;
  const primaryEmail = contact.emails[0]?.address;
  const secondaryEmail = contact.emails[1]?.address;

  return (
    <Card className="overflow-hidden border border-border/90 bg-card shadow-2xs">
      {/* Top Identity Header Bar */}
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/80 bg-muted/20 px-5 py-3">
        <div className="flex items-center gap-3.5">
          <EntityAvatar
            name={name}
            className="size-10 text-sm font-bold border border-border shadow-xs"
          />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="editorial-title text-xl font-bold tracking-tight text-foreground">
                {name}
              </h1>
              <Badge
                variant="outline"
                className={`text-[11px] font-medium ${publicationBadgeStyle(
                  contact.source_db
                )}`}
              >
                {sourceLabel(contact.source_db)}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {contact.job_title && <span>{contact.job_title}</span>}
              {contact.job_title && contact.company && <span>·</span>}
              {contact.company && (
                <Link
                  href={`/companies/${contact.company.id}`}
                  className="font-semibold text-primary hover:underline inline-flex items-center gap-1"
                >
                  <Building2 className="size-3" />
                  <span>{contact.company.name}</span>
                </Link>
              )}
            </div>
          </div>
        </div>

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
              <span>Edit Record</span>
            </Button>
          )}
        </div>
      </CardHeader>

      {/* The Iconic ACT! 3-Column Upper Form Card */}
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
          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Company:</span>
            <span className="font-semibold text-foreground truncate flex-1 text-right">
              {contact.company ? (
                <Link
                  href={`/companies/${contact.company.id}`}
                  className="text-primary hover:underline"
                >
                  {contact.company.name}
                </Link>
              ) : (
                "—"
              )}
            </span>
          </div>

          {/* Job Title */}
          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Title:</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate flex-1 text-right">
                {contact.job_title || "—"}
              </span>
            )}
          </div>

          {/* Department */}
          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Department:</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate flex-1 text-right">
                {contact.department || "—"}
              </span>
            )}
          </div>

          {/* Phone */}
          <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-border/40">
            <span className="w-24 shrink-0 text-muted-foreground">Phone:</span>
            {primaryPhone ? (
              <div className="flex items-center gap-1.5">
                <a href={`tel:${primaryPhone}`} className="font-medium text-foreground hover:text-primary">
                  {primaryPhone}
                </a>
                <button
                  type="button"
                  onClick={() => copyText(primaryPhone, "phone", "phone-main")}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {copiedKey === "phone-main" ? (
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </button>
              </div>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </div>

          {/* Mobile */}
          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Mobile:</span>
            {mobilePhone ? (
              <div className="flex items-center gap-1.5">
                <a href={`tel:${mobilePhone}`} className="font-medium text-foreground hover:text-primary">
                  {mobilePhone}
                </a>
                <button
                  type="button"
                  onClick={() => copyText(mobilePhone, "mobile", "phone-mob")}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {copiedKey === "phone-mob" ? (
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </button>
              </div>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </div>

          {/* E-mail */}
          <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-border/40">
            <span className="w-24 shrink-0 text-muted-foreground">E-mail:</span>
            {primaryEmail ? (
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
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </button>
              </div>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </div>

          {/* Alt E-mail */}
          {secondaryEmail && (
            <div className="flex items-baseline justify-between gap-2">
              <span className="w-24 shrink-0 text-muted-foreground">Alt E-mail:</span>
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

          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Address 1:</span>
            <span className="font-medium text-foreground truncate flex-1 text-right">
              {primaryAddress?.line1 || "—"}
            </span>
          </div>

          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Address 2:</span>
            <span className="font-medium text-foreground truncate flex-1 text-right">
              {primaryAddress?.line2 || "—"}
            </span>
          </div>

          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">City:</span>
            <span className="font-medium text-foreground truncate flex-1 text-right">
              {primaryAddress?.city || "—"}
            </span>
          </div>

          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">State / County:</span>
            <span className="font-medium text-foreground truncate flex-1 text-right">
              {primaryAddress?.state || "—"}
            </span>
          </div>

          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Postal Code:</span>
            <span className="font-mono font-medium text-foreground truncate flex-1 text-right">
              {primaryAddress?.postal_code || "—"}
            </span>
          </div>

          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Country:</span>
            <span className="font-medium text-foreground truncate flex-1 text-right">
              {primaryAddress?.country || "—"}
            </span>
          </div>

          {/* Web Site */}
          <div className="flex items-baseline justify-between gap-2 pt-1 border-t border-border/40">
            <span className="w-24 shrink-0 text-muted-foreground">Web Site:</span>
            {contact.company?.id ? (
              <Link
                href={`/companies/${contact.company.id}`}
                className="font-medium text-primary hover:underline truncate inline-flex items-center gap-1"
              >
                <span>Company Profile</span>
                <ExternalLink className="size-3" />
              </Link>
            ) : (
              <span className="text-muted-foreground">—</span>
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
          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">ID/Status:</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            ) : (
              <Badge variant="secondary" className="font-semibold text-[11px]">
                {contact.category || "Standard"}
              </Badge>
            )}
          </div>

          {/* Referred By */}
          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Referred By:</span>
            {editing ? (
              <Input
                className="h-7 text-xs flex-1"
                value={referredBy}
                onChange={(e) => setReferredBy(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate flex-1 text-right">
                {contact.referred_by || "—"}
              </span>
            )}
          </div>

          {/* Birthdate */}
          <div className="flex items-baseline justify-between gap-2">
            <span className="w-24 shrink-0 text-muted-foreground">Birthdate:</span>
            {editing ? (
              <Input
                type="date"
                className="h-7 text-xs flex-1"
                value={birthdate}
                onChange={(e) => setBirthdate(e.target.value)}
              />
            ) : (
              <span className="font-medium text-foreground truncate flex-1 text-right">
                {contact.birthdate ? new Date(contact.birthdate).toLocaleDateString() : "—"}
              </span>
            )}
          </div>

          {/* Activity Cadence Stats */}
          <div className="flex flex-col gap-1.5 pt-2 border-t border-border/40 text-[11px]">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last Meeting:</span>
              <span className="font-semibold text-foreground">
                {contact.last_meet_date
                  ? new Date(contact.last_meet_date).toLocaleDateString()
                  : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last Reach:</span>
              <span className="font-semibold text-foreground">
                {contact.last_reach_date
                  ? new Date(contact.last_reach_date).toLocaleDateString()
                  : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last Attempt:</span>
              <span className="font-semibold text-foreground">
                {contact.last_attempt_date
                  ? new Date(contact.last_attempt_date).toLocaleDateString()
                  : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Letter Sent:</span>
              <span className="font-semibold text-foreground">
                {contact.last_letter_date
                  ? new Date(contact.last_letter_date).toLocaleDateString()
                  : "—"}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
