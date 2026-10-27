"use client";

import Link from "next/link";
import { Copy, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

export type SubscribeForm = { key: string; title: string; tool: string; received: number; address: string };

const WHERE: Record<string, string> = {
  Wufoo: "In Wufoo: the form's Integrations, then WebHook. Paste the address and tick “Include Field and Form Structures with Entry Data”.",
  "WordPress (Elementor)": "In WordPress: edit the subscribe page in Elementor, select the form, then Actions After Submit, add Webhook and paste the address. Turn on Advanced Data.",
  Stova: "In Stova: paste the address where the form can send each registration on (a webhook), if it has one.",
};

/** Where each title's subscribe form sends its sign-ups (Lead & Contact Capture). Each address is that form's
 * secret, so it's only shown to administrators and data managers. */
export function SubscribeFormAddresses({ forms }: { forms: SubscribeForm[] }) {
  const copy = (text: string) =>
    navigator.clipboard.writeText(text).then(() => toast.success("Copied")).catch(() => toast.error("Couldn't copy - select the address and copy it instead"));
  return (
    <section aria-labelledby="subscribe-heading" className="flex flex-col gap-3 rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="subscribe-heading" className="flex items-center gap-1.5 text-sm font-bold text-foreground">
          <UserPlus className="size-4 text-muted-foreground" aria-hidden="true" /> Subscription sign-ups
        </h2>
        <Link href="/automations/review?kind=subscription_signup" target="_blank" rel="noreferrer" className="text-xs font-semibold text-primary hover:underline">
          See the sign-ups waiting
        </Link>
      </div>
      <p className="text-xs text-muted-foreground">
        Each subscribe form sends its sign-ups to its own address below. Each one becomes a card in the Review Queue, checked for people already on the database, personal email addresses and overseas print requests. Keep these addresses private.
      </p>
      <ul className="flex flex-col gap-2">
        {forms.map((f) => (
          <li key={f.key} className="flex flex-col gap-1.5 rounded-lg border border-border/70 p-3 text-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-semibold">{f.title} <span className="text-xs font-normal text-muted-foreground">· {f.tool}</span></p>
              <span className="text-xs text-muted-foreground">{f.received ? `${f.received} sign-up${f.received === 1 ? "" : "s"} so far` : "No sign-ups yet"}</span>
            </div>
            <div className="flex items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded-md bg-muted px-2 py-1 text-xs">{f.address}</code>
              <Button size="sm" variant="outline" className="shrink-0 gap-1.5" onClick={() => copy(f.address)}>
                <Copy className="size-3.5" aria-hidden="true" /> Copy address
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">{WHERE[f.tool] ?? "Paste the address where the form can send each entry on."}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
