"use client";

import { Fragment, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, Download, ExternalLink, Lock, Printer } from "lucide-react";
import { toast } from "sonner";
import type { CommissionLine, CommissionStatement } from "@/lib/commission-types";
import { approveStatement, decideNewBusiness } from "@/lib/commission-actions";
import { downloadFile } from "@/lib/download";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { InfoHint } from "@/components/sales/info-hint";
import { SalesHeader, fmtDate, fmtGBP } from "@/components/sales/sales-ui";
import { NewBusinessPill, monthLabel, pctLabel } from "@/components/commission/commission-ui";
import { friendlyError } from "@/lib/errors";

function shift(period: string, d: number) {
  const [y, m] = period.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1 + d, 1));
  return `${t.getUTCFullYear()}-${String(t.getUTCMonth() + 1).padStart(2, "0")}`;
}

function Tile({ label, value, hint, strong }: { label: string; value: string; hint?: string; strong?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 shadow-2xs ${strong ? "border-primary/40 bg-primary/5" : "border-border/80 bg-card"}`}>
      <div className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">{label}{hint && <InfoHint>{hint}</InfoHint>}</div>
      <div className={`mt-1 tabular-nums ${strong ? "text-2xl font-bold" : "text-lg font-semibold"}`}>{value}</div>
    </div>
  );
}

export function StatementView({ s }: { s: CommissionStatement }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [confirm, setConfirm] = useState(false);
  const [ask, setAsk] = useState<CommissionLine | null>(null);
  const [askReason, setAskReason] = useState("");
  const locked = !!s.approved;
  const earnedWord = s.settings.earned_on === "booked" ? "booked" : "published or held";
  const thisMonth = new Date().toISOString().slice(0, 7);
  const checks = s.lines.filter((l) => l.new_business === "check");
  const groups = s.groups.map((g) => ({ ...g, lines: s.lines.filter((l) => l.group === g.name) }));

  function decide(l: CommissionLine, decision: "new" | "returning" | null, reason?: string) {
    start(async () => {
      try {
        await decideNewBusiness(l.order_id, decision, reason);
        toast.success(decision === null ? "Back to the automatic decision" : decision === "new" ? `${l.client}: new business` : `${l.client}: returning customer`);
        router.refresh();
      } catch (e) { toast.error(friendlyError(e, "Couldn't save that")); }
    });
  }

  function onDecideAndClose(l: CommissionLine) {
    decide(l, l.new_business === "new" ? "returning" : "new", askReason.trim());
    setAsk(null);
  }

  return (
    <>
      <SalesHeader
        title={`${s.rep.name}: ${monthLabel(s.period)}`}
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Commissions", href: `/sales/commissions?year=${s.period.slice(0, 4)}` }]}
        description={`Bookings ${earnedWord} in ${monthLabel(s.period)} that ${s.rep.name.split(" ")[0]} has credit for, the rate each one earned and why. Amounts are before VAT.`}
        actions={<div className="print-hide flex flex-wrap items-center gap-2">
          <Button size="sm" variant="ghost" className="gap-1" nativeButton={false} render={<Link href={`/sales/commissions/${s.rep.id}/${shift(s.period, -1)}`} />}><ChevronLeft className="size-3.5" /> {monthLabel(shift(s.period, -1), true)}</Button>
          {shift(s.period, 1) <= thisMonth && <Button size="sm" variant="ghost" className="gap-1" nativeButton={false} render={<Link href={`/sales/commissions/${s.rep.id}/${shift(s.period, 1)}`} />}>{monthLabel(shift(s.period, 1), true)} <ChevronRight className="size-3.5" /></Button>}
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => downloadFile(`/api/files/commission/statement.xlsx?rep_id=${s.rep.id}&period=${s.period}`, "commission.xlsx").catch((e) => toast.error(friendlyError(e, "Couldn't download")))}><Download className="size-3.5" /> Excel</Button>
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => window.print()}><Printer className="size-3.5" /> Print</Button>
          {s.can_approve && <Button size="sm" className="gap-1.5" disabled={pending || checks.length > 0} title={checks.length ? "Decide the bookings marked “Needs a decision” first" : undefined} onClick={() => setConfirm(true)}><Lock className="size-3.5" /> Approve this month</Button>}
        </div>}
      />

      {locked && (
        <div className="flex flex-wrap items-start gap-2 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "color-mix(in oklab, var(--ok) 40%, transparent)", background: "color-mix(in oklab, var(--ok) 8%, transparent)" }}>
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" style={{ color: "var(--ok)" }} aria-hidden="true" />
          <p className="min-w-0 flex-1">
            <strong>Approved{s.approved?.at ? ` on ${fmtDate(s.approved.at.slice(0, 10))}` : ""}{s.approved?.by_name ? ` by ${s.approved.by_name}` : ""}.</strong>{" "}
            <span className="text-muted-foreground">These are the figures that were paid; they don&apos;t change.</span>
            {Math.abs(s.approved?.changed_since_gbp ?? 0) >= 0.01 && <> Bookings for this month have changed since, by <strong>{fmtGBP(s.approved!.changed_since_gbp)}</strong>; that goes on the next statement as an adjustment.</>}
          </p>
        </div>
      )}

      {checks.length > 0 && !locked && (
        <section className="rounded-xl border px-4 py-3" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }} aria-labelledby="chk-h">
          <h2 id="chk-h" className="flex items-center gap-2 text-sm font-bold"><AlertTriangle className="size-4" style={{ color: "var(--warn)" }} aria-hidden="true" />{checks.length === 1 ? "1 booking needs" : `${checks.length} bookings need`} a decision on new business</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">A similar name has spent with BMI in the last {s.settings.lookback_months} months. Is it the same customer? The month can be approved once these are decided.</p>
          <ul className="mt-2 flex flex-col divide-y divide-border/60">
            {checks.map((l) => <CheckRow key={l.order_id} l={l} canDecide={s.can_decide} pending={pending} onDecide={decide} />)}
          </ul>
        </section>
      )}

      {s.flags.map((f) => <p key={f} className="text-xs" style={{ color: "var(--warn)" }}>{f}</p>)}

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" aria-label="Totals">
        <Tile label="Their revenue" value={fmtGBP(s.totals.share_gbp)} hint="Their credited share of each booking, after any agency's cut." />
        <Tile label="Commission" value={fmtGBP(s.totals.base_gbp)} hint="The plan's rate on their revenue, product by product." />
        <Tile label="New business top-up" value={fmtGBP(s.totals.new_business_gbp)} hint={`The extra rate on bookings from customers who hadn't spent with BMI in the previous ${s.settings.lookback_months} months.`} />
        <Tile label="Bonuses" value={fmtGBP(s.totals.bonuses_gbp)} />
        <Tile label="Event profit share" value={fmtGBP(s.totals.event_profit_gbp)} hint="A share of each event's profit, in the month its costs are signed off." />
        <Tile label="Total" value={fmtGBP(s.totals.total_gbp ?? s.totals.core_gbp)} strong hint={s.totals.adjustments_gbp ? `Includes ${fmtGBP(s.totals.adjustments_gbp)} of adjustments for earlier months.` : undefined} />
      </section>

      {s.lines.length === 0 && s.bonuses.length === 0 && s.events.length === 0 && (s.adjustments ?? []).length === 0 ? (
        <p className="rounded-xl border border-border/80 bg-card p-6 text-center text-sm text-muted-foreground">Nothing {earnedWord} this month.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
          <table className="w-full min-w-[62rem] text-sm">
            <caption className="sr-only">Bookings and commission</caption>
            <thead>
              <tr className="border-b border-border/70 text-left text-xs text-muted-foreground">
                <th scope="col" className="px-4 py-2 font-semibold">Issue or event</th>
                <th scope="col" className="px-2 py-2 font-semibold">Client</th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">Their share</th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">Rate</th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">Commission</th>
                <th scope="col" className="px-2 py-2 font-semibold">New business</th>
                <th scope="col" className="px-4 py-2 text-right font-semibold">Total</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <Fragment key={g.name}>
                  <tr className="border-b border-border/70 bg-muted/30">
                    <th colSpan={7} scope="colgroup" className="px-4 py-2 text-left text-xs font-bold">
                      {g.name} <span className="font-normal text-muted-foreground">· {g.bookings} booking{g.bookings === 1 ? "" : "s"} · {fmtGBP(g.share_gbp)} revenue · {fmtGBP(g.commission_gbp)} commission</span>
                    </th>
                  </tr>
                  {g.lines.map((l) => <LineRow key={l.order_id} l={l} canDecide={s.can_decide} pending={pending} onDecide={decide} onAsk={(x) => { setAsk(x); setAskReason(""); }} />)}
                </Fragment>
              ))}
              {s.bonuses.length > 0 && <>
                <tr className="border-b border-border/70 bg-muted/30"><th colSpan={7} scope="colgroup" className="px-4 py-2 text-left text-xs font-bold">Bonuses</th></tr>
                {s.bonuses.map((b, i) => (
                  <tr key={i} className="border-b border-border/60">
                    <td colSpan={6} className="px-4 py-2">
                      <span className="font-medium">{b.label}</span> <span className="text-xs text-muted-foreground">· {b.group} · {b.reason}</span>
                      {b.edition_id && <Link href={`/sales/editions/${b.edition_id}`} target="_blank" rel="noreferrer" className="ml-1 inline-flex text-primary"><ExternalLink className="size-3" aria-label="Open the edition" /></Link>}
                    </td>
                    <td className="px-4 py-2 text-right font-semibold tabular-nums">{fmtGBP(b.amount_gbp)}</td>
                  </tr>
                ))}
              </>}
              {s.events.length > 0 && <>
                <tr className="border-b border-border/70 bg-muted/30"><th colSpan={7} scope="colgroup" className="px-4 py-2 text-left text-xs font-bold">Event profit share <span className="font-normal text-muted-foreground">· events whose costs were signed off this month</span></th></tr>
                {s.events.map((e) => (
                  <tr key={e.edition_id} className="border-b border-border/60">
                    <td colSpan={6} className="px-4 py-2">
                      <Link href={`/sales/editions/${e.edition_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">{e.edition} <ExternalLink className="size-3" aria-hidden="true" /></Link>
                      <span className="ml-1 text-xs text-muted-foreground">
                        {fmtGBP(e.income_gbp)} income ({e.basis}) − {fmtGBP(e.costs_gbp)} costs = {fmtGBP(e.profit_gbp)} profit × {pctLabel(e.rate)}
                        {e.loss && " · made a loss, so nothing is due"}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right font-semibold tabular-nums">{fmtGBP(e.amount_gbp)}</td>
                  </tr>
                ))}
              </>}
              {(s.adjustments ?? []).map((a) => (
                <tr key={a.period} className="border-b border-border/60">
                  <td colSpan={6} className="px-4 py-2">
                    <Link href={`/sales/commissions/${s.rep.id}/${a.period}`} className="font-medium text-primary hover:underline">{a.label}</Link>
                    <span className="ml-1 text-xs text-muted-foreground">· bookings in an approved month changed after it was paid</span>
                  </td>
                  <td className="px-4 py-2 text-right font-semibold tabular-nums">{fmtGBP(a.amount_gbp)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-muted/30">
                <td colSpan={2} className="px-4 py-2.5 text-sm font-bold">Total</td>
                <td className="px-2 py-2.5 text-right font-semibold tabular-nums">{fmtGBP(s.totals.share_gbp)}</td>
                <td />
                <td className="px-2 py-2.5 text-right tabular-nums">{fmtGBP(s.totals.base_gbp)}</td>
                <td className="px-2 py-2.5 text-xs tabular-nums">+ {fmtGBP(s.totals.new_business_gbp)} top-up</td>
                <td className="px-4 py-2.5 text-right text-base font-bold tabular-nums">{fmtGBP(s.totals.total_gbp ?? s.totals.core_gbp)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <details className="print-hide rounded-xl border border-border/80 bg-card shadow-2xs">
        <summary className="cursor-pointer px-4 py-3 text-sm font-bold">{s.rep.name.split(" ")[0]}&apos;s plan</summary>
        <ul className="flex flex-col gap-1.5 border-t border-border/70 px-4 py-3 text-sm">
          {s.plan.length === 0 && <li className="text-muted-foreground">No plan yet, so every booking uses the standard rate.</li>}
          {s.plan.map((r) => (
            <li key={r.id}>
              <strong>{r.name}</strong>: {pctLabel(r.base_rate)} of their revenue
              {r.new_business_rate ? `, plus ${pctLabel(r.new_business_rate)} on new business` : ""}
              {r.new_business_rate_change_on && r.new_business_rate_after != null ? ` (${pctLabel(r.new_business_rate_after)} for issues from ${fmtDate(r.new_business_rate_change_on)})` : ""}
              {r.new_client_bonus_gbp ? `, ${fmtGBP(r.new_client_bonus_gbp)} per new customer` : ""}
              {r.new_guide_bonus_gbp ? `, ${fmtGBP(r.new_guide_bonus_gbp)} per new contract-publishing guide` : ""}
              {r.threshold_bonus_gbp && r.threshold_gbp ? `, ${fmtGBP(r.threshold_bonus_gbp)} when a title passes ${fmtGBP(r.threshold_gbp)} in a year` : ""}
              {r.event_profit_rate ? `, ${pctLabel(r.event_profit_rate)} of each event's profit` : ""}
            </li>
          ))}
        </ul>
      </details>

      <Dialog open={!!ask} onOpenChange={(o) => !o && setAsk(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{ask?.new_business === "new" ? `${ask?.client} isn't new business?` : `${ask?.client} is new business?`}</DialogTitle>
            <DialogDescription>{ask?.new_business_reason}. Your decision replaces the automatic one for this booking and is kept in its history.</DialogDescription>
          </DialogHeader>
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Why
            <Input autoFocus value={askReason} onChange={(e) => setAskReason(e.target.value)} placeholder={ask?.new_business === "new" ? "e.g. same group as Hilton, who booked in March" : "e.g. a different company with a similar name"} className="h-8 text-sm" />
          </label>
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>Cancel</DialogClose>
            <Button disabled={pending || !askReason.trim()} onClick={() => { if (ask) onDecideAndClose(ask); }}>{ask?.new_business === "new" ? "Mark as returning" : "Mark as new business"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve {s.rep.name}&apos;s {monthLabel(s.period)}?</DialogTitle>
            <DialogDescription>
              {fmtGBP(s.totals.total_gbp)} is locked as the amount due. Later changes to these bookings won&apos;t alter it; they go on the next statement as an adjustment.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>Cancel</DialogClose>
            <Button disabled={pending} onClick={() => start(async () => {
              try { await approveStatement(s.rep.id, s.period); toast.success("Approved"); setConfirm(false); router.refresh(); }
              catch (e) { toast.error(friendlyError(e, "Couldn't approve")); }
            })}>Approve</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

type Decide = (l: CommissionLine, decision: "new" | "returning" | null, reason?: string) => void;

function CheckRow({ l, canDecide, pending, onDecide }: { l: CommissionLine; canDecide: boolean; pending: boolean; onDecide: Decide }) {
  const [reason, setReason] = useState("");
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1.5 py-2 text-sm">
      <div className="min-w-0 flex-1">
        <span className="font-semibold">{l.client}</span> <span className="text-xs text-muted-foreground">· {l.edition} · {fmtGBP(l.share_gbp)}</span>
        <p className="text-xs text-muted-foreground">{l.new_business_reason}</p>
      </div>
      {canDecide && <>
        <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why (optional)" className="h-7 w-48 text-xs" aria-label={`Reason for ${l.client}`} />
        <Button size="xs" variant="outline" disabled={pending} onClick={() => onDecide(l, "new", reason || "A different customer from the similar name")}>New business</Button>
        <Button size="xs" variant="outline" disabled={pending} onClick={() => onDecide(l, "returning", reason || "Same customer as the similar name")}>Same customer</Button>
      </>}
    </li>
  );
}

function LineRow({ l, canDecide, pending, onDecide, onAsk }: { l: CommissionLine; canDecide: boolean; pending: boolean; onDecide: Decide; onAsk: (l: CommissionLine) => void }) {
  return (
    <tr className="border-b border-border/60 align-top">
      <td className="px-4 py-2">
        <Link href={`/sales/editions/${l.edition_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">{l.edition} <ExternalLink className="size-3" aria-hidden="true" /></Link>
        <div className="text-[11px] text-muted-foreground">{l.publication ? `Published ${fmtDate(l.publication)}` : `Booked ${fmtDate(l.booked_on)}`}{l.size ? ` · ${l.size}` : ""}</div>
      </td>
      <td className="px-2 py-2">
        {l.company_id ? <Link href={`/companies/${l.company_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">{l.client} <ExternalLink className="size-3 text-muted-foreground" aria-hidden="true" /></Link> : l.client}
        {l.booked_on && <div className="text-[11px] text-muted-foreground">Booked {fmtDate(l.booked_on)}</div>}
      </td>
      <td className="px-2 py-2 text-right tabular-nums">
        {fmtGBP(l.share_gbp)}
        {(l.split || l.agency_cut) && <div className="text-[11px] text-muted-foreground">{l.split ? `of ${fmtGBP(l.value_gbp)}` : ""}{l.agency_cut ? " after agency cut" : ""}</div>}
      </td>
      <td className="px-2 py-2 text-right tabular-nums" title={l.base_source}>
        {pctLabel(l.base_rate)}
        {l.flags.length > 0 && <div className="text-[11px]" style={{ color: "var(--warn)" }} title={l.flags.join(" ")}>not in plan</div>}
      </td>
      <td className="px-2 py-2 text-right tabular-nums">{fmtGBP(l.base_gbp)}</td>
      <td className="max-w-[18rem] px-2 py-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <NewBusinessPill status={l.new_business} manager={l.new_business_decided_by === "manager"} />
          {l.new_business_gbp > 0 && <span className="text-xs tabular-nums">+{fmtGBP(l.new_business_gbp)} ({pctLabel(l.new_business_rate)})</span>}
        </div>
        <div className="text-[11px] text-muted-foreground">{l.new_business_reason}</div>
        {canDecide && l.new_business !== "check" && (
          <div className="print-hide mt-0.5 flex gap-2 text-[11px]">
            {l.new_business_decided_by === "manager"
              ? <button type="button" disabled={pending} className="font-semibold text-primary hover:underline" onClick={() => onDecide(l, null)}>Undo decision</button>
              : <button type="button" disabled={pending} className="font-semibold text-primary hover:underline" onClick={() => onAsk(l)}>{l.new_business === "new" ? "Not new business?" : "Is new business?"}</button>}
          </div>
        )}
      </td>
      <td className="px-4 py-2 text-right font-semibold tabular-nums">{fmtGBP(l.commission_gbp)}</td>
    </tr>
  );
}
