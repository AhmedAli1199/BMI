"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Bot, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { sendNotetaker } from "@/lib/calls-actions";
import { searchContacts } from "@/lib/actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EntityPicker } from "@/components/entity-picker";
import { InfoHint } from "@/components/sales/info-hint";

type Option = { id: string; label: string; sublabel?: string | null };

/** Paste a Meet, Teams or Zoom link and the notetaker joins the call. */
export function SendNotetaker({ initialContact = null, compact = false }: { initialContact?: Option | null; compact?: boolean }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [contact, setContact] = useState<Option | null>(initialContact);
  const [pending, start] = useTransition();
  const labelCls = "flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted-foreground";

  function send() {
    start(async () => {
      try {
        const c = await sendNotetaker({ meeting_url: url.trim(), title: title.trim() || null, contact_id: contact?.id ?? null });
        toast.success("The notetaker is on its way - let it in when it asks to join");
        setUrl(""); setTitle("");
        router.push(`/calls/${c.id}`);
      } catch (e) {
        toast.error(friendlyError(e, "The notetaker couldn't be sent. Check the link and try again."));
      }
    });
  }

  return (
    <section aria-labelledby="send-nt" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
      <h2 id="send-nt" className="mb-3 flex items-center gap-1.5 text-sm font-bold">
        <Bot className="size-4 text-primary" aria-hidden="true" /> Send the notetaker
        <InfoHint>It joins the call as &quot;BMI Notetaker&quot;, records it, and when the call ends you get the notes and the full transcript here. Someone in the call may need to let it in. For Zoom, connect your Zoom first (under Your calendars) and stay in the call: Zoom only lets it in with you there.</InfoHint>
      </h2>
      <div className={`grid gap-3 ${compact ? "" : "md:grid-cols-[2fr_1fr_1.2fr_auto]"} items-end`}>
        <label className={labelCls}>Meeting link<Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://meet.google.com/…, a Teams or a Zoom link" /></label>
        <label className={labelCls}>What it&apos;s about (optional)<Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Spring campaign" /></label>
        <div className={labelCls}>
          <EntityPicker label="Who it's with (optional)" placeholder="Search contacts…"
            search={async (q) => (await searchContacts(q)).map((c) => ({ id: c.id, label: c.full_name ?? "Unnamed", sublabel: c.company_name }))}
            value={contact} onChange={setContact} viewHref={(id) => `/contacts/${id}`} />
        </div>
        <Button disabled={pending || !url.trim()} onClick={send} className="gap-1.5">
          {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Bot className="size-3.5" />} Send
        </Button>
      </div>
    </section>
  );
}
