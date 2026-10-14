import Link from "next/link";
import { backendFetch } from "@/lib/backend";
import type { ProposalReport } from "@/lib/proposals-types";
import { SalesHeader, fmtGBP } from "@/components/sales/sales-ui";
import { InfoHint } from "@/components/sales/info-hint";

const PERIODS = [30, 90, 365];

function hours(h: number | null): string {
  if (h == null) return "—";
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} min`;
  if (h < 48) return `${Math.round(h * 10) / 10} h`;
  return `${Math.round(h / 24)} days`;
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-border/80 bg-card p-3 shadow-2xs">
      <p className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">{label}{hint && <InfoHint>{hint}</InfoHint>}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

/** Proposal requests: how many came in, how quickly each got a reply, and how many became bookings. */
export default async function ProposalReportPage({ searchParams }: { searchParams: Promise<{ days?: string; user?: string }> }) {
  const sp = await searchParams;
  const days = PERIODS.includes(Number(sp.days)) ? Number(sp.days) : 90;
  const qs = new URLSearchParams({ days: String(days) });
  if (sp.user) qs.set("user_id", sp.user);
  const r = await backendFetch<ProposalReport>(`/api/proposal-report?${qs}`);
  const t = r.total;
  const link = (patch: Record<string, string | undefined>) => {
    const q = new URLSearchParams({ days: String(days), ...(sp.user ? { user: sp.user } : {}) });
    for (const [k, v] of Object.entries(patch)) { if (v) q.set(k, v); else q.delete(k); }
    return `/sales/proposals/report?${q}`;
  };
  const breakdown = (title: string, data: Record<string, number>) => (
    <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
      <h2 className="mb-2 text-sm font-bold">{title}</h2>
      {Object.keys(data).length === 0 ? <p className="text-xs text-muted-foreground">Nothing yet.</p> : (
        <ul className="flex flex-col gap-1 text-sm">
          {Object.entries(data).sort((a, b) => b[1] - a[1]).map(([k, n]) => <li key={k} className="flex justify-between gap-2"><span>{k}</span><span className="tabular-nums font-semibold">{n}</span></li>)}
        </ul>
      )}
    </section>
  );
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Proposal requests report"
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Proposals", href: "/sales/proposals" }]}
        description="Every email asking for prices or a proposal that the Brain spotted: how many came in, how quickly each got a reply, and how many turned into bookings."
      />
      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" aria-label="Period" className="flex gap-1">
          {PERIODS.map((d) => (
            <Link key={d} role="tab" aria-selected={d === days} href={link({ days: String(d) })}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${d === days ? "border-primary bg-primary/10" : "border-border text-muted-foreground hover:bg-accent/50"}`}>
              Last {d === 365 ? "year" : `${d} days`}
            </Link>
          ))}
        </div>
        {r.staff && (
          <div className="ml-auto flex flex-wrap gap-1 text-xs">
            <Link href={link({ user: undefined })} className={`rounded-full border px-2.5 py-1 ${!sp.user ? "border-primary bg-primary/10" : "border-border text-muted-foreground"}`}>Everyone</Link>
            {r.rows.filter((x) => x.user_id).map((x) => (
              <Link key={x.user_id} href={link({ user: x.user_id ?? undefined })} className={`rounded-full border px-2.5 py-1 ${sp.user === x.user_id ? "border-primary bg-primary/10" : "border-border text-muted-foreground"}`}>{x.name}</Link>
            ))}
          </div>
        )}
      </div>
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" aria-label="Totals">
        <Tile label="Requests" value={String(t.received)} />
        <Tile label="Replied to" value={String(t.replied)} hint="Sent from the card, answered another way, or turned into a full proposal." />
        <Tile label="Usual time to reply" value={hours(t.median_hours)} hint="The middle time between the email arriving and the reply - half were quicker, half slower." />
        <Tile label="Still waiting" value={String(t.waiting)} />
        <Tile label="Became bookings" value={String(t.bookings)} hint="Requests where the client then booked: from the proposal, or any booking for that client made after the request." />
        <Tile label="Booked from them" value={fmtGBP(t.booked_gbp)} hint="Before VAT." />
      </section>
      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[44rem] text-sm">
          <caption className="sr-only">By salesperson</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs text-muted-foreground">
              <th scope="col" className="px-4 py-2 font-semibold">Salesperson</th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">Requests</th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">Replied</th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">Usual time</th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">Not requests</th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">Waiting</th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">Full proposals</th>
              <th scope="col" className="px-4 py-2 text-right font-semibold">Bookings</th>
            </tr>
          </thead>
          <tbody>
            {r.rows.map((x) => (
              <tr key={x.user_id ?? x.name} className="border-b border-border/60 last:border-0">
                <td className="px-4 py-2 font-medium">{x.user_id ? <Link href={`/automations/review?kind=proposal_request`} className="hover:underline">{x.name}</Link> : x.name}</td>
                <td className="px-2 py-2 text-right tabular-nums">{x.received}</td>
                <td className="px-2 py-2 text-right tabular-nums">{x.replied}</td>
                <td className="px-2 py-2 text-right tabular-nums">{hours(x.median_hours)}</td>
                <td className="px-2 py-2 text-right tabular-nums text-muted-foreground">{x.not_requests}</td>
                <td className="px-2 py-2 text-right tabular-nums" style={x.waiting ? { color: "var(--warn)", fontWeight: 600 } : undefined}>{x.waiting}</td>
                <td className="px-2 py-2 text-right tabular-nums">{x.proposals}</td>
                <td className="px-4 py-2 text-right tabular-nums">{x.bookings}{x.booked_gbp ? <span className="ml-1 text-xs text-muted-foreground">{fmtGBP(x.booked_gbp)}</span> : null}</td>
              </tr>
            ))}
            {r.rows.length === 0 && <tr><td colSpan={8} className="px-4 py-6 text-center text-sm text-muted-foreground">No proposal requests in this period. Turn on “Spot proposal requests” in Automations settings to start.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {breakdown("By type of request", r.by_type)}
        {breakdown("By magazine", r.by_magazine)}
      </div>
    </div>
  );
}
