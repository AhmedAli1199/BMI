"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { DeadlineRule, EditorialSettings, RegularSection } from "@/lib/editorial-types";
import { saveEditorialSettings } from "@/lib/editorial-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { InfoHint } from "@/components/sales/info-hint";
import { brandColor } from "@/components/rate-card/brand-style";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-9 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const STD = [
  { key: "advertising", label: "Advertising deadline" },
  { key: "editorial", label: "Editorial deadline" },
  { key: "copy", label: "Copy & artwork deadline" },
];

function example(r: DeadlineRule): string {
  const pub = new Date(2026, 5, 11); // 11 June
  let d: Date;
  if (r.kind === "days_before") d = new Date(pub.getTime() - r.value * 86400000);
  else d = new Date(2026, 4, Math.min(r.value, 31));
  return `e.g. for an issue out on Thu 11 June: ${d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "long" })}`;
}

/** A brand's usual deadlines (so new issues fill their dates in themselves) and its regular sections. */
const FACTS: [string, string, string][] = [
  ["print_run", "Print run", "e.g. 12,808"],
  ["email_database", "Email database size", "e.g. 26,000"],
  ["readership", "Who reads it", "e.g. travel professionals throughout the UK"],
  ["website", "Website", "e.g. sellingtravel.co.uk"],
  ["media_pack", "Media pack link", "https://…"],
  ["video", "Video link", "https://…"],
  ["latest_issue", "Latest issue link", "https://issuu.com/…"],
];

