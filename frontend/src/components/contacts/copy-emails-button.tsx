"use client";

import { useTransition } from "react";
import { Copy } from "lucide-react";
import { toast } from "sonner";
import type { ContactScope } from "@/lib/contact-tools-types";
import { getEmailAddresses } from "@/lib/contact-tools-actions";
import { Button } from "@/components/ui/button";

/** "Copy email addresses": the addresses for a search or ticked contacts, ready to paste into
 * Outlook's Bcc box. People who unsubscribed or whose address bounced are left out, and we say how many. */
export function CopyEmailsButton({ scope, size = "sm", variant = "outline", label = "Copy emails" }: { scope: ContactScope; size?: "sm" | "default"; variant?: "outline" | "ghost"; label?: string }) {
  const [pending, start] = useTransition();

  function copy() {
    start(async () => {
      try {
        const r = await getEmailAddresses(scope);
        if (r.addresses.length === 0) {
          toast.error("None of these contacts has an email address we can use.");
          return;
        }
        await navigator.clipboard.writeText(r.text);
        const left = [
          r.skipped_unsubscribed && `${r.skipped_unsubscribed} unsubscribed`,
          r.skipped_bounced && `${r.skipped_bounced} bounced`,
          r.skipped_no_email && `${r.skipped_no_email} with no email`,
          r.duplicates_removed && `${r.duplicates_removed} repeated`,
        ].filter(Boolean);
        toast.success(`Copied ${r.addresses.length.toLocaleString()} email address${r.addresses.length === 1 ? "" : "es"} - paste them into Bcc.`, {
          description: [left.length ? `Left out: ${left.join(", ")}.` : "", r.addresses.length > 500 ? "Outlook only sends to about 500 people at once, so send in batches." : ""].filter(Boolean).join(" ") || undefined,
          duration: 8000,
        });
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't copy the addresses");
      }
    });
  }

  return (
    <Button size={size} variant={variant} onClick={copy} disabled={pending} title="Copy these contacts' email addresses, ready to paste into Outlook's Bcc box">
      <Copy className="size-3.5" /> {label}
    </Button>
  );
}
