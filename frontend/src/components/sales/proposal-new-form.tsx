"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { SalesRate, SalesTitle } from "@/lib/sales-types";
import { TEMPLATE_OPTIONS, type ProposalKind, type ProposalLine } from "@/lib/proposals-types";
import { ProposalLines, type EditLine } from "@/components/sales/proposal-lines";
import { searchCompanies, searchContacts } from "@/lib/actions";
import { createProposal } from "@/lib/proposals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EntityPicker } from "@/components/entity-picker";
import { InfoHint } from "@/components/sales/info-hint";
import { ProposalIssuePicker } from "@/components/sales/proposal-issue-picker";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";

type Option = { id: string; label: string; sublabel?: string | null };

const templateFor = (slug: string) => (slug.startsWith("obh") ? "obh" : slug.startsWith("tbtm") ? "tbtm" : "stm");

export function ProposalNewForm({ titles, rates, year, company: initial, initialTitleId, initialEditionId }: {
  titles: SalesTitle[];
  rates: SalesRate[];
  year: number;
  company: Option | null;
  initialTitleId?: string | null;
  initialEditionId?: string | null;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [company, setCompany] = useState<Option | null>(initial);
  const [contact, setContact] = useState<Option | null>(null);
  const [titleId, setTitleId] = useState(initialTitleId && titles.some((t) => t.id === initialTitleId) ? initialTitleId : titles[0]?.id ?? "");
  const [editionId, setEditionId] = useState(initialEditionId ?? "");
  const title = titles.find((t) => t.id === titleId);
  const [template, setTemplate] = useState(title ? templateFor(title.slug) : "stm");
  const [campaign, setCampaign] = useState(initial ? `${initial.label} ${year}/${String(year + 1).slice(2)}` : "");
  const [rows, setRows] = useState<EditLine[]>([]);
  const [kind, setKind] = useState<ProposalKind>("issue");
  const [discount, setDiscount] = useState(0);

  function pickCompany(o: Option | null) {
    setCompany(o);
    if (o && !campaign.trim()) setCampaign(`${o.label} ${year}/${String(year + 1).slice(2)}`);
  }
  function pickTitle(id: string) {
    setTitleId(id);
    const t = titles.find((x) => x.id === id);
    if (t) setTemplate(templateFor(t.slug));
    setEditionId("");
  }

  function submit() {
    if (!company) return toast.error("Choose the client first");
    if (rows.some((r) => r.source === "manual" && (!r.product.trim() || r.unit_price == null))) return toast.error("Give every line a name and a price");
    start(async () => {
      try {
        const lines: ProposalLine[] = rows.map((r) => ({ ...r, product: r.product.trim(), unit_price: r.source === "manual" ? r.unit_price : null }));
        const p = await createProposal({ company_id: company.id, contact_id: contact?.id ?? null, title_id: titleId || null, edition_id: editionId || null, template,
          campaign_name: campaign.trim(), year, lines, kind, discount_pct: discount });
        router.push(`/sales/proposals/${p.id}`);
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't start the proposal"));
      }
    });
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="grid gap-4 rounded-xl border border-border/80 bg-card p-4 shadow-2xs sm:grid-cols-2">
        <div className="sm:col-span-2">
          <EntityPicker label="Client" placeholder="Search for a client…" search={async (q) => (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name, sublabel: c.industry }))} value={company} onChange={pickCompany} />
        </div>
        <div className="sm:col-span-2">
          <EntityPicker label="Who it's for (optional)" placeholder="Search for the contact…" search={async (q) => (await searchContacts(q)).map((c) => ({ id: c.id, label: c.full_name ?? "Unnamed", sublabel: c.company_name }))} value={contact} onChange={setContact} />
        </div>
        <label className={labelCls}>
          Title
          <select className={selectCls} value={titleId} onChange={(e) => pickTitle(e.target.value)}>
            {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </label>
        <label className={`${labelCls} sm:col-span-2`}>
          <span className="flex items-center gap-1">Which issue <InfoHint>From the editorial plan. Its date, advertising deadline and planned features go into the wording. Leave it on “next open issue” and we&apos;ll pick the next one that can still take adverts.</InfoHint></span>
          <ProposalIssuePicker titleId={titleId || null} value={editionId} onChange={(id) => setEditionId(id)} include={initialEditionId} emptyLabel="The next open issue (picked for you)" />
        </label>
        <label className={labelCls}>
          <span className="flex items-center gap-1">Word template <InfoHint>Follows the title you chose (Onboard Hospitality, Selling Travel, or The Business Travel Magazine). Change it if the proposal belongs in a different look.</InfoHint></span>
          <select className={selectCls} value={template} onChange={(e) => setTemplate(e.target.value)}>
            {TEMPLATE_OPTIONS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </label>
        <label className={`${labelCls} sm:col-span-2`}>
          <span className="flex items-center gap-1">Campaign name <InfoHint>Goes in the header of the Word document, e.g. “Delta Air Lines 2026/27”.</InfoHint></span>
          <Input value={campaign} onChange={(e) => setCampaign(e.target.value)} placeholder="Client 2026/27" className="h-8 text-sm" />
        </label>
      </section>

      <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold">What you&apos;re offering
          <InfoHint>Pick products from any title&apos;s rate card - their prices are filled in for you. For anything not on it, add your own line and type the price. Pick the issues each product runs in, take a % off a line or the whole proposal, and give lines an option name to offer choices (Option A: one issue, Option B: the year). Rate card offers are added for you. All prices are before VAT.</InfoHint>
        </h2>
        <ProposalLines lines={rows} onChange={setRows} titles={titles} rates={rates} defaultTitleId={titleId || null}
          discount={discount} onDiscount={setDiscount} kind={kind} onKind={setKind} stale />
      </section>

      <div className="flex items-center justify-end gap-3">
        <p className="text-xs text-muted-foreground">Nothing is sent. You&apos;ll review and edit everything first.</p>
        <Button onClick={submit} disabled={pending || !company} className="gap-1.5">
          {pending && <Loader2 className="size-4 animate-spin" />} Draft the proposal
        </Button>
      </div>
    </div>
  );
}
