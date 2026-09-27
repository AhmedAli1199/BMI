"use client";

import Link from "next/link";
import { useState } from "react";
import { Building2, Plus } from "lucide-react";
import type { EditionSummary, Renewals, SalesRep } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";
import { OrderSheet, type OrderSheetTarget } from "@/components/sales/order-sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";

export function RenewalsTable({ data, editions, reps }: { data: Renewals; editions: EditionSummary[]; reps: SalesRep[] }) {
  const today = new Date().toISOString().slice(0, 10);
  const open = editions.filter((e) => e.status === "open");
  const defaultEd = open.find((e) => (e.edition_date ?? "") >= today) ?? open[0] ?? editions[0];
  const [editionId, setEditionId] = useState(defaultEd?.id ?? "");
  const [target, setTarget] = useState<OrderSheetTarget | null>(null);
  const chosen = editions.find((e) => e.id === editionId);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {data.items.length} advertiser{data.items.length === 1 ? "" : "s"} · {fmtGBP(data.not_rebooked_value_gbp)} spent with {data.title.name} last year
        </p>
        {editions.length > 0 && (
          <label className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            Book renewals into
            <select
              value={editionId}
              onChange={(e) => setEditionId(e.target.value)}
              className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              {editions.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.label}
                  {e.edition_date ? ` (${fmtDate(e.edition_date, false)})` : ""}
                  {e.status === "closed" ? " - closed" : ""}
                </option>
              ))}
            </select>
            <InfoHint>&ldquo;Book&rdquo; opens a new booking in this edition, pre-filled with the advertiser, their CRM company, salesperson and last year&apos;s size - adjust anything before saving.</InfoHint>
          </label>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[760px] text-sm">
          <caption className="sr-only">Last year&apos;s advertisers who haven&apos;t rebooked this title yet</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
              <th scope="col" className="px-4 py-2.5 font-semibold">Advertiser</th>
              <th scope="col" className="px-3 py-2.5 font-semibold">Last booking</th>
              <th scope="col" className="px-3 py-2.5 text-right font-semibold">Spent last year</th>
              <th scope="col" className="px-3 py-2.5 font-semibold">Salesperson</th>
              <th scope="col" className="px-4 py-2.5 text-right font-semibold"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((r) => (
              <tr key={r.client_name} className="border-b border-border/60 last:border-0 hover:bg-accent/30">
                <td className="px-4 py-2.5">
                  <div className="font-semibold text-foreground">{r.client_name}</div>
                  {r.company && (
                    <Link href={`/companies/${r.company.id}`} className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary">
                      <Building2 className="size-3" aria-hidden="true" /> {r.company.label}
                    </Link>
                  )}
                </td>
                <td className="px-3 py-2.5 text-xs">
                  <Link href={`/sales/editions/${r.last_edition.id}`} className="font-medium text-foreground hover:text-primary hover:underline">
                    {r.last_edition.label}
                  </Link>
                  <div className="text-[11px] text-muted-foreground">
                    {r.size ?? "—"} · {fmtGBP(r.last_value_gbp)}
                    {r.last_booked_on ? ` · booked ${fmtDate(r.last_booked_on)}` : ""}
                  </div>
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums">
                  <span className="font-semibold">{fmtGBP(r.last_year_value_gbp)}</span>
                  {r.last_year_orders > 1 && <div className="text-[11px] text-muted-foreground">{r.last_year_orders} bookings</div>}
                </td>
                <td className="px-3 py-2.5 text-xs">{r.rep ? r.rep.name : <span className="text-muted-foreground">—</span>}</td>
                <td className="px-4 py-2.5 text-right">
                  <Button
                    size="xs"
                    variant="outline"
                    className="gap-1"
                    disabled={!chosen}
                    aria-label={`Book ${r.client_name} into ${chosen?.label ?? "an edition"}`}
                    onClick={() =>
                      chosen &&
                      setTarget({
                        mode: "create",
                        editionId: chosen.id,
                        titleId: chosen.title.id,
                        year: chosen.year,
                        editionLabel: chosen.label,
                        defaults: {
                          client_name: r.client_name,
                          company: r.company,
                          rep: r.rep,
                          size: r.size,
                          value_gbp: r.last_value_gbp,
                        },
                      })
                    }
                  >
                    <Plus className="size-3" aria-hidden="true" /> Book
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <OrderSheet target={target} reps={reps} canDelete={false} onClose={() => setTarget(null)} />
    </div>
  );
}
