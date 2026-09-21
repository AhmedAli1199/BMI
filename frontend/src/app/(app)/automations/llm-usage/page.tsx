import Link from "next/link";
import { ArrowLeft, Coins, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { LlmUsageSummary } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const DAY_OPTIONS = [
  { value: 7, label: "7 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
] as const;

const GRANULARITY_OPTIONS = [
  { value: "hour", label: "By hour" },
  { value: "day", label: "By day" },
] as const;

function formatCost(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

function formatBucketLabel(iso: string, granularity: string): string {
  const d = new Date(iso);
  return granularity === "hour"
    ? d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric" })
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/** Deliberately not linked from anywhere a reviewer visits day to day -
 * only from the Automations Settings page's own subtle link. "How much
 * are we spending on AI calls" is an occasional check-in, not a metric
 * that belongs on a regularly used screen. Every real Gemini/OpenAI call
 * anywhere in the codebase logs one row (see backend/app/automations/
 * llm.py's LlmUsageEvent write) - this page only aggregates and displays
 * them, it never computes cost itself. */
export default async function LlmUsagePage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string; granularity?: string }>;
}) {
  const { days: rawDays, granularity: rawGranularity } = await searchParams;
  const days = DAY_OPTIONS.some((d) => String(d.value) === rawDays) ? Number(rawDays) : 30;
  const granularity = GRANULARITY_OPTIONS.some((g) => g.value === rawGranularity) ? rawGranularity! : "day";

  const summary = await backendFetch<LlmUsageSummary>(
    `/api/automations/llm-usage?days=${days}&granularity=${granularity}`
  );

  const hrefFor = (nextDays: number, nextGranularity: string) =>
    `/automations/llm-usage?days=${nextDays}&granularity=${nextGranularity}`;

  const successRate = summary.total_calls > 0
    ? Math.round(((summary.total_calls - summary.total_failures) / summary.total_calls) * 100)
    : 100;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div>
        <Link
          href="/automations/settings"
          className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Automations Settings
        </Link>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles className="size-3.5" />
          <span>LLM usage &amp; cost</span>
        </div>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          What the AI calls are costing
        </h1>
        <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
          Every real Gemini/OpenAI call any automation makes is logged here - tokens used and an
          estimated dollar cost from the price-per-1M-tokens settings in effect at the time. Estimates,
          not an invoice - cross-check against the provider&apos;s own billing page for exact figures.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 rounded-lg border border-border/70 p-0.5">
          {DAY_OPTIONS.map((d) => (
            <Link key={d.value} href={hrefFor(d.value, granularity)}>
              <span
                className={`inline-block rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                  days === d.value ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {d.label}
              </span>
            </Link>
          ))}
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-border/70 p-0.5">
          {GRANULARITY_OPTIONS.map((g) => (
            <Link key={g.value} href={hrefFor(days, g.value)}>
              <span
                className={`inline-block rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                  granularity === g.value ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {g.label}
              </span>
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="editorial-card">
          <CardContent className="flex flex-col gap-1 p-4">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
              <Coins className="size-3.5" /> Total cost
            </span>
            <span className="text-xl font-bold text-foreground">{formatCost(summary.total_cost_usd)}</span>
          </CardContent>
        </Card>
        <Card className="editorial-card">
          <CardContent className="flex flex-col gap-1 p-4">
            <span className="text-xs font-semibold text-muted-foreground">Total calls</span>
            <span className="text-xl font-bold text-foreground">{summary.total_calls.toLocaleString()}</span>
          </CardContent>
        </Card>
        <Card className="editorial-card">
          <CardContent className="flex flex-col gap-1 p-4">
            <span className="text-xs font-semibold text-muted-foreground">Success rate</span>
            <span className={`text-xl font-bold ${successRate < 90 ? "text-[var(--warn)]" : "text-foreground"}`}>
              {successRate}%
            </span>
          </CardContent>
        </Card>
        <Card className="editorial-card">
          <CardContent className="flex flex-col gap-1 p-4">
            <span className="text-xs font-semibold text-muted-foreground">Total tokens</span>
            <span className="text-xl font-bold text-foreground">
              {(summary.total_prompt_tokens + summary.total_completion_tokens).toLocaleString()}
            </span>
          </CardContent>
        </Card>
      </div>

      <Card className="editorial-card">
        <CardHeader className="border-b pb-3">
          <span className="text-sm font-bold text-foreground">Usage over time</span>
        </CardHeader>
        <CardContent className="p-0">
          {summary.buckets.length === 0 ? (
            <p className="p-4 text-xs text-muted-foreground">No LLM calls recorded in this range.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Calls</TableHead>
                  <TableHead className="text-right">Failures</TableHead>
                  <TableHead className="text-right">Tokens</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...summary.buckets].reverse().map((b) => (
                  <TableRow key={b.bucket_start}>
                    <TableCell className="text-xs font-medium">{formatBucketLabel(b.bucket_start, granularity)}</TableCell>
                    <TableCell className="text-right text-xs">{b.call_count.toLocaleString()}</TableCell>
                    <TableCell className={`text-right text-xs ${b.failure_count > 0 ? "text-[var(--warn)] font-semibold" : ""}`}>
                      {b.failure_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right text-xs">{(b.prompt_tokens + b.completion_tokens).toLocaleString()}</TableCell>
                    <TableCell className="text-right text-xs font-semibold">{formatCost(b.cost_usd)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card className="editorial-card">
        <CardHeader className="border-b pb-3">
          <span className="text-sm font-bold text-foreground">By automation</span>
        </CardHeader>
        <CardContent className="p-0">
          {summary.by_purpose.length === 0 ? (
            <p className="p-4 text-xs text-muted-foreground">No LLM calls recorded in this range.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Purpose</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead className="text-right">Calls</TableHead>
                  <TableHead className="text-right">Failures</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.by_purpose.map((p) => (
                  <TableRow key={`${p.purpose}:${p.provider}`}>
                    <TableCell className="text-xs font-medium">{p.purpose}</TableCell>
                    <TableCell className="text-xs capitalize text-muted-foreground">{p.provider}</TableCell>
                    <TableCell className="text-right text-xs">{p.call_count.toLocaleString()}</TableCell>
                    <TableCell className={`text-right text-xs ${p.failure_count > 0 ? "text-[var(--warn)] font-semibold" : ""}`}>
                      {p.failure_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right text-xs font-semibold">{formatCost(p.cost_usd)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
