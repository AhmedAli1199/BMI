"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Globe } from "lucide-react";
import { toast } from "sonner";
import type { BrandTitle } from "@/lib/rate-card-types";
import { saveTitleLinks } from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";
import { friendlyError } from "@/lib/errors";

const example = (t: string) => t.replace("{edition}", "105").replace("{year}", String(new Date().getFullYear())).replace("{page}", "23");

/** Where each part of the brand can be read online - renewal emails link advertisers back to last year's ad. */
export function OnlineLinks({ titles, canEdit }: { titles: BrandTitle[]; canEdit: boolean }) {
  return (
    <section aria-labelledby="links-h" className="rounded-xl border border-border/80 bg-card shadow-2xs print-hide">
      <details>
        <summary className="flex cursor-pointer items-center gap-1.5 px-4 py-3 text-sm font-bold">
          <Globe className="size-4 text-muted-foreground" aria-hidden="true" />
          <span id="links-h">Online edition links</span>
          <InfoHint>
            Renewal emails link the advertiser to last year&apos;s ad. Use {"{edition}"} (the edition name, e.g. 105), {"{year}"} and {"{page}"} (the page number from the order register).
            If the page isn&apos;t known the issue link is used; an edition&apos;s own link (set on its page) overrides both.
          </InfoHint>
          <span className="ml-auto text-xs font-normal text-muted-foreground">{titles.filter((t) => t.digital_issue_url || t.digital_page_url).length} of {titles.length} set</span>
        </summary>
        <ul className="divide-y divide-border/60 border-t border-border/70">
          {titles.map((t) => <TitleLinks key={t.id} title={t} canEdit={canEdit} />)}
        </ul>
      </details>
    </section>
  );
}

function TitleLinks({ title, canEdit }: { title: BrandTitle; canEdit: boolean }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [page, setPage] = useState(title.digital_page_url ?? "");
  const [issue, setIssue] = useState(title.digital_issue_url ?? "");
  const dirty = page !== (title.digital_page_url ?? "") || issue !== (title.digital_issue_url ?? "");
  return (
    <li className="grid gap-3 px-4 py-3 md:grid-cols-[12rem_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-start">
      <p className="text-sm font-semibold">{title.name}</p>
      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Link to a page in an issue
        <Input value={page} onChange={(e) => setPage(e.target.value)} disabled={!canEdit} placeholder="https://…/{edition}/page/{page}" className="h-8 text-sm" />
        {page && <span className="truncate text-[11px]">e.g. {example(page)}</span>}
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Link to an issue
        <Input value={issue} onChange={(e) => setIssue(e.target.value)} disabled={!canEdit} placeholder="https://…/{edition}" className="h-8 text-sm" />
        {issue && <span className="truncate text-[11px]">e.g. {example(issue)}</span>}
      </label>
      <div className="md:pt-5">
        {canEdit && dirty && (
          <Button size="sm" disabled={pending} onClick={() => start(async () => {
            try {
              await saveTitleLinks(title.id, { digital_page_url: page.trim() || null, digital_issue_url: issue.trim() || null });
              toast.success("Links saved");
              router.refresh();
            } catch (e) { toast.error(friendlyError(e, "Couldn't save the links")); }
          })}>Save</Button>
        )}
      </div>
    </li>
  );
}
