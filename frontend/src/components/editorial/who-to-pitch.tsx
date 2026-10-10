"use client";

import { useState } from "react";
import Link from "next/link";
import { ExternalLink, Mail, Send, Users } from "lucide-react";
import { EmailFromTemplate } from "@/components/mail-merge/email-from-template";
import type { PitchCompany, PitchList } from "@/lib/editorial-types";
import { Button } from "@/components/ui/button";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";

type Tab = "lapsed" | "previous" | "feature_matches";

/** Who to approach for this issue - every company opens in a new tab so the list stays put. */
export function WhoToPitch({ pitch, open }: { pitch: PitchList; open: boolean }) {
  const tabs: { key: Tab; label: string; hint: string }[] = [
    { key: "lapsed", label: "Haven't rebooked", hint: pitch.compared_with ? `Booked ${pitch.compared_with.label} (${pitch.compared_with.year}) but nothing in this issue yet.` : "Last year's equivalent issue isn't in the plan, so there's no one to compare with." },
    { key: "previous", label: "Booked the last issue", hint: "Advertised in the issue before this one but haven't booked this one." },
    { key: "feature_matches", label: "Fit a feature", hint: "Past advertisers in this title whose line of business matches the words in a planned feature. A starting point - check before you call." },
  ];
  const first = tabs.find((t) => pitch[t.key].length > 0)?.key ?? "lapsed";
  const [tab, setTab] = useState<Tab>(first);
  const total = pitch.lapsed.length + pitch.previous.length + pitch.feature_matches.length;
  const rows = pitch[tab];
  const current = tabs.find((t) => t.key === tab)!;
  const [emailTo, setEmailTo] = useState<PitchCompany | null>(null);

  return (
    <section aria-labelledby="wp-h" className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
      <header className="flex flex-wrap items-center gap-2 border-b border-border/70 px-4 py-3">
        <Users className="size-4 text-muted-foreground" aria-hidden="true" />
        <h2 id="wp-h" className="text-sm font-bold">Who should we pitch?</h2>
        <InfoHint>Worked out from the order register. Anyone who has already booked this issue ({pitch.already_booked} so far) is left off. Click a name to open the company in a new tab.</InfoHint>
        {!open && <span className="ml-auto text-xs text-muted-foreground">Advertising has closed for this issue.</span>}
      </header>
      {total === 0 ? (
        <p className="px-4 py-4 text-sm text-muted-foreground">No one to suggest yet - there are no earlier bookings to compare with.</p>
      ) : (
        <>
          <div role="tablist" aria-label="Kinds of suggestion" className="flex flex-wrap gap-1 border-b border-border/70 px-3 py-2">
            {tabs.map((t) => (
              <button key={t.key} role="tab" type="button" aria-selected={tab === t.key} onClick={() => setTab(t.key)}
                className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${tab === t.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}>
                {t.label} ({pitch[t.key].length})
              </button>
            ))}
          </div>
          <p className="px-4 pt-3 text-xs text-muted-foreground">{current.hint}</p>
          {rows.length === 0 ? (
            <p className="px-4 py-4 text-sm text-muted-foreground">Nobody here.</p>
          ) : (
            <ul className="divide-y divide-border/60">
              {rows.map((c) => <PitchRow key={`${c.company_id ?? c.name}`} c={c} issueId={pitch.issue_id} titleId={pitch.title_id ?? null} open={open} onEmail={setEmailTo} />)}
            </ul>
          )}
        </>
      )}
      {emailTo && (
        <EmailFromTemplate open={!!emailTo} onOpenChange={(o) => !o && setEmailTo(null)} companyId={emailTo.company_id}
          titleId={pitch.title_id ?? null} editionId={pitch.issue_id} feature={emailTo.feature ?? null} />
      )}
    </section>
  );
}

function PitchRow({ c, issueId, open, onEmail }: { c: PitchCompany; issueId: string; titleId: string | null; open: boolean; onEmail: (c: PitchCompany) => void }) {
  const last = [c.last_size, c.last_value_gbp != null ? fmtGBP(c.last_value_gbp) : null, c.last_booked ? `booked ${fmtDate(c.last_booked)}` : null].filter(Boolean).join(" · ");
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm">
      <div className="min-w-0 flex-1">
        {c.company_id ? (
          <Link href={`/companies/${c.company_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-primary hover:underline">
            {c.name} <ExternalLink className="size-3" aria-hidden="true" />
          </Link>
        ) : (
          <span className="font-semibold">{c.name} <span className="text-xs font-normal text-muted-foreground">(not linked to a CRM company yet)</span></span>
        )}
        <p className="text-xs text-muted-foreground">{c.reason}{last ? ` · ${last}` : ""}{c.rep ? ` · ${c.rep}` : ""}</p>
      </div>
      {open && c.company_id && (
        <Button size="sm" variant="outline" className="gap-1.5" onClick={() => onEmail(c)}><Mail className="size-3.5" /> Email</Button>
      )}
      {open && c.company_id && (
        <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false}
          render={<Link href={`/sales/proposals/new?company=${c.company_id}&edition=${issueId}`} target="_blank" rel="noreferrer" />}>
          <Send className="size-3.5" /> Draft a proposal
        </Button>
      )}
    </li>
  );
}
