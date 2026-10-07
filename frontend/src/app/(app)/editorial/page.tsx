import Link from "next/link";
import { CalendarRange, Settings2 } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { Deadline, Planner } from "@/lib/editorial-types";
import { Button } from "@/components/ui/button";
import { YearSwitch } from "@/components/sales/sales-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { YearPlanner, PlannerLegend } from "@/components/editorial/year-planner";
import { IssueList } from "@/components/editorial/issue-list";
import { DeadlinesList } from "@/components/editorial/deadlines-list";
import { AddIssueButton } from "@/components/editorial/issue-sheet";
import { LoadPlanButton, PlanNextYearButton } from "@/components/editorial/brand-actions";
import { PrintButton } from "@/components/editorial/print-button";
import { brandColor } from "@/components/rate-card/brand-style";

type SP = { year?: string; view?: string; brand?: string; days?: string };

const VIEWS = [
  { key: "planner", label: "Year planner" },
  { key: "deadlines", label: "Deadlines" },
  { key: "list", label: "List" },
];

/** The editorial plan: every brand's issues, specials and events, their deadlines and planned features. */
export default async function EditorialPage({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const view = VIEWS.some((v) => v.key === sp.view) ? sp.view! : "planner";
  const plan = await backendFetch<Planner>(`/api/editorial/planner${sp.year ? `?year=${Number(sp.year)}` : ""}`);
  const year = plan.year;
  const brands = sp.brand ? plan.brands.filter((b) => b.key === sp.brand) : plan.brands;
  const days = Number(sp.days) || 60;
  const deadlines = view === "deadlines"
    ? await backendFetch<Deadline[]>(`/api/editorial/deadlines?days=${days}&past=3${sp.brand ? `&brand=${sp.brand}` : ""}`).catch(() => [] as Deadline[])
    : [];
  const href = (patch: Partial<SP>) => {
    const p = new URLSearchParams();
    const merged = { year: String(year), view, brand: sp.brand, ...patch };
    for (const [k, v] of Object.entries(merged)) if (v) p.set(k, v);
    return `/editorial?${p}`;
  };
  const seedable = brands.filter((b) => b.can_edit && b.seed_available > 0);
  const empty = brands.every((b) => b.rows.length === 0 && b.undated.length === 0);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
        <div className="min-w-0">
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary"><CalendarRange className="size-3.5" aria-hidden="true" /> Editorial plan</p>
          <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Editorial plan</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Every brand&apos;s issues, specials and events for the year - with their deadlines and the features planned for each. Proposals and renewal emails use it to pitch the right issue.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 print-hide">
          <AddIssueButton brands={plan.brands} year={year} />
          {view !== "deadlines" && <YearSwitch years={plan.years} current={year} href={(y) => href({ year: String(y) })} />}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 print-hide">
        <nav aria-label="View" className="flex items-center gap-0.5 rounded-lg border border-border/80 bg-card p-0.5">
          {VIEWS.map((v) => (
            <Link key={v.key} href={href({ view: v.key })} aria-current={view === v.key ? "page" : undefined}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold ${view === v.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}>{v.label}</Link>
          ))}
        </nav>
        <nav aria-label="Brand" className="flex flex-wrap items-center gap-1.5">
          <Link href={href({ brand: undefined })} aria-current={!sp.brand ? "page" : undefined} className={`rounded-full border px-3 py-1 text-xs font-medium ${!sp.brand ? "border-primary bg-primary/10" : "border-border/80 bg-card hover:bg-muted"}`}>All brands</Link>
          {plan.brands.map((b) => (
            <Link key={b.key} href={href({ brand: b.key })} aria-current={sp.brand === b.key ? "page" : undefined}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${sp.brand === b.key ? "border-primary bg-primary/10" : "border-border/80 bg-card hover:bg-muted"}`}>
              <span className="masthead-rule w-2.5" style={{ background: brandColor(b.key) }} aria-hidden="true" />{b.short}
            </Link>
          ))}
        </nav>
        {view === "deadlines" && (
          <nav aria-label="How far ahead" className="ml-auto flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">Show the next</span>
            {[30, 60, 120, 365].map((d) => <Link key={d} href={href({ days: String(d) })} aria-current={days === d ? "page" : undefined} className={`rounded-md px-2 py-1 font-semibold ${days === d ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"}`}>{d === 365 ? "year" : `${d} days`}</Link>)}
          </nav>
        )}
        {view !== "deadlines" && <span className="ml-auto"><PrintButton /></span>}
      </div>

      {seedable.length > 0 && view !== "deadlines" && (
        <section className="flex flex-wrap items-center gap-3 rounded-xl border border-border/80 bg-card px-4 py-3 shadow-2xs print-hide">
          <p className="min-w-0 flex-1 text-sm"><strong>Your {year} plan is ready to load.</strong> <span className="text-muted-foreground">We&apos;ve read the issues, dates and features from your published features lists and media kits. Dates we could only read as a month are marked “please check”.</span></p>
          {seedable.map((b) => <LoadPlanButton key={b.key} brand={b.key} brandName={b.short} year={year} count={b.seed_available} />)}
        </section>
      )}

      {view === "planner" && !empty && <PlannerLegend />}
      {view === "planner" && (empty ? <EmptyPlan year={year} /> : <YearPlanner brands={brands} year={year} today={plan.today} />)}
      {view === "list" && <IssueList brands={brands} />}
      {view === "deadlines" && <DeadlinesList items={deadlines} />}

      {view !== "deadlines" && (
        <section aria-label="Brand tools" className="grid gap-3 md:grid-cols-3 print-hide">
          {brands.map((b) => (
            <div key={b.key} className="flex flex-col gap-2 rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
              <p className="flex items-center gap-2 text-sm font-bold"><span className="masthead-rule w-4" style={{ background: brandColor(b.key) }} aria-hidden="true" />{b.name}</p>
              {b.about && <p className="text-xs text-muted-foreground">{b.about}</p>}
              {b.undated.length > 0 && <p className="text-xs" style={{ color: "var(--warn)" }}>{b.undated.length} without a date yet: {b.undated.map((u) => u.name).slice(0, 4).join(", ")}{b.undated.length > 4 ? "…" : ""}</p>}
              <div className="mt-auto flex flex-wrap gap-2 pt-1">
                {b.can_edit && b.rows.length > 0 && <PlanNextYearButton brand={b.key} brandName={b.name} fromYear={year} />}
                <Button size="sm" variant="ghost" className="gap-1.5" nativeButton={false} render={<Link href={`/editorial/settings/${b.key}`} />}><Settings2 className="size-3.5" /> Deadline rules &amp; sections</Button>
              </div>
            </div>
          ))}
        </section>
      )}
      <p className="flex items-center gap-1 text-xs text-muted-foreground print-hide">
        Who can change the plan
        <InfoHint>Admins and data managers can change every brand. Each brand&apos;s publishers can change their own brand&apos;s plan. Everyone can view it.</InfoHint>
      </p>
    </div>
  );
}

function EmptyPlan({ year }: { year: number }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border/80 bg-card/60 px-6 py-12 text-center">
      <CalendarRange className="size-8 text-muted-foreground" aria-hidden="true" />
      <p className="text-base font-bold">Nothing planned for {year} yet</p>
      <p className="max-w-md text-sm text-muted-foreground">Add an issue or event with the button at the top, or go to last year and use “Plan {year}” to copy it forward.</p>
    </div>
  );
}