export function BrandSettingsForm({ settings, brandName, canEdit }: { settings: EditorialSettings; brandName: string; canEdit: boolean }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [rules, setRules] = useState<DeadlineRule[]>(settings.deadline_rules);
  const [sections, setSections] = useState<RegularSection[]>(settings.regular_sections);
  const [about, setAbout] = useState(settings.about ?? "");
  const [facts, setFacts] = useState<Record<string, string>>(settings.facts ?? {});
  const usedStd = new Set(rules.map((r) => r.key));

  function addRule(key: string, label: string) {
    setRules([...rules, { key, label, kind: key === "copy" ? "day_prev_month" : "days_before", value: key === "copy" ? 25 : 14 }]);
  }
  function save() {
    start(async () => {
      try {
        await saveEditorialSettings(settings.brand, { deadline_rules: rules.filter((r) => r.label.trim()), regular_sections: sections.filter((s) => s.name.trim()), about: about.trim() || null, facts });
        toast.success("Saved"); router.refresh();
      } catch (e) { toast.error(friendlyError(e, "Couldn't save")); }
    });
  }

  return (
    <>
      <div className="flex flex-col gap-3 border-b border-border/80 pb-5">
        <span className="masthead-rule w-16" style={{ background: brandColor(settings.brand) }} aria-hidden="true" />
        <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
          <Link href={`/editorial?brand=${settings.brand}`} className="hover:text-foreground">Editorial plan</Link><ChevronRight className="size-3.5" aria-hidden="true" />
          <span className="text-foreground" aria-current="page">{brandName} settings</span>
        </nav>
        <h1 className="editorial-title text-2xl font-bold tracking-tight sm:text-3xl">{brandName}: deadlines and regular sections</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">Tell the Brain how this brand&apos;s deadlines usually work. When you add an issue with a publication date, its deadlines are filled in for you - you can always change them on the issue.</p>
      </div>

      <section aria-labelledby="ru-h" className="rounded-xl border border-border/80 bg-card shadow-2xs">
        <header className="flex items-center gap-2 border-b border-border/70 px-4 py-3">
          <h2 id="ru-h" className="text-sm font-bold">Usual deadlines</h2>
          <InfoHint>Two ways to set a deadline: a number of days before publication (“9 days before”), or a day of the month before (“the 25th of the month before”).</InfoHint>
        </header>
        <ul className="divide-y divide-border/60">
          {rules.length === 0 && <li className="px-4 py-4 text-xs text-muted-foreground">No usual deadlines yet. Add the ones this brand uses.</li>}
          {rules.map((r, i) => (
            <li key={i} className="flex flex-col gap-1.5 px-4 py-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Input aria-label="Deadline name" value={r.label} disabled={!canEdit || STD.some((s) => s.key === r.key)} onChange={(e) => setRules(rules.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} className="h-9 w-56 font-semibold" />
                <span>is</span>
                {r.kind === "days_before" ? (
                  <><Input aria-label="Number of days" type="number" min={0} max={365} disabled={!canEdit} value={r.value} onChange={(e) => setRules(rules.map((x, j) => (j === i ? { ...x, value: Number(e.target.value) } : x)))} className="h-9 w-20 tabular-nums" /><span>days before publication</span></>
                ) : (
                  <><span>the</span><Input aria-label="Day of the month" type="number" min={1} max={31} disabled={!canEdit} value={r.value} onChange={(e) => setRules(rules.map((x, j) => (j === i ? { ...x, value: Number(e.target.value) } : x)))} className="h-9 w-20 tabular-nums" /><span>of the month before</span></>
                )}
                {canEdit && (
                  <>
                    <select aria-label="How it's worked out" className={selectCls} value={r.kind} onChange={(e) => setRules(rules.map((x, j) => (j === i ? { ...x, kind: e.target.value as DeadlineRule["kind"] } : x)))}>
                      <option value="days_before">Days before</option><option value="day_prev_month">Day of the month before</option>
                    </select>
                    <Button size="icon-sm" variant="ghost" aria-label={`Remove ${r.label}`} onClick={() => setRules(rules.filter((_, j) => j !== i))}><Trash2 className="size-3.5" /></Button>
                  </>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{example(r)}</p>
            </li>
          ))}
        </ul>
        {canEdit && (
          <div className="flex flex-wrap gap-1.5 border-t border-border/70 px-4 py-3">
            {STD.filter((s) => !usedStd.has(s.key)).map((s) => <Button key={s.key} size="xs" variant="outline" className="gap-1" onClick={() => addRule(s.key, s.label)}><Plus className="size-3" /> {s.label}</Button>)}
            <Button size="xs" variant="outline" className="gap-1" onClick={() => addRule(`custom-${Date.now()}`, "")}><Plus className="size-3" /> Another deadline</Button>
          </div>
        )}
      </section>

      <section aria-labelledby="rs-h" className="rounded-xl border border-border/80 bg-card shadow-2xs">
        <header className="flex items-center gap-2 border-b border-border/70 px-4 py-3">
          <h2 id="rs-h" className="text-sm font-bold">Regular sections</h2>
          <InfoHint>The sections every issue has - shown on each issue&apos;s page so the team and proposals can mention them.</InfoHint>
        </header>
        <ul className="divide-y divide-border/60">
          {sections.map((s, i) => (
            <li key={i} className="flex items-center gap-2 px-4 py-2">
              <Input aria-label="Section name" value={s.name} disabled={!canEdit} onChange={(e) => setSections(sections.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} className="h-8 w-48 text-sm font-semibold" />
              <Input aria-label="What it is" value={s.description ?? ""} disabled={!canEdit} onChange={(e) => setSections(sections.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))} placeholder="What it is (optional)" className="h-8 flex-1 text-sm" />
              {canEdit && <Button size="icon-xs" variant="ghost" aria-label={`Remove ${s.name}`} onClick={() => setSections(sections.filter((_, j) => j !== i))}><Trash2 className="size-3" /></Button>}
            </li>
          ))}
        </ul>
        {canEdit && <div className="border-t border-border/70 px-4 py-3"><Button size="xs" variant="outline" className="gap-1" onClick={() => setSections([...sections, { name: "", description: null }])}><Plus className="size-3" /> Add a section</Button></div>}
      </section>

      <section aria-labelledby="ab-h" className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
        <h2 id="ab-h" className="text-sm font-bold">About the publishing schedule</h2>
        <Textarea rows={3} disabled={!canEdit} value={about} onChange={(e) => setAbout(e.target.value)} placeholder="e.g. Quarterly magazine, published to coincide with the industry's key trade shows." className="mt-2 text-sm" />
      </section>

      <section aria-labelledby="fa-h" className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
        <h2 id="fa-h" className="flex items-center gap-1 text-sm font-bold">Figures and links used in emails <InfoHint>Every email template quotes these through merge fields like {"{{print_run}}"}, so change a figure here once and every email that mentions it is up to date.</InfoHint></h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {FACTS.map(([key, label, placeholder]) => (
            <label key={key} className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
              <span>{label} <code className="font-normal">{`{{${key}}}`}</code></span>
              <Input disabled={!canEdit} value={facts[key] ?? ""} onChange={(e) => setFacts({ ...facts, [key]: e.target.value })} placeholder={placeholder} className="h-8 text-sm" />
            </label>
          ))}
        </div>
      </section>

      {canEdit ? (
        <div className="flex justify-end gap-2"><Button variant="outline" nativeButton={false} render={<Link href={`/editorial?brand=${settings.brand}`} />}>Back to the plan</Button><Button onClick={save} disabled={pending}>{pending ? "Saving…" : "Save"}</Button></div>
      ) : <p className="text-xs text-muted-foreground">View only - ask an admin, a data manager or this brand&apos;s publisher to change these.</p>}
    </>
  );
}
