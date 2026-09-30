"use client";

import { Sparkles } from "lucide-react";
import { LogInteractionDialog } from "@/components/log-interaction-dialog";

/** The collapsed "log something" bar shown above a record's activity/notes
 * tabs - opens LogInteractionDialog pinned to this contact or company. */
export function TouchpointBar({
  contactId,
  companyId,
  contactName,
  sourceDb,
}: {
  contactId?: string;
  companyId?: string;
  contactName: string;
  sourceDb: string;
}) {
  return (
    <LogInteractionDialog
      contactId={contactId}
      companyId={companyId}
      contactName={contactName}
      sourceDb={sourceDb}
      trigger={
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-card p-3 shadow-xs cursor-pointer hover:border-primary/40 transition-colors">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="size-3.5 text-primary" />
            <span>Quick Touchpoint with {contactName.split(" ")[0]}</span>
          </div>
          <span className="text-xs font-semibold text-primary">Log or schedule &rarr;</span>
        </div>
      }
    />
  );
}
