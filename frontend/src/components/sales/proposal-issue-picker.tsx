"use client";

import { useEffect, useState } from "react";
import type { UpcomingIssue } from "@/lib/proposals-types";
import { getUpcomingIssues } from "@/lib/proposals-actions";
import { fmtDate } from "@/components/sales/sales-ui";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60 dark:bg-input/30";

export function issueOptionLabel(i: UpcomingIssue): string {
  const bits = [i.label];
  if (i.edition_date) bits.push(`${i.kind === "issue" || i.kind === "guide" ? "out" : "on"} ${fmtDate(i.edition_date)}`);
  if (i.ad_deadline) bits.push(i.open ? `book by ${fmtDate(i.ad_deadline)}` : "advertising closed");
  return bits.join(" · ");
}

/** The title's upcoming issues from the editorial plan. Empty value = `emptyLabel` (e.g. "pick the next one for me"). */
export function ProposalIssuePicker({ titleId, value, onChange, include, emptyLabel, disabled, id }: {
  titleId: string | null;
  value: string;
  onChange: (id: string, issue: UpcomingIssue | null) => void;
  include?: string | null;
  emptyLabel: string;
  disabled?: boolean;
  id?: string;
}) {
  const [loaded, setLoaded] = useState<{ key: string; issues: UpcomingIssue[] } | null>(null);
  const key = `${titleId ?? ""}:${include ?? ""}`;

  useEffect(() => {
    if (!titleId) return;
    let live = true;
    getUpcomingIssues(titleId, include)
      .then((r) => live && setLoaded({ key, issues: r }))
      .catch(() => live && setLoaded({ key, issues: [] }));
    return () => { live = false; };
  }, [titleId, include, key]);

  const issues = titleId && loaded?.key === key ? loaded.issues : [];
  const loading = !!titleId && loaded?.key !== key;
  return (
    <select id={id} className={selectCls} value={value} disabled={disabled || loading || !titleId}
      onChange={(e) => onChange(e.target.value, issues.find((i) => i.id === e.target.value) ?? null)}>
      <option value="">{loading ? "Loading the editorial plan…" : issues.length ? emptyLabel : "No upcoming issues in the editorial plan"}</option>
      {issues.map((i) => (
        <option key={i.id} value={i.id}>{issueOptionLabel(i)}{i.suggested ? " (next open)" : ""}</option>
      ))}
    </select>
  );
}
