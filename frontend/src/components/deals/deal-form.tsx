"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, CalendarPlus, Copy, Gift, Loader2, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { SalesRate, SalesRep, SalesTitle } from "@/lib/sales-types";
import type { DealInput, DealIssue, DealLine, DealPlacement, DealPreview } from "@/lib/deals-types";
import { createDeal, getDealIssues, getDealPrefill, previewDeal, updateDeal } from "@/lib/deals-actions";
import { searchCompanies, searchContacts } from "@/lib/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EntityPicker } from "@/components/entity-picker";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-8 w-full min-w-0 truncate rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60 dark:bg-input/30";
const labelCls = "flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted-foreground";
const cardCls = "rounded-xl border border-border/80 bg-card p-4 shadow-2xs";

type Option = { id: string; label: string; sublabel?: string | null };
type Line = DealLine & { key: string };

const pct = (v: number) => (v ? String(Math.round(v * 10000) / 100) : "");
const fromPct = (s: string) => Math.min(Math.max((Number(s) || 0) / 100, 0), 1);
const num = (s: string) => (s.trim() === "" ? null : Number(s));
const newKey = () => crypto.randomUUID().replace(/-/g, "").slice(0, 12);

function blankLine(titleId: string | null): Line {
  return { key: newKey(), title_id: titleId, rate_id: null, description: "", detail: null, size: null, qty: 1, unit_price: null, list_price: null,
    discount_pct: 0, added_value: false, share_gbp: null, placements: [{}] };
}

