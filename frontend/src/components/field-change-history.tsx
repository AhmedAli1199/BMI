"use client";

import { useState, useTransition } from "react";
import { ChevronDown, ChevronRight, History } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { FieldChange } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  first_name: "First name",
  last_name: "Last name",
  full_name: "Full name",
  job_title: "Title",
  department: "Department",
  category: "Category",
  referred_by: "Referred by",
  birthdate: "Birthdate",
  company_id: "Company",
  name: "Name",
  industry: "Industry",
  website: "Website",
  territory: "Territory",
  region: "Region",
  division: "Division",
  num_employees: "Employee count",
  revenue: "Revenue",
};

function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field.replace(/_/g, " ");
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.round(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

/** Collapsed by default (most people never need it) and fetched only when
 * opened - "the ability to identify which BMI user has made changes to
 * specific data" (BMI's own Act pain-points doc), without loading it on
 * every single page view. */
export function FieldChangeHistory({
  entityId,
  fetchChanges,
}: {
  entityId: string;
  fetchChanges: (id: string) => Promise<FieldChange[]>;
}) {
  const [open, setOpen] = useState(false);
  const [changes, setChanges] = useState<FieldChange[] | null>(null);
  const [pending, startTransition] = useTransition();

  function toggle() {
    const next = !open;
    setOpen(next);
    // Always refetch on open, rather than caching after the first load -
    // this panel sits right next to the record's own editable fields, so
    // "opened it once, edited a field, opened it again" is a completely
    // normal sequence within one page view. A stale cached [] (or a
    // stale older list) after that edit would show as silently broken.
    if (next) {
      startTransition(async () => {
        setChanges(await fetchChanges(entityId));
      });
    }
  }

  return (
    <Card className="editorial-card">
      <button
        type="button"
        onClick={toggle}
        className="flex w-full items-center justify-between gap-2 p-4 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-bold text-foreground">
          <History className="size-4 text-muted-foreground" />
          History of changes
        </span>
        {open ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
      </button>
      {open && (
        <CardContent className="flex flex-col gap-2 border-t border-border pt-3">
          {pending && <p className="text-xs text-muted-foreground">Loading…</p>}
          {!pending && changes && changes.length === 0 && (
            <p className="text-xs text-muted-foreground">No field edits recorded yet.</p>
          )}
          {!pending && changes && changes.length > 0 && (
            <ul className="flex flex-col gap-2.5">
              {changes.map((c) => (
                <li key={c.id} className="text-xs">
                  <span className="font-semibold text-foreground">{fieldLabel(c.field)}</span>{" "}
                  <span className="text-muted-foreground">changed</span>{" "}
                  {c.old_value ? (
                    <>
                      <span className="text-muted-foreground line-through">{c.old_value}</span>{" "}
                      <span className="text-muted-foreground">→</span>{" "}
                    </>
                  ) : null}
                  <span className="font-medium text-foreground">{c.new_value || "(cleared)"}</span>
                  <div className="mt-0.5 text-muted-foreground">
                    {c.changed_by ? c.changed_by.name : "Unknown user"} · {timeAgo(c.changed_at)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      )}
    </Card>
  );
}
