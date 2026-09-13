"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Building2,
  Calendar,
  Check,
  Copy,
  ExternalLink,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import type { ContactDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EntityAvatar } from "@/components/entity-avatar";
import { sourceLabel } from "@/lib/sources";
import { AddressBlock } from "@/components/address-block";
import { ContactGroupsEditor } from "@/components/contact-groups-editor";

export function ContactDossier({
  contact,
  onEditToggle,
}: {
  contact: ContactDetail;
  onEditToggle?: () => void;
}) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

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

  const publicationBadgeStyle = (source: string) => {
    switch (source) {
      case "onboard":
        return "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400";
      case "sellingtravel":
        return "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
      case "prospects":
        return "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400";
      default:
        return "border-border bg-muted text-muted-foreground";
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Identity Profile Card */}
      <Card className="editorial-card overflow-hidden">
        {/* Subtle decorative top bar */}
        <div className="h-2 w-full bg-gradient-to-r from-amber-600/60 via-primary to-amber-700/60" />

        <CardHeader className="p-5 pb-4">
          <div className="flex items-start justify-between gap-3">
            <EntityAvatar
              name={name}
              className="size-14 text-base font-semibold border-2 border-background shadow-xs ring-1 ring-border"
            />
            <div className="flex items-center gap-1.5">
              <Badge
                variant="outline"
                className={`text-[11px] font-medium ${publicationBadgeStyle(
                  contact.source_db
                )}`}
              >
                {sourceLabel(contact.source_db)}
              </Badge>
              {onEditToggle && (
                <Button
                  size="icon-xs"
                  variant="ghost"
                  onClick={onEditToggle}
                  title="Edit details"
                  className="cursor-pointer"
                >
                  <Pencil className="size-3.5 text-muted-foreground" />
                </Button>
              )}
            </div>
          </div>

          <div className="mt-3">
            <h2 className="editorial-title text-xl font-bold tracking-tight text-foreground">
              {name}
            </h2>
            {contact.job_title && (
              <p className="text-xs font-medium text-muted-foreground mt-0.5">
                {contact.job_title}
              </p>
            )}
            {contact.company && (
              <Link
                href={`/companies/${contact.company.id}`}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline mt-1.5"
              >
                <Building2 className="size-3.5 shrink-0" />
                <span>{contact.company.name}</span>
              </Link>
            )}
          </div>
        </CardHeader>

        <CardContent className="flex flex-col gap-4 p-5 pt-0 text-xs">
          {/* Quick Contact Points */}
          <div className="flex flex-col gap-2 rounded-md border border-border/80 bg-muted/40 p-3">
            {contact.emails.map((e, idx) => (
              <div
                key={e.id || idx}
                className="group flex items-center justify-between gap-2"
              >
                <a
                  href={`mailto:${e.address}`}
                  className="flex items-center gap-2 truncate text-foreground hover:text-primary"
                >
                  <Mail className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate">{e.address}</span>
                </a>
                <button
                  type="button"
                  onClick={() => copyText(e.address ?? "", "email", `email-${idx}`)}
                  className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 cursor-pointer"
                  title="Copy email"
                >
                  {copiedKey === `email-${idx}` ? (
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </button>
              </div>
            ))}

            {contact.phones.map((p, idx) => (
              <div
                key={p.id || idx}
                className="group flex items-center justify-between gap-2"
              >
                <a
                  href={`tel:${p.number}`}
                  className="flex items-center gap-2 truncate text-foreground hover:text-primary"
                >
                  <Phone className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate">{p.number}</span>
                </a>
                <button
                  type="button"
                  onClick={() => copyText(p.number ?? "", "phone", `phone-${idx}`)}
                  className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 cursor-pointer"
                  title="Copy phone"
                >
                  {copiedKey === `phone-${idx}` ? (
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </button>
              </div>
            ))}

            {contact.addresses.map((a, idx) => (
              <div key={a.id || idx} className="flex items-start gap-2 pt-1">
                <MapPin className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                <div className="flex-1 text-[11px] text-muted-foreground">
                  <AddressBlock address={a} />
                </div>
              </div>
            ))}

            {contact.emails.length === 0 &&
              contact.phones.length === 0 &&
              contact.addresses.length === 0 && (
                <span className="text-muted-foreground italic">
                  No contact channels on file.
                </span>
              )}
          </div>

          {/* Activity Cadence Stats */}
          {(contact.last_meet_date ||
            contact.last_reach_date ||
            contact.last_attempt_date) && (
            <div className="grid grid-cols-2 gap-2 border-t pt-3 text-[11px]">
              {contact.last_reach_date && (
                <div>
                  <span className="text-muted-foreground">Last Reach: </span>
                  <span className="font-medium text-foreground">
                    {new Date(contact.last_reach_date).toLocaleDateString()}
                  </span>
                </div>
              )}
              {contact.last_meet_date && (
                <div>
                  <span className="text-muted-foreground">Last Meeting: </span>
                  <span className="font-medium text-foreground">
                    {new Date(contact.last_meet_date).toLocaleDateString()}
                  </span>
                </div>
              )}
              {contact.last_attempt_date && (
                <div>
                  <span className="text-muted-foreground">Last Attempt: </span>
                  <span className="font-medium text-foreground">
                    {new Date(contact.last_attempt_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Group Memberships */}
          <div className="border-t pt-3">
            <span className="text-[11px] font-semibold text-muted-foreground block mb-2">
              Assigned Publishing Groups
            </span>
            <ContactGroupsEditor contactId={contact.id} groups={contact.groups} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
