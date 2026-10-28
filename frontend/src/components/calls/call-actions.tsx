"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BookmarkCheck, FileText, Loader2, Sparkles, Square } from "lucide-react";
import { toast } from "sonner";
import type { Call } from "@/lib/calls-types";
import { LIVE_STATUSES } from "@/lib/calls-types";
import { linkCall, makePitchFromCall, saveCallToHistory, stopNotetaker } from "@/lib/calls-actions";
import { searchContacts } from "@/lib/actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { EntityPicker } from "@/components/entity-picker";

type Option = { id: string; label: string; sublabel?: string | null };

export function CallActions({ call }: { call: Call }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [contact, setContact] = useState<Option | null>(call.contact ? { id: call.contact.id, label: call.contact.name ?? "Contact" } : null);

  const run = (fn: () => Promise<unknown>, ok: string, fallback: string) =>
    start(async () => {
      try { await fn(); toast.success(ok); router.refresh(); } catch (e) { toast.error(friendlyError(e, fallback)); }
    });

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="w-64">
        <EntityPicker label="Contact" placeholder="Link to a contact…"
          search={async (q) => (await searchContacts(q)).map((c) => ({ id: c.id, label: c.full_name ?? "Unnamed", sublabel: c.company_name }))}
          value={contact}
          onChange={(v) => { setContact(v); run(() => linkCall(call.id, { contact_id: v?.id ?? null }), v ? "Linked to the contact" : "Unlinked", "Couldn't link the call"); }}
          viewHref={(id) => `/contacts/${id}`} />
      </div>
      {LIVE_STATUSES.includes(call.status) && call.status !== "processing" && (
        <Button variant="outline" className="gap-1.5" disabled={pending} onClick={() => run(() => stopNotetaker(call.id), "The notetaker is leaving the call - the notes follow in a few minutes", "Couldn't stop the notetaker")}>
          <Square className="size-3.5" /> Stop recording
        </Button>
      )}
      {call.status === "completed" && call.notes && (
        call.saved_to_history_at ? (
          <span className="inline-flex items-center gap-1 text-xs font-semibold" style={{ color: "var(--ok)" }}><BookmarkCheck className="size-3.5" /> Saved to the contact&apos;s history</span>
        ) : (
          <Button className="gap-1.5" disabled={pending || !contact} title={contact ? undefined : "Link a contact first"}
            onClick={() => run(() => saveCallToHistory(call.id), "Saved to the contact's history, with a reminder for each thing to do", "Couldn't save the notes")}>
            {pending ? <Loader2 className="size-3.5 animate-spin" /> : <BookmarkCheck className="size-3.5" />} Save to history
          </Button>
        )
      )}
      {call.status === "completed" && call.notes && (
        call.pitch_proposal_id ? (
          <Button variant="outline" className="gap-1.5" nativeButton={false} render={<Link href={`/sales/proposals/${call.pitch_proposal_id}`} />}>
            <FileText className="size-3.5" /> Open the pitch
          </Button>
        ) : (
          <Button variant="outline" className="gap-1.5" disabled={pending || !call.can_pitch} title={call.can_pitch ? "A proposal draft that answers what the client said on this call" : "Link the call to a contact at the client's company first"}
            onClick={() => start(async () => {
              try {
                const r = await makePitchFromCall(call.id);
                toast.success("Pitch drafted from the call - check it before sending");
                router.push(r.href);
              } catch (e) { toast.error(friendlyError(e, "Couldn't make a pitch from this call")); }
            })}>
            {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />} Make a pitch
          </Button>
        )
      )}
    </div>
  );
}
