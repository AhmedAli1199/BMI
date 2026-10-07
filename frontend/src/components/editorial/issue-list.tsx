import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import type { PlannerBrand } from "@/lib/editorial-types";
import { KIND_LABELS, issueLabel } from "@/lib/editorial-types";
import { brandColor } from "@/components/rate-card/brand-style";
import { fmtGBP } from "@/components/sales/sales-ui";
import { fmtDay } from "@/components/editorial/editorial-ui";

/** The same plan as a table - easier to scan, print and read with a screen reader. */
export function IssueList({ brands }: { brands: PlannerBrand[] }) {
  return (
    <div className="flex flex-col gap-5">
      {brands.map((b) => {
        const issues = [...b.rows.flatMap((r) => r.issues), ...b.undated].sort((x, y) => (x.edition_date ?? "9999").localeCompare(y.edition_date ?? "9999"));
        return (
          <section key={b.key} aria-labelledby={`l-${b.key}`} className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs print-avoid-break">
            <header className="flex items-center gap-2 border-b border-border/70 px-4 py-2.5">
              <span className="masthead-rule w-6" style={{ background: brandColor(b.key) }} aria-hidden="true" />
              <h2 id={`l-${b.key}`} className="text-sm font-bold">{b.name}</h2>
              <span className="text-xs text-muted-foreground">{issues.length} planned</span>
            </header>
            {issues.length === 0 ? <p className="px-4 py-4 text-xs text-muted-foreground">Nothing planned yet.</p> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[48rem] text-sm">
                  <caption className="sr-only">{b.name} plan</caption>
                  <thead>
                    <tr className="text-left text-xs text-muted-foreground">
                      <th scope="col" className="px-4 py-2 font-semibold">What</th>
                      <th scope="col" className="px-2 py-2 font-semibold">Publishes / on</th>
                      <th scope="col" className="px-2 py-2 font-semibold">Advertising deadline</th>
                      <th scope="col" className="px-2 py-2 font-semibold">Editorial deadline</th>
                      <th scope="col" className="px-2 py-2 text-right font-semibold">Features</th>
                      <th scope="col" className="px-4 py-2 text-right font-semibold">Booked</th>
                    </tr>
                  </thead>
                  <tbody>
                    {issues.map((i) => (
                      <tr key={i.id} className="border-t border-border/60 align-top hover:bg-muted/30">
                        <td className="px-4 py-2">
                          <Link href={`/editorial/issues/${i.id}`} className="font-semibold hover:underline">{issueLabel(i)}</Link>
                          {i.needs_check && <AlertTriangle className="ml-1.5 inline size-3.5" style={{ color: "var(--warn)" }} aria-label="Some dates need checking" />}
                          <p className="text-xs text-muted-foreground">{i.title_name} · {KIND_LABELS[i.kind]}{i.period_label ? ` · ${i.period_label}` : ""}</p>
                          {i.theme && <p className="text-xs text-muted-foreground">{i.theme}</p>}
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap">{fmtDay(i.edition_date, true)}</td>
                        <td className="px-2 py-2 whitespace-nowrap">{fmtDay(i.ad_deadline)}</td>
                        <td className="px-2 py-2 whitespace-nowrap">{fmtDay(i.editorial_deadline)}</td>
                        <td className="px-2 py-2 text-right tabular-nums">{i.features || "—"}</td>
                        <td className="px-4 py-2 text-right tabular-nums">{i.orders ? fmtGBP(i.booked_gbp) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
