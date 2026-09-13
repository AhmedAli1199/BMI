"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Building2,
  Calendar,
  Check,
  Copy,
  ExternalLink,
  Eye,
  Mail,
  Phone,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";
import type { ContactListItem } from "@/lib/types";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EntityAvatar } from "@/components/entity-avatar";
import { sourceLabel } from "@/lib/sources";

export function ContactPreviewDrawer({
  contact,
  open,
  onOpenChange,
}: {
  contact: ContactListItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);

  if (!contact) return null;

  const name =
    contact.full_name ||
    [contact.first_name, contact.last_name].filter(Boolean).join(" ") ||
    "(no name)";

  function copyEmail() {
    if (!contact?.primary_email) return;
    navigator.clipboard.writeText(contact.primary_email);
    setCopied(true);
    toast.success("Email copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
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
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md p-6 flex flex-col justify-between overflow-y-auto"
      >
        <div className="flex flex-col gap-6">
          <SheetHeader className="text-left">
            <div className="flex items-center justify-between gap-3">
              <Badge
                variant="outline"
                className={`text-xs font-semibold ${publicationBadgeStyle(
                  contact.source_db
                )}`}
              >
                {sourceLabel(contact.source_db)}
              </Badge>
              <Link
                href={`/contacts/${contact.id}`}
                className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
              >
                <span>Full Record</span>
                <ExternalLink className="size-3" />
              </Link>
            </div>

            <div className="mt-4 flex items-start gap-4">
              <EntityAvatar name={name} className="size-14 text-base font-bold" />
              <div className="flex flex-col">
                <SheetTitle className="editorial-title text-xl font-bold text-foreground">
                  {name}
                </SheetTitle>
                {contact.job_title && (
                  <p className="text-xs font-medium text-muted-foreground mt-0.5">
                    {contact.job_title}
                  </p>
                )}
                {contact.company_name && (
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-primary font-medium">
                    <Building2 className="size-3.5" />
                    <span>{contact.company_name}</span>
                  </div>
                )}
              </div>
            </div>
          </SheetHeader>

          {/* Quick Communication Card */}
          <div className="rounded-lg border border-border bg-muted/30 p-4 flex flex-col gap-3">
            <span className="text-xs font-bold text-foreground">
              Direct Channels
            </span>

            {contact.primary_email ? (
              <div className="flex items-center justify-between gap-2 rounded bg-background p-2.5 border border-border/70 text-xs">
                <a
                  href={`mailto:${contact.primary_email}`}
                  className="flex items-center gap-2 truncate text-foreground hover:text-primary font-mono text-[11px]"
                >
                  <Mail className="size-3.5 text-muted-foreground shrink-0" />
                  <span className="truncate">{contact.primary_email}</span>
                </a>
                <button
                  type="button"
                  onClick={copyEmail}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                  title="Copy email"
                >
                  {copied ? (
                    <Check className="size-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                </button>
              </div>
            ) : (
              <span className="text-xs text-muted-foreground italic">
                No direct email recorded
              </span>
            )}
          </div>

          {/* Editorial Quick Actions */}
          <div className="flex flex-col gap-2">
            <span className="text-xs font-bold text-foreground">
              Editorial Workflows
            </span>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <Link
                href={`/contacts/${contact.id}`}
                className="flex items-center justify-center gap-2 rounded-md border border-border bg-card p-2.5 font-medium hover:border-primary/50 transition-colors"
              >
                <Eye className="size-3.5 text-primary" />
                <span>View Timeline</span>
              </Link>
              {contact.primary_email && (
                <a
                  href={`mailto:${contact.primary_email}?subject=BMI Publishing — Editorial Enquiry`}
                  className="flex items-center justify-center gap-2 rounded-md border border-border bg-card p-2.5 font-medium hover:border-primary/50 transition-colors"
                >
                  <Mail className="size-3.5 text-blue-600" />
                  <span>Draft Email</span>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Footer Link to Full Dossier */}
        <div className="border-t pt-4 mt-6">
          <Link
            href={`/contacts/${contact.id}`}
            className="flex items-center justify-center w-full gap-2 rounded-lg bg-primary py-2.5 px-4 text-xs font-semibold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors cursor-pointer"
          >
            <span>Open 3-Zone Workspace</span>
            <ExternalLink className="size-4" />
          </Link>
        </div>
      </SheetContent>
    </Sheet>
  );
}