export function DealForm({ dealId, initial, titles, reps, rates, company: initialCompany, contact: initialContact, myRepId }: {
  dealId?: string;
  initial: DealInput;
  titles: SalesTitle[];
  reps: SalesRep[];
  rates: SalesRate[];
  company: Option | null;
  contact: Option | null;
  myRepId: string | null;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [f, setF] = useState<DealInput>(() => ({ ...initial, rep_id: initial.rep_id ?? myRepId }));
  const [lines, setLines] = useState<Line[]>(() => (initial.lines.length ? initial.lines : [blankLine(initial.title_id)]).map((l) => ({ ...l, key: l.key ?? newKey() })));
  const [company, setCompany] = useState<Option | null>(initialCompany);
  const [contact, setContact] = useState<Option | null>(initialContact);
  const [issues, setIssues] = useState<Record<string, DealIssue[]>>({});
  const [preview, setPreview] = useState<DealPreview | null>(null);
  const [shareOpen, setShareOpen] = useState(f.split.length > 0);
  const [lastOrder, setLastOrder] = useState<{ id: string; number: number } | null>(null);
  // "" = not chosen yet; "house" = deliberately nobody (no commission)
  const [repPick, setRepPick] = useState<string>(() => initial.rep_id ?? myRepId ?? (dealId ? "house" : ""));
  const set = <K extends keyof DealInput>(k: K, v: DealInput[K]) => setF((x) => ({ ...x, [k]: v }));

  // Each title's issues, months and events (with deadlines), loaded once per title.
  const wanted = useMemo(() => [...new Set(lines.map((l) => l.title_id).filter(Boolean) as string[])], [lines]);
  const includeRef = useRef([...new Set(lines.flatMap((l) => l.placements.map((p) => p.edition_id).filter(Boolean) as string[]))]);
  useEffect(() => {
    let live = true;
    wanted.filter((t) => !issues[t]).forEach((t) => {
      getDealIssues(t, includeRef.current).then((r) => live && setIssues((m) => ({ ...m, [t]: r }))).catch(() => live && setIssues((m) => ({ ...m, [t]: [] })));
    });
    return () => { live = false; };
  }, [wanted, issues]);

  // Live totals: the same sums the order is saved with, worked out on the server.
  const priceKey = JSON.stringify([f.pricing, f.package_price_gbp, f.package_split, f.discount_pct, f.agency_pct, lines.map((l) => [l.qty, l.unit_price, l.list_price, l.discount_pct, l.added_value, l.share_gbp, l.placements.length])]);
  useEffect(() => {
    let live = true;
    const t = setTimeout(() => {
      previewDeal({ pricing: f.pricing, package_price_gbp: f.package_price_gbp, package_split: f.package_split, discount_pct: f.discount_pct, agency_pct: f.agency_pct,
        lines: lines.map((l) => ({ ...l, placements: l.placements.map(() => ({})) })) })
        .then((r) => live && setPreview(r)).catch(() => undefined);
    }, 350);
    return () => { live = false; clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [priceKey]);

  const ratesFor = (titleId: string | null | undefined) => rates.filter((r) => r.title_id === titleId);
  const updLine = (key: string, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  const updPlace = (key: string, i: number, patch: Partial<DealPlacement>) =>
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, placements: l.placements.map((p, j) => (j === i ? { ...p, ...patch } : p)) } : l)));

  function pickCompany(o: Option | null) {
    setCompany(o);
    if (!o) return;
    setF((x) => ({ ...x, company_id: o.id, client_name: o.label }));
    getDealPrefill({ company_id: o.id }).then((p) => {
      setF((x) => ({
        ...x,
        confirmation_address: x.confirmation_address || p.confirmation_address || x.confirmation_address,
        invoice_to: x.invoice_to || p.invoice_to || null,
        invoice_email: x.invoice_email || p.invoice_email || null,
        agency_name: x.agency_name || p.agency_name || null,
        agency_pct: x.agency_pct || p.agency_pct || 0,
      }));
      setLastOrder(p.last_order ?? null);
    }).catch(() => undefined);
  }
  function pickContact(o: Option | null) {
    setContact(o);
    if (!o) return setF((x) => ({ ...x, contact_id: null }));
    setF((x) => ({ ...x, contact_id: o.id, contact_name: o.label }));
    getDealPrefill({ contact_id: o.id }).then((p) => setF((x) => ({ ...x, contact_email: p.contact_email ?? x.contact_email }))).catch(() => undefined);
  }
  function pickRate(l: Line, rateId: string) {
    const r = rates.find((x) => x.id === rateId);
    if (!r) return updLine(l.key, { rate_id: null });
    updLine(l.key, { rate_id: r.id, description: l.description && l.rate_id === null ? l.description : r.product, list_price: r.price_gbp,
      unit_price: l.unit_price == null || l.unit_price === l.list_price ? r.price_gbp : l.unit_price });
  }
  function addEveryIssue(l: Line) {
    const list = (issues[l.title_id ?? ""] ?? []).filter((i) => i.open && i.kind !== "month");
    const have = new Set(l.placements.map((p) => p.edition_id));
    const add = list.filter((i) => !have.has(i.id)).map((i) => ({ edition_id: i.id }));
    if (!add.length) return toast.info("Every open issue is already on this line");
    updLine(l.key, { placements: [...l.placements.filter((p) => p.edition_id), ...add] });
  }
  function move(key: string, d: -1 | 1) {
    setLines((ls) => {
      const i = ls.findIndex((l) => l.key === key);
      const j = i + d;
      if (j < 0 || j >= ls.length) return ls;
      const out = [...ls];
      [out[i], out[j]] = [out[j], out[i]];
      return out;
    });
  }

  function submit(status?: "pencilled" | "confirmed") {
    if (!f.client_name.trim() && !company) return toast.error("Choose the client first");
    if (!repPick && !f.split.length) return toast.error("Choose the salesperson, so the right person earns the commission");
    if (lines.some((l) => !l.description.trim() && !l.size)) return toast.error("Say what each item is");
    if (lines.some((l) => l.placements.some((p) => !p.edition_id))) return toast.error("Choose the issue, month or event for every item");
    if (f.pricing === "items" && lines.some((l) => !l.added_value && (l.unit_price == null || Number.isNaN(l.unit_price)))) return toast.error("Give every item a price, or tick it as free");
    if (f.pricing === "package" && !f.package_price_gbp) return toast.error("Enter the package price");
    if (f.split.length && Math.abs(f.split.reduce((s, x) => s + x.pct, 0) - 1) > 0.001) return toast.error("The split between salespeople needs to add up to 100%");
    const input: DealInput = { ...f, client_name: f.client_name.trim(), lines: lines.map((l) => ({ ...l, placements: l.placements.map((p) => ({ ...p })) })), status: status ?? f.status };
    start(async () => {
      try {
        const d = dealId ? await updateDeal(dealId, input) : await createDeal(input);
        d.notes?.forEach((n) => toast.info(n));
        toast.success(dealId ? "Order saved" : `Order ${d.number} created`);
        router.push(`/sales/deals/${d.id}`);
      } catch (e) { toast.error(friendlyError(e, "Couldn't save the order")); }
    });
  }

  const totals = preview && !preview.error ? preview : null;
  const showShares = f.pricing === "package" && f.package_split === "manual";

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="flex min-w-0 flex-col gap-5">
        {/* ---- client ---- */}
        <section className={cardCls} aria-labelledby="df-client">
          <h2 id="df-client" className="mb-3 text-sm font-bold">Client</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <EntityPicker label="Client company" placeholder="Search the CRM…" search={async (q) => (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name, sublabel: c.industry }))}
              value={company} onChange={pickCompany} viewHref={(id) => `/companies/${id}`} />
            <EntityPicker label="Their contact" placeholder="Search for the contact…" search={async (q) => (await searchContacts(q)).map((c) => ({ id: c.id, label: c.full_name ?? "Unnamed", sublabel: c.company_name }))}
              value={contact} onChange={pickContact} viewHref={(id) => `/contacts/${id}`} />
            <label className={labelCls}><span className="flex items-center gap-1">Client name as booked <InfoHint>How it appears on the bookings and the confirmation. Usually the company name, but can differ (&quot;Brunswick - Delice de France&quot;).</InfoHint></span>
              <Input value={f.client_name} onChange={(e) => set("client_name", e.target.value)} className="h-8 text-sm" /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className={labelCls}>Contact name<Input value={f.contact_name ?? ""} onChange={(e) => set("contact_name", e.target.value)} className="h-8 text-sm" /></label>
              <label className={labelCls}>Contact email<Input type="email" value={f.contact_email ?? ""} onChange={(e) => set("contact_email", e.target.value)} className="h-8 text-sm" /></label>
            </div>
            <label className={labelCls}>Salesperson
              <select className={selectCls} value={repPick} onChange={(e) => { setRepPick(e.target.value); set("rep_id", e.target.value && e.target.value !== "house" ? e.target.value : null); }}>
                <option value="">Choose…</option>
                {reps.filter((r) => r.active || r.id === f.rep_id).map((r) => <option key={r.id} value={r.id}>{r.name} ({r.code})</option>)}
                <option value="house">House account (no commission)</option>
              </select>
            </label>
            <label className={labelCls}><span className="flex items-center gap-1">Order date <InfoHint>The day the client agreed. Items added to the order later are dated the day they&apos;re added, so only what was on the first deal counts as new business.</InfoHint></span>
              <Input type="date" value={f.booked_on ?? ""} onChange={(e) => set("booked_on", e.target.value || null)} className="h-8 text-sm" /></label>
          </div>
          {lastOrder && <p className="mt-2 text-xs text-muted-foreground">Invoice details filled in from their last order, <a href={`/sales/deals/${lastOrder.id}`} target="_blank" rel="noreferrer" className="font-semibold text-primary hover:underline">order {lastOrder.number}</a>. Check they still apply.</p>}
          <div className="mt-3">
            {!shareOpen ? (
              <button type="button" className="text-xs font-semibold text-primary hover:underline" onClick={() => { setShareOpen(true); if (f.rep_id) set("split", [{ rep_id: f.rep_id, pct: 0.5 }]); }}>Shared with another salesperson?</button>
            ) : (
              <fieldset className="rounded-lg border border-border/70 p-3">
                <legend className="px-1 text-xs font-semibold text-muted-foreground">Split of the credit (for commission)</legend>
                {f.split.map((s, i) => (
                  <div key={i} className="mb-2 flex items-center gap-2">
                    <select className={selectCls} value={s.rep_id} onChange={(e) => set("split", f.split.map((x, j) => (j === i ? { ...x, rep_id: e.target.value } : x)))} aria-label="Salesperson">
                      {reps.filter((r) => r.active || r.id === s.rep_id).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                    <Input inputMode="decimal" value={pct(s.pct)} onChange={(e) => set("split", f.split.map((x, j) => (j === i ? { ...x, pct: fromPct(e.target.value) } : x)))} className="h-8 w-20 text-sm" aria-label="Share %" />
                    <span className="text-xs text-muted-foreground">%</span>
                    <Button type="button" size="icon-sm" variant="ghost" aria-label="Remove" onClick={() => set("split", f.split.filter((_, j) => j !== i))}><X className="size-3.5" /></Button>
                  </div>
                ))}
                <div className="flex items-center gap-3 text-xs">
                  <button type="button" className="font-semibold text-primary hover:underline" onClick={() => set("split", [...f.split, { rep_id: reps.find((r) => r.active && !f.split.some((x) => x.rep_id === r.id))?.id ?? reps[0].id, pct: 0 }])}>Add a salesperson</button>
                  <span className={Math.abs(f.split.reduce((s, x) => s + x.pct, 0) - 1) > 0.001 ? "font-semibold text-destructive" : "text-muted-foreground"}>Adds up to {Math.round(f.split.reduce((s, x) => s + x.pct, 0) * 1000) / 10}%</span>
                  <button type="button" className="ml-auto text-muted-foreground hover:underline" onClick={() => { setShareOpen(false); set("split", []); }}>Not shared</button>
                </div>
              </fieldset>
            )}
          </div>
        </section>

        {/* ---- items ---- */}
        <section className="flex flex-col gap-3" aria-labelledby="df-items">
          <div className="flex items-center justify-between">
            <h2 id="df-items" className="flex items-center gap-1 text-sm font-bold">What they&apos;ve booked <InfoHint>One line per product. Put a line in every issue, month or event it runs in: each one becomes its own booking, counts in that issue&apos;s figures and earns commission when it runs.</InfoHint></h2>
            <Button type="button" size="sm" variant="outline" className="gap-1" onClick={() => setLines((ls) => [...ls, blankLine(ls[ls.length - 1]?.title_id ?? f.title_id)])}><Plus className="size-3.5" /> Add an item</Button>
          </div>
          {lines.map((l, li) => {
            const opts = issues[l.title_id ?? ""] ?? [];
            const titleRates = ratesFor(l.title_id);
            const pl = totals?.lines?.[li];
            const each = (l.unit_price ?? 0) * l.qty * (1 - l.discount_pct);
            const off = l.list_price && !l.added_value && f.pricing === "items" && l.unit_price != null ? 1 - each / (l.list_price * l.qty) : 0;
            return (
              <article key={l.key} className={`${cardCls} ${l.added_value ? "border-dashed" : ""}`} aria-label={`Item ${li + 1}`}>
                <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
                  <label className={labelCls}>Title
                    <select className={selectCls} value={l.title_id ?? ""} onChange={(e) => updLine(l.key, { title_id: e.target.value || null, rate_id: null, placements: [{}] })}>
                      <option value="">Choose…</option>
                      {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </label>
                  <label className={labelCls}>From the rate card
                    <select className={selectCls} value={l.rate_id ?? ""} disabled={!l.title_id} onChange={(e) => pickRate(l, e.target.value)}>
                      <option value="">{titleRates.length ? "Choose a product, or type your own below" : "Nothing on the rate card - type it below"}</option>
                      {[...new Set(titleRates.map((r) => r.year))].sort().map((y) => (
                        <optgroup key={y} label={String(y)}>
                          {titleRates.filter((r) => r.year === y).map((r) => <option key={r.id} value={r.id}>{r.product}{r.price_gbp != null ? ` - ${fmtGBP(r.price_gbp)}` : ""}</option>)}
                        </optgroup>
                      ))}
                    </select>
                  </label>
                  <label className={`${labelCls} sm:col-span-2`}>What it is, as it should read on the confirmation
                    <Input value={l.description} onChange={(e) => updLine(l.key, { description: e.target.value })} placeholder="e.g. Full page advert, Solus html email, Sponsored Q&A" className="h-8 text-sm" />
                  </label>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5">
                  <label className={labelCls}><span className="flex items-center gap-1">Size code <InfoHint>The order register&apos;s shorthand (FP, DPS, 1/2) - counts the pages in the issue.</InfoHint></span>
                    <Input value={l.size ?? ""} onChange={(e) => updLine(l.key, { size: e.target.value || null })} placeholder="e.g. FP" className="h-8 text-sm" /></label>
                  <label className={labelCls}><span className="flex items-center gap-1">Each time <InfoHint>How many of it in each issue or month, e.g. 4 weekly banners in a month.</InfoHint></span>
                    <Input type="number" min={1} value={l.qty} onChange={(e) => updLine(l.key, { qty: Math.max(1, Number(e.target.value) || 1) })} className="h-8 text-sm" /></label>
                  {f.pricing === "items" && !l.added_value ? <>
                    <label className={labelCls}>Price each (£)
                      <Input inputMode="decimal" value={l.unit_price ?? ""} onChange={(e) => updLine(l.key, { unit_price: num(e.target.value) })} className="h-8 text-sm" /></label>
                    <label className={labelCls}>% off this item
                      <Input inputMode="decimal" value={pct(l.discount_pct)} onChange={(e) => updLine(l.key, { discount_pct: fromPct(e.target.value) })} placeholder="0" className="h-8 text-sm" /></label>
                  </> : showShares && !l.added_value ? (
                    <label className={`${labelCls} col-span-2`}>This line&apos;s share of the package (£)
                      <Input inputMode="decimal" value={l.share_gbp ?? ""} onChange={(e) => updLine(l.key, { share_gbp: num(e.target.value) })} className="h-8 text-sm" /></label>
                  ) : <div className="col-span-2" />}
                  <label className={labelCls}>Rate card price (£)
                    <Input inputMode="decimal" value={l.list_price ?? ""} onChange={(e) => updLine(l.key, { list_price: num(e.target.value) })} placeholder="optional" className="h-8 text-sm" /></label>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                  <label className="flex items-center gap-1.5 font-semibold">
                    <input type="checkbox" checked={l.added_value} onChange={(e) => updLine(l.key, { added_value: e.target.checked })} />
                    <Gift className="size-3.5" aria-hidden="true" /> Free - added value
                  </label>
                  {off > 0.0005 && <span style={{ color: "var(--warn)" }}>{Math.round(off * 1000) / 10}% below rate card</span>}
                  {l.added_value && l.list_price ? <span className="text-muted-foreground">Shows as &quot;normally {fmtGBP(l.list_price * l.qty)} each&quot;</span> : null}
                  <label className="flex min-w-48 flex-1 items-center gap-1.5 text-muted-foreground">Extra wording
                    <Input value={l.detail ?? ""} onChange={(e) => updLine(l.key, { detail: e.target.value || null })} placeholder="optional, printed under the line" className="h-7 text-xs" />
                  </label>
                </div>

                <div className="mt-3 rounded-lg border border-border/70">
                  <div className="flex items-center justify-between border-b border-border/70 px-3 py-1.5 text-xs font-semibold text-muted-foreground">
                    <span>Runs in ({l.placements.length})</span>
                    <span className="flex gap-3">
                      <button type="button" className="text-primary hover:underline disabled:opacity-50" disabled={!l.title_id} onClick={() => addEveryIssue(l)}><CalendarPlus className="mr-1 inline size-3" />Every open issue</button>
                      <button type="button" className="text-primary hover:underline disabled:opacity-50" disabled={!l.title_id} onClick={() => updLine(l.key, { placements: [...l.placements, {}] })}><Plus className="mr-0.5 inline size-3" />Another</button>
                    </span>
                  </div>
                  <ul className="divide-y divide-border/60">
                    {l.placements.map((p, pi) => {
                      const iss = opts.find((x) => x.id === p.edition_id);
                      return (
                        <li key={pi} className="grid items-center gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1.6fr)_8.5rem_8.5rem_minmax(0,1fr)_auto]">
                          <select className={selectCls} value={p.edition_id ?? ""} disabled={!l.title_id} aria-label="Issue, month or event"
                            onChange={(e) => updPlace(l.key, pi, { edition_id: e.target.value || null })}>
                            <option value="">{l.title_id ? (opts.length ? "Choose the issue, month or event…" : "Loading…") : "Choose the title first"}</option>
                            {opts.map((o) => <option key={o.id} value={o.id}>{o.label}{o.edition_date ? ` · ${fmtDate(o.edition_date)}` : ""}{!o.open ? " · deadline passed" : o.ad_deadline ? ` · book by ${fmtDate(o.ad_deadline)}` : ""}</option>)}
                          </select>
                          <Input type="date" value={p.item_date ?? ""} onChange={(e) => updPlace(l.key, pi, { item_date: e.target.value || null })} className="h-8 text-xs" aria-label="Exact date it runs (optional)" title="Exact date it runs, if not the issue's date (an email on 13 May)" />
                          <Input type="date" value={p.copy_due ?? ""} onChange={(e) => updPlace(l.key, pi, { copy_due: e.target.value || null })} className="h-8 text-xs" aria-label="Copy due (optional)"
                            title={iss?.copy_deadline ? `Copy due - the issue's copy deadline is ${fmtDate(iss.copy_deadline)}` : "Copy or artwork due (optional)"} />
                          <span className="text-right text-xs tabular-nums text-muted-foreground">
                            {l.added_value ? "Free" : pl ? fmtGBP(pl.placements[pi] ?? 0) : ""}
                            {iss && !iss.open && <span className="block" style={{ color: "var(--warn)" }}>deadline passed</span>}
                          </span>
                          <Button type="button" size="icon-sm" variant="ghost" aria-label="Remove this one" disabled={l.placements.length === 1}
                            onClick={() => updLine(l.key, { placements: l.placements.filter((_, j) => j !== pi) })}><X className="size-3.5" /></Button>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="px-3 pb-2 text-[11px] text-muted-foreground">Dates are optional: the exact day it runs (if not the issue&apos;s date) and when copy is due.</p>
                </div>

                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold tabular-nums">{l.added_value ? "Free" : pl ? `${fmtGBP(pl.total_gbp)}${l.placements.length > 1 ? ` for ${l.placements.length}` : ""}` : ""}</span>
                  <span className="flex gap-1">
                    <Button type="button" size="icon-sm" variant="ghost" aria-label="Move up" disabled={li === 0} onClick={() => move(l.key, -1)}><ArrowUp className="size-3.5" /></Button>
                    <Button type="button" size="icon-sm" variant="ghost" aria-label="Move down" disabled={li === lines.length - 1} onClick={() => move(l.key, 1)}><ArrowDown className="size-3.5" /></Button>
                    <Button type="button" size="icon-sm" variant="ghost" aria-label="Copy this item" onClick={() => setLines((ls) => [...ls.slice(0, li + 1), { ...l, key: newKey(), placements: l.placements.map((p) => ({ ...p, order_id: null, booked_on: null })) }, ...ls.slice(li + 1)])}><Copy className="size-3.5" /></Button>
                    <Button type="button" size="icon-sm" variant="ghost" aria-label="Remove this item" disabled={lines.length === 1} onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))}><Trash2 className="size-3.5 text-destructive" /></Button>
                  </span>
                </div>
              </article>
            );
          })}
        </section>

        {/* ---- price ---- */}
        <section className={cardCls} aria-labelledby="df-price">
          <h2 id="df-price" className="mb-3 text-sm font-bold">Price</h2>
          <div role="radiogroup" aria-label="How it's priced" className="mb-3 flex flex-wrap gap-2">
            {([["items", "Each item has its price"], ["package", "One package price"]] as const).map(([v, label]) => (
              <button key={v} type="button" role="radio" aria-checked={f.pricing === v} onClick={() => set("pricing", v)}
                className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${f.pricing === v ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:bg-muted"}`}>{label}</button>
            ))}
          </div>
          {f.pricing === "package" && (
            <div className="mb-3 grid gap-3 sm:grid-cols-3">
              <label className={labelCls}>Package price (£)<Input inputMode="decimal" value={f.package_price_gbp ?? ""} onChange={(e) => set("package_price_gbp", num(e.target.value))} className="h-8 text-sm" /></label>
              <label className={`${labelCls} sm:col-span-2`}>Name on the confirmation<Input value={f.package_label ?? ""} onChange={(e) => set("package_label", e.target.value || null)} placeholder={`Marketing package for ${f.client_name || "the client"}`} className="h-8 text-sm" /></label>
              <label className={`${labelCls} sm:col-span-3`}><span className="flex items-center gap-1">Share it across the items <InfoHint>Each item still needs its own value, so the issue it runs in gets its revenue and commission is earned as it runs. By rate card value gives dearer items a bigger share.</InfoHint></span>
                <select className={selectCls} value={f.package_split} onChange={(e) => set("package_split", e.target.value as DealInput["package_split"])}>
                  <option value="rate_card">In proportion to their rate card value</option>
                  <option value="even">Evenly</option>
                  <option value="manual">I&apos;ll type each line&apos;s share</option>
                </select>
              </label>
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-3">
            <label className={labelCls}>% off the whole order<Input inputMode="decimal" value={pct(f.discount_pct)} onChange={(e) => set("discount_pct", fromPct(e.target.value))} placeholder="0" className="h-8 text-sm" /></label>
            <label className={labelCls}><span className="flex items-center gap-1">Booked through an agency <InfoHint>The agency is invoiced and keeps its commission. It comes off what&apos;s invoiced and off the salesperson&apos;s commissionable revenue.</InfoHint></span>
              <Input value={f.agency_name ?? ""} onChange={(e) => set("agency_name", e.target.value || null)} placeholder="Agency name (optional)" className="h-8 text-sm" /></label>
            <label className={labelCls}>Agency commission (%)<Input inputMode="decimal" value={pct(f.agency_pct)} onChange={(e) => set("agency_pct", fromPct(e.target.value))} placeholder="e.g. 10" className="h-8 text-sm" /></label>
          </div>
          {(preview?.warnings ?? []).map((w) => <p key={w} className="mt-2 text-xs" style={{ color: "var(--warn)" }}>{w}</p>)}
          {preview?.error && <p className="mt-2 text-xs" style={{ color: "var(--warn)" }}>{preview.error}</p>}
        </section>

        {/* ---- confirmation ---- */}
        <section className={cardCls} aria-labelledby="df-doc">
          <h2 id="df-doc" className="mb-3 text-sm font-bold">Confirmation</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className={labelCls}>Document
              <select className={selectCls} value={f.document} onChange={(e) => set("document", e.target.value as DealInput["document"])}>
                <option value="confirmation">Order confirmation (invoice to follow)</option>
                <option value="schedule">Schedule of works (a campaign over several months)</option>
              </select>
            </label>
            <label className={labelCls}>Publication heading<Input value={f.publication_label ?? ""} onChange={(e) => set("publication_label", e.target.value || null)} placeholder="e.g. The Business Travel Magazine plus digital activity" className="h-8 text-sm" /></label>
            <label className={labelCls}>Confirmation address<Textarea rows={4} value={f.confirmation_address ?? ""} onChange={(e) => set("confirmation_address", e.target.value || null)} className="text-sm" /></label>
            <label className={labelCls}>
              <span className="flex items-center justify-between">Invoice to
                <button type="button" className="font-semibold text-primary hover:underline" onClick={() => set("invoice_to", f.confirmation_address)}>Same as confirmation</button>
              </span>
              <Textarea rows={4} value={f.invoice_to ?? ""} onChange={(e) => set("invoice_to", e.target.value || null)} placeholder={"e.g. Accounts Payable\n…"} className="text-sm" />
            </label>
            <label className={labelCls}>Client&apos;s order or PO number<Input value={f.po_number ?? ""} onChange={(e) => set("po_number", e.target.value || null)} className="h-8 text-sm" /></label>
            <label className={labelCls}>Email the invoice to<Input type="email" value={f.invoice_email ?? ""} onChange={(e) => set("invoice_email", e.target.value || null)} placeholder="if not the contact" className="h-8 text-sm" /></label>
            <label className={labelCls}><span className="flex items-center gap-1">When to invoice <InfoHint>Shown on the order page as &quot;ready to invoice&quot;, so accounts know what to raise.</InfoHint></span>
              <select className={selectCls} value={f.invoice_plan} onChange={(e) => set("invoice_plan", e.target.value as DealInput["invoice_plan"])}>
                <option value="on_publication">Each item as it runs</option>
                <option value="upfront">All of it now</option>
                <option value="custom">As agreed (see instructions)</option>
              </select>
            </label>
            <label className={labelCls}>Insertions booked<Input value={f.insertions_label ?? ""} onChange={(e) => set("insertions_label", e.target.value || null)} placeholder="Filled in from the items (e.g. April, June, September)" className="h-8 text-sm" /></label>
            <label className={`${labelCls} sm:col-span-2`}>Special instructions<Textarea rows={2} value={f.special_instructions ?? ""} onChange={(e) => set("special_instructions", e.target.value || null)} className="text-sm" /></label>
            <label className={`${labelCls} sm:col-span-2`}>Copy and artwork<Textarea rows={2} value={f.copy_instructions ?? ""} onChange={(e) => set("copy_instructions", e.target.value || null)} placeholder="e.g. 500 words copy for the 3/4 column; all insertions proofed and signed off before publication" className="text-sm" /></label>
            <label className={labelCls}>Production contact<Input value={f.production_contact ?? ""} onChange={(e) => set("production_contact", e.target.value || null)} placeholder="e.g. Steve Hunter - production@bmipublishing.co.uk" className="h-8 text-sm" /></label>
            <label className="flex items-center gap-2 self-end pb-1.5 text-sm"><input type="checkbox" checked={f.show_artwork_specs} onChange={(e) => set("show_artwork_specs", e.target.checked)} /> Print the artwork specification</label>
          </div>
          <label className={`${labelCls} mt-3`}>Notes for the team (never printed)<Textarea rows={2} value={f.notes ?? ""} onChange={(e) => set("notes", e.target.value || null)} className="text-sm" /></label>
        </section>
      </div>

      {/* ---- totals ---- */}
      <aside className="lg:sticky lg:top-4 lg:self-start">
        <div className={cardCls}>
          <h2 className="mb-2 text-sm font-bold">Order total</h2>
          {!totals ? <p className="text-xs text-muted-foreground">Add an item to see the total.</p> : (
            <dl className="flex flex-col gap-1.5 text-sm">
              {totals.rate_card_gbp ? <Row label="At rate card" value={fmtGBP(totals.rate_card_gbp)} muted /> : null}
              {totals.added_value_gbp ? <Row label="Given free" value={fmtGBP(totals.added_value_gbp)} muted /> : null}
              {totals.discount_gbp ? <><Row label="Before discount" value={fmtGBP(totals.gross_gbp ?? 0)} /><Row label={`Discount ${pct(f.discount_pct)}%`} value={`- ${fmtGBP(totals.discount_gbp)}`} /></> : null}
              <Row label="Total" value={fmtGBP(totals.total_gbp ?? 0)} strong />
              {totals.agency_gbp ? <><Row label={`Agency ${pct(f.agency_pct)}%`} value={`- ${fmtGBP(totals.agency_gbp)}`} /><Row label="To invoice" value={fmtGBP(totals.payable_gbp ?? 0)} strong /></> : null}
              <p className="text-[11px] text-muted-foreground">Before VAT.</p>
              {totals.off_rate_card_pct != null && totals.off_rate_card_pct > 0.05 && (
                <p className="rounded-md px-2 py-1 text-xs" style={{ background: "color-mix(in oklab, var(--warn) 10%, transparent)" }}>
                  {totals.off_rate_card_pct}% below rate card, including anything given free.
                </p>
              )}
            </dl>
          )}
          <div className="mt-4 flex flex-col gap-2">
            {dealId ? (
              <Button disabled={pending} onClick={() => submit()}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save changes</Button>
            ) : <>
              <Button disabled={pending} onClick={() => submit("confirmed")}>{pending && <Loader2 className="size-3.5 animate-spin" />} Confirm the order</Button>
              <Button variant="outline" disabled={pending} onClick={() => submit("pencilled")}>Pencil it in</Button>
              <p className="text-[11px] text-muted-foreground">Pencilled orders hold the space but don&apos;t count in sales figures or commission until they&apos;re confirmed.</p>
            </>}
            <Button variant="ghost" disabled={pending} onClick={() => router.back()}>Cancel</Button>
          </div>
        </div>
      </aside>
    </div>
  );
}

function Row({ label, value, strong, muted }: { label: string; value: string; strong?: boolean; muted?: boolean }) {
  return (
    <div className={`flex items-center justify-between gap-2 ${strong ? "font-bold" : ""} ${muted ? "text-muted-foreground" : ""}`}>
      <dt>{label}</dt><dd className="tabular-nums">{value}</dd>
    </div>
  );
}
