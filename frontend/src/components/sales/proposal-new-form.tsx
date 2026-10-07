"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { SalesRate, SalesTitle } from "@/lib/sales-types";
import { TEMPLATE_OPTIONS, type ProposalLine } from "@/lib/proposals-types";
import { searchCompanies, searchContacts } from "@/lib/actions";
import { createProposal } from "@/lib/proposals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EntityPicker } from "@/components/entity-picker";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtGBP } from "@/components/sales/sales-ui";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";

type Option = { id: string; label: string; sublabel?: string | null };
type Row = { key: string; product: string; qty: number; price: string; source: "rate_card" | "manual"; rateId?: string };

const templateFor = (slug: string) => (slug.startsWith("obh") ? "obh" : slug.startsWith("tbtm") ? "tbtm" : "stm");

export function ProposalNewForm({ titles, rates, year, company: initial }: { titles: SalesTitle[]; rates: SalesRate[]; year: number; company: Option | null }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [company, setCompany] = useState<Option | null>(initial);
  const [contact, setContact] = useState<Option | null>(null);
  const [titleId, setTitleId] = useState(titles[0]?.id ?? "");
  const title = titles.find((t) => t.id === titleId);
  const [template, setTemplate] = useState(title ? templateFor(title.slug) : "stm");
  const [campaign, setCampaign] = useState(initial ? `${initial.label} ${year}/${String(year + 1).slice(2)}` : "");
  const [rows, setRows] = useState<Row[]>([]);
  const titleRates = rates.filter((r) => r.title_id === titleId && r.price_gbp != null);

  const total = rows.reduce((s, r) => s + r.qty * (Number(r.price) || 0), 0);

  function pickCompany(o: Option | null) {
    setCompany(o);
    if (o && !campaign.trim()) setCampaign(`${o.label} ${year}/${String(year + 1).slice(2)}`);
  }
  function pickTitle(id: string) {
    setTitleId(id);
    const t = titles.find((x) => x.id === id);
    if (t) setTemplate(templateFor(t.slug));
    setRows((rs) => rs.filter((r) => r.source === "manual"));
  }
  function addRate(rateId: string) {
    const r = titleRates.find((x) => x.id === rateId);
    if (!r) return;
    setRows((rs) => [...rs, { key: crypto.randomUUID(), product: r.product, qty: 1, price: String(r.price_gbp), source: "rate_card", rateId: r.id }]);
  }

  function submit() {
    if (!company) return toast.error("Choose the client first");
    if (rows.some((r) => r.source === "manual" && (!r.product.trim() || r.price === ""))) return toast.error("Give every line a name and a price");
    start(async () => {
      try {
        const lines: ProposalLine[] = rows.map((r) => ({
          product: r.product.trim(),
          qty: r.qty,
          unit_price: r.source === "manual" ? Number(r.price) : null,
          source: r.source,
          rate_id: r.rateId ?? null,
        }));
        const p = await createProposal({ company_id: company.id, contact_id: contact?.id ?? null, title_id: titleId || null, template, campaign_name: campaign.trim(), year, lines });
        router.push(`/sales/proposals/${p.id}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't start the proposal");
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

      <section className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
        <header className="flex items-center gap-2 border-b border-border/70 px-4 py-3">
          <h2 className="text-sm font-bold">What you&apos;re offering</h2>
          <InfoHint>Pick products from the {year} rate card - their prices are filled in for you and can&apos;t be changed here. For anything not on the rate card, add your own line and type the price. All prices are before VAT.</InfoHint>
        </header>
        <div className="flex flex-col gap-2 p-4">
          {titleRates.length === 0 && <p className="text-xs text-muted-foreground">There&apos;s no {year} rate card for {title?.name ?? "this title"} yet, so add your own lines with prices below.</p>}
          {rows.map((r) => (
            <div key={r.key} className="grid grid-cols-[minmax(0,1fr)_4.5rem_7rem_auto] items-center gap-2">
              <Input aria-label="Product" value={r.product} disabled={r.source === "rate_card"} onChange={(e) => setRows(rows.map((x) => (x.key === r.key ? { ...x, product: e.target.value } : x)))} className="h-8 text-sm" placeholder="What are you offering?" />
              <Input aria-label="Quantity" type="number" min={1} value={r.qty} onChange={(e) => setRows(rows.map((x) => (x.key === r.key ? { ...x, qty: Math.max(1, Number(e.target.value) || 1) } : x)))} className="h-8 text-right text-sm tabular-nums" />
              <Input aria-label="Price each in £" type="number" min={0} value={r.price} disabled={r.source === "rate_card"} onChange={(e) => setRows(rows.map((x) => (x.key === r.key ? { ...x, price: e.target.value } : x)))} className="h-8 text-right text-sm tabular-nums" placeholder="£" />
              <Button size="icon-sm" variant="ghost" aria-label={`Remove ${r.product || "line"}`} onClick={() => setRows(rows.filter((x) => x.key !== r.key))}><Trash2 className="size-3.5" /></Button>
            </div>
          ))}
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {titleRates.length > 0 && (
              <select aria-label="Add from the rate card" className={`${selectCls} !w-auto min-w-48`} value="" onChange={(e) => addRate(e.target.value)}>
                <option value="">Add from the rate card…</option>
                {titleRates.map((r) => <option key={r.id} value={r.id}>{r.product} · {fmtGBP(r.price_gbp)}</option>)}
              </select>
            )}
            <Button size="sm" variant="ghost" className="gap-1.5" onClick={() => setRows([...rows, { key: crypto.randomUUID(), product: "", qty: 1, price: "", source: "manual" }])}>
              <Plus className="size-3.5" /> Add my own line
            </Button>
            <span className="ml-auto text-sm font-semibold tabular-nums">Total {fmtGBP(total)} <span className="text-xs font-normal text-muted-foreground">before VAT</span></span>
          </div>
        </div>
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
