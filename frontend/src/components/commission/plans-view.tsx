"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { CommissionPlans, CommissionRule, CommissionRuleInput, CommissionSettings } from "@/lib/commission-types";
import { deleteCommissionRule, saveCommissionRule, saveCommissionSettings } from "@/lib/commission-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";
import { pctLabel } from "@/components/commission/commission-ui";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";

type Rep = CommissionPlans["reps"][number];

export function PlansView({ data }: { data: CommissionPlans }) {
  const [editing, setEditing] = useState<{ rep: Rep; rule: CommissionRule | null } | null>(null);
  const titleName = Object.fromEntries(data.titles.map((t) => [t.slug, t.name]));
  const reps = data.reps.filter((r) => r.active || r.rules.length);

  return (
    <>
      <SettingsCard settings={data.settings} canEdit={data.can_edit} />
      <div className="grid gap-4 lg:grid-cols-2">
        {reps.map((rep) => (
          <section key={rep.id} className="rounded-xl border border-border/80 bg-card shadow-2xs" aria-labelledby={`rep-${rep.id}`}>
            <header className="flex items-center justify-between gap-2 border-b border-border/70 px-4 py-3">
              <h2 id={`rep-${rep.id}`} className="text-sm font-bold">{rep.name} <span className="font-normal text-muted-foreground">({rep.code})</span></h2>
              {data.can_edit && <Button size="xs" variant="outline" className="gap-1" onClick={() => setEditing({ rep, rule: null })}><Plus className="size-3" /> Add a product</Button>}
            </header>
            {rep.rules.length === 0 ? (
              <p className="px-4 py-3 text-xs text-muted-foreground">No plan, so every booking earns the standard {pctLabel(rep.default_rate)}.</p>
            ) : (
              <ul className="divide-y divide-border/60">
                {rep.rules.map((r) => (
                  <li key={r.id} className="flex items-start gap-2 px-4 py-2.5">
                    <div className="min-w-0 flex-1 text-sm">
                      <div className="font-semibold">{r.name}</div>
                      <p className="text-xs text-muted-foreground">
                        {pctLabel(r.base_rate)} of their revenue{r.new_business_rate ? ` + ${pctLabel(r.new_business_rate)} on new business` : ""}
                        {r.new_business_rate_change_on && r.new_business_rate_after != null ? ` (${pctLabel(r.new_business_rate_after)} for issues from ${fmtDate(r.new_business_rate_change_on)})` : ""}
                        {r.new_client_bonus_gbp ? ` · ${fmtGBP(r.new_client_bonus_gbp)} per new customer` : ""}
                        {r.new_guide_bonus_gbp ? ` · ${fmtGBP(r.new_guide_bonus_gbp)} per new contract-publishing guide` : ""}
                        {r.threshold_bonus_gbp && r.threshold_gbp ? ` · ${fmtGBP(r.threshold_bonus_gbp)} when a title passes ${fmtGBP(r.threshold_gbp)} in a year` : ""}
                        {r.event_profit_rate ? ` · ${pctLabel(r.event_profit_rate)} of each event's profit` : ""}
                      </p>
                      <p className="text-[11px] text-muted-foreground">Covers: {r.title_slugs.map((s) => titleName[s] ?? s).join(", ") || "no titles yet"}</p>
                      {r.notes && <p className="text-[11px] italic text-muted-foreground">{r.notes}</p>}
                    </div>
                    {data.can_edit && <Button size="icon-sm" variant="ghost" aria-label={`Change ${r.name}`} onClick={() => setEditing({ rep, rule: r })}><Pencil className="size-3.5" /></Button>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
      <Sheet open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-lg">
          {editing && <RuleForm key={editing.rule?.id ?? `new-${editing.rep.id}`} rep={editing.rep} rule={editing.rule} titles={data.titles} onDone={() => setEditing(null)} />}
        </SheetContent>
      </Sheet>
    </>
  );
}

function SettingsCard({ settings, canEdit }: { settings: CommissionSettings; canEdit: boolean }) {
  const router = useRouter();
  const [s, setS] = useState(settings);
  const [pending, start] = useTransition();
  const dirty = JSON.stringify(s) !== JSON.stringify(settings);
  return (
    <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs" aria-labelledby="cs-h">
      <h2 id="cs-h" className="mb-3 flex items-center gap-1 text-sm font-bold">How the plans are applied <InfoHint>These are the answers to BMI&apos;s open questions about the structure, so a change here is all it takes when a rule is clarified.</InfoHint></h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className={labelCls}>A booking counts in the month
          <select className={selectCls} disabled={!canEdit} value={s.earned_on} onChange={(e) => setS({ ...s, earned_on: e.target.value as CommissionSettings["earned_on"] })}>
            <option value="publication">its issue publishes or event runs</option>
            <option value="booked">it was booked</option>
          </select>
        </label>
        <label className={labelCls}>New business means no spend in the last
          <span className="flex items-center gap-2"><Input type="number" min={1} max={120} disabled={!canEdit} value={s.lookback_months} onChange={(e) => setS({ ...s, lookback_months: Number(e.target.value) || 24 })} className="h-8 w-20 text-sm" /><span className="font-normal">months</span></span>
        </label>
        <label className={labelCls}>
          <span className="flex items-center gap-1">A new customer&apos;s first deal lasts <InfoHint>0 = only bookings made the same day as their first booking count as new business. Set e.g. 30 if a first deal booked in pieces over a month should all count.</InfoHint></span>
          <span className="flex items-center gap-2"><Input type="number" min={0} max={366} disabled={!canEdit} value={s.first_deal_days} onChange={(e) => setS({ ...s, first_deal_days: Number(e.target.value) || 0 })} className="h-8 w-20 text-sm" /><span className="font-normal">days after the first booking</span></span>
        </label>
        <label className={labelCls}>Event profit is worked out from
          <select className={selectCls} disabled={!canEdit} value={s.event_profit_basis} onChange={(e) => setS({ ...s, event_profit_basis: e.target.value as CommissionSettings["event_profit_basis"] })}>
            <option value="all">the whole event&apos;s income</option>
            <option value="own">only their own sales on it</option>
          </select>
        </label>
      </div>
      {canEdit && dirty && (
        <div className="mt-3 flex justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={() => setS(settings)}>Undo</Button>
          <Button size="sm" disabled={pending} onClick={() => start(async () => {
            try { await saveCommissionSettings(s); toast.success("Saved - unapproved months are worked out again"); router.refresh(); }
            catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save"); }
          })}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
        </div>
      )}
    </section>
  );
}

const pctIn = (v: number | null | undefined) => (v == null ? "" : String(Math.round(v * 10000) / 100));
const numIn = (v: number | null | undefined) => (v == null ? "" : String(v));
const toRate = (v: string) => (v.trim() === "" ? null : Number(v) / 100);
const toNum = (v: string) => (v.trim() === "" ? null : Number(v));

function RuleForm({ rep, rule, titles, onDone }: { rep: Rep; rule: CommissionRule | null; titles: { slug: string; name: string }[]; onDone: () => void }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [f, setF] = useState({
    name: rule?.name ?? "", slugs: rule?.title_slugs ?? [], base: pctIn(rule?.base_rate), nb: pctIn(rule?.new_business_rate),
    change: rule?.new_business_rate_change_on ?? "", after: pctIn(rule?.new_business_rate_after), guide: numIn(rule?.new_guide_bonus_gbp),
    tBonus: numIn(rule?.threshold_bonus_gbp), threshold: numIn(rule?.threshold_gbp), client: numIn(rule?.new_client_bonus_gbp),
    event: pctIn(rule?.event_profit_rate), from: rule?.valid_from ?? "", until: rule?.valid_until ?? "", notes: rule?.notes ?? "",
  });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  function save() {
    if (!f.name.trim()) return toast.error("Give the product a name");
    if (f.base.trim() === "" || Number.isNaN(Number(f.base))) return toast.error("Enter the rate on their revenue");
    const input: CommissionRuleInput = {
      rep_id: rep.id, name: f.name.trim(), title_slugs: f.slugs, base_rate: Number(f.base) / 100, new_business_rate: toRate(f.nb) ?? 0,
      new_business_rate_change_on: f.change || null, new_business_rate_after: f.change ? toRate(f.after) : null,
      new_guide_bonus_gbp: toNum(f.guide), threshold_bonus_gbp: toNum(f.tBonus), threshold_gbp: toNum(f.threshold),
      new_client_bonus_gbp: toNum(f.client), event_profit_rate: toRate(f.event), valid_from: f.from || null, valid_until: f.until || null,
      notes: f.notes.trim() || null,
    };
    start(async () => {
      try { await saveCommissionRule(input, rule?.id); toast.success("Saved"); onDone(); router.refresh(); }
      catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save"); }
    });
  }

  return (
    <>
      <SheetHeader className="border-b border-border/70">
        <SheetTitle>{rule ? rule.name : "Add a product"}</SheetTitle>
        <SheetDescription>{rep.name}&apos;s commission on one product group. Leave a box empty if it doesn&apos;t apply.</SheetDescription>
      </SheetHeader>
      <div className="flex flex-col gap-4 p-4">
        <label className={labelCls}>Product group<Input value={f.name} onChange={set("name")} placeholder="e.g. Selling Travel Magazine (print and digital)" className="h-8 text-sm" /></label>
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1 text-xs font-semibold text-muted-foreground">Titles it covers</legend>
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
            {titles.map((t) => (
              <label key={t.slug} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={f.slugs.includes(t.slug)} onChange={(e) => setF({ ...f, slugs: e.target.checked ? [...f.slugs, t.slug] : f.slugs.filter((x) => x !== t.slug) })} />
                {t.name}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="grid grid-cols-2 gap-3">
          <label className={labelCls}>Rate on their revenue (%)<Input inputMode="decimal" value={f.base} onChange={set("base")} placeholder="5" className="h-8 text-sm" /></label>
          <label className={labelCls}>Extra on new business (%)<Input inputMode="decimal" value={f.nb} onChange={set("nb")} placeholder="2" className="h-8 text-sm" /></label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className={labelCls}><span className="flex items-center gap-1">New business rate changes for issues from <InfoHint>For a temporary rate, like David&apos;s 5% until May 2027: the date and the rate that applies from then on.</InfoHint></span><Input type="date" value={f.change} onChange={set("change")} className="h-8 text-sm" /></label>
          <label className={labelCls}>...to (%)<Input inputMode="decimal" value={f.after} onChange={set("after")} disabled={!f.change} placeholder="2" className="h-8 text-sm" /></label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className={labelCls}>Bonus per new customer (£)<Input inputMode="decimal" value={f.client} onChange={set("client")} className="h-8 text-sm" /></label>
          <label className={labelCls}>Bonus per new contract-publishing guide (£)<Input inputMode="decimal" value={f.guide} onChange={set("guide")} className="h-8 text-sm" /></label>
          <label className={labelCls}>Bonus when a title&apos;s yearly revenue passes (£)<Input inputMode="decimal" value={f.tBonus} onChange={set("tBonus")} placeholder="Bonus" className="h-8 text-sm" /></label>
          <label className={labelCls}>...this much (£)<Input inputMode="decimal" value={f.threshold} onChange={set("threshold")} placeholder="8000" className="h-8 text-sm" /></label>
          <label className={labelCls}>Share of each event&apos;s profit (%)<Input inputMode="decimal" value={f.event} onChange={set("event")} className="h-8 text-sm" /></label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className={labelCls}>Applies from (optional)<Input type="date" value={f.from} onChange={set("from")} className="h-8 text-sm" /></label>
          <label className={labelCls}>Until (optional)<Input type="date" value={f.until} onChange={set("until")} className="h-8 text-sm" /></label>
        </div>
        <label className={labelCls}>Notes<Textarea rows={2} value={f.notes} onChange={set("notes")} className="text-sm" /></label>
      </div>
      <SheetFooter className="flex-row border-t border-border/70">
        {rule && <Button variant="ghost" className="mr-auto gap-1.5 text-destructive hover:text-destructive" disabled={pending} onClick={() => {
          if (!window.confirm(`Remove ${rule.name} from ${rep.name}'s plan?`)) return;
          start(async () => { try { await deleteCommissionRule(rule.id); toast.success("Removed"); onDone(); router.refresh(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't remove"); } });
        }}><Trash2 className="size-3.5" /> Remove</Button>}
        <Button variant="ghost" onClick={onDone}>Cancel</Button>
        <Button disabled={pending} onClick={save}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
      </SheetFooter>
    </>
  );
}
