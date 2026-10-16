import Link from "next/link";
import { redirect } from "next/navigation";
import { ExternalLink, ThumbsDown, ThumbsUp, TriangleAlert } from "lucide-react";
import { getSession } from "@/lib/session";
import { brainActivity } from "@/lib/brain-actions";
import type { BrainActivity } from "@/lib/brain-types";
import { HubHeader } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";

/** Admins: what people ask the assistant, how quick and how cheap it is, and which answers didn't help. */
export default async function ActivityPage() {
  const session = await getSession();
  if (session?.role !== "admin") redirect("/brain");
  const data: BrainActivity = await brainActivity(14).catch(() => ({ items: [], summary: { answers: 0, helpful: 0, not_helpful: 0, avg_seconds: null, cache_hit_pct: null } }));
  const s = data.summary;
  const tiles = [
    { label: "Answers (14 days)", value: String(s.answers) },
    { label: "Helpful / not", value: `${s.helpful} / ${s.not_helpful}` },
    { label: "Average time to answer", value: s.avg_seconds != null ? `${s.avg_seconds}s` : "-" },
    { label: "Served from the cache", value: s.cache_hit_pct != null ? `${s.cache_hit_pct}%` : "-",
      hint: "How much of what the Brain reads each time was already cached by Google - cached text costs about a tenth and is quicker. Higher is better." },
  ];
  const idx = data.index;
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <HubHeader title="What people asked the Brain" description="Every question from the last two weeks, what it looked up, how long it took and whether it helped. Answers marked not helpful show what to add to the help guides." />
      <div className="grid gap-3 sm:grid-cols-4">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
            <p className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">{t.label}{t.hint && <InfoHint>{t.hint}</InfoHint>}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{t.value}</p>
          </div>
        ))}
      </div>
      {idx && (
        <p className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
          Notes and history it can search: <strong className="text-foreground tabular-nums">{idx.chunks.toLocaleString("en-GB")}</strong> pieces
          {idx.meaning_search ? <> · {idx.embedded.toLocaleString("en-GB")} searchable by meaning</> : <> · searching by exact words only</>}
          {idx.last_indexed && <> · last updated {new Date(idx.last_indexed).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</>}
          <InfoHint>{idx.meaning_search
            ? "Every 15 minutes new and changed notes, history, activities and call notes are added. Searching by meaning finds a note even when it uses different words."
            : "Searching by meaning isn't switched on for this database yet. Until it is, the Brain finds notes by their exact words, which still works well for names, rates and dates."}</InfoHint>
        </p>
      )}
      {data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">Nobody has asked anything yet.</p>
      ) : (
        <ul className="divide-y divide-border/60 rounded-xl border border-border/80 bg-card shadow-2xs">
          {data.items.map((i) => (
            <li key={i.id} className="grid gap-1 px-4 py-3 sm:grid-cols-[1fr_auto]">
              <div className="min-w-0">
                <p className="text-sm font-medium">{i.question || "(pointed at something)"}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{i.answer}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {i.who} · {new Date(i.at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                  {i.page && <> · <Link href={i.page} target="_blank" rel="noreferrer" className="hover:underline">{i.page}</Link></>}
                  {i.steps.length > 0 && <> · {i.steps.join(", ")}</>}
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs tabular-nums text-muted-foreground sm:justify-end">
                {i.problem && <span className="inline-flex items-center gap-1" style={{ color: "var(--destructive)" }}><TriangleAlert className="size-3" /> Didn&apos;t answer</span>}
                {i.ms != null && <span>{(i.ms / 1000).toFixed(1)}s</span>}
                {i.input_tokens ? <span title="Of what it read, how much came from the cache">{Math.round(100 * (i.cached_tokens ?? 0) / i.input_tokens)}% cached</span> : null}
                {i.rating === 1 && <ThumbsUp className="size-3.5" style={{ color: "var(--ok)" }} aria-label="Helpful" />}
                {i.rating === -1 && <ThumbsDown className="size-3.5" style={{ color: "var(--destructive)" }} aria-label="Not helpful" />}
                {i.feedback_id && <Link href={`/feedback?open=${i.feedback_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-primary hover:underline">Feedback <ExternalLink className="size-3" /></Link>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
