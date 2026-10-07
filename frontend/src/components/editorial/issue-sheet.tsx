"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import type { IssueFormat, IssueKind, PlannerBrand } from "@/lib/editorial-types";
import { FORMAT_LABELS, KIND_LABELS } from "@/lib/editorial-types";
import { addIssue } from "@/lib/editorial-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";

const selectCls = "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

function F({ label, hint, htmlFor, children }: { label: string; hint?: React.ReactNode; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1"><Label htmlFor={htmlFor} className="text-xs font-semibold text-muted-foreground">{label}</Label>{hint && <InfoHint>{hint}</InfoHint>}</div>
      {children}
    </div>
  );
}

/** "Add an issue or event": the few things needed to put it on the planner. Deadlines are worked out from the
 * brand's rules (set in its settings) and can be changed on the issue's page. */
export function AddIssueButton({ brands, year }: { brands: PlannerBrand[]; year: number }) {
  const router = useRouter();
  const editable = brands.filter((b) => b.can_edit);
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [brand, setBrand] = useState(editable[0]?.key ?? "");
  const b = editable.find((x) => x.key === brand);
  const [titleId, setTitleId] = useState(b?.titles[0]?.id ?? "");
  const [kind, setKind] = useState<IssueKind>("issue");
  const [format, setFormat] = useState<IssueFormat>("print_digital");
  const [name, setName] = useState("");
  const [pub, setPub] = useState("");
  const [period, setPeriod] = useState("");
  const [theme, setTheme] = useState("");
  const [distribution, setDistribution] = useState("");
  if (!editable.length) return null;

  function save() {
    if (!name.trim()) return toast.error("Give it a name, e.g. 109 or Spring issue.");
    start(async () => {
      try {
        const r = await addIssue({ brand, title_id: titleId, year: pub ? Number(pub.slice(0, 4)) : year, name: name.trim(), kind, format,
          edition_date: pub || null, period_label: period || null, theme: theme || null, distribution: distribution || null, use_rules: true });
        toast.success(`Added ${r.name}`);
        setOpen(false);
        router.push(`/editorial/issues/${r.id}`);
      } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't add it"); }
    });
  }

  return (
    <>
      <Button size="sm" className="gap-1.5" onClick={() => setOpen(true)}><Plus className="size-3.5" /> Add an issue or event</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-lg">
          <SheetHeader className="border-b border-border/70 px-5 py-4">
            <SheetTitle className="text-base font-bold">Add an issue or event</SheetTitle>
            <SheetDescription className="text-xs">Deadlines are filled in from the brand&apos;s usual rules. You can change them, and add features, on the next page.</SheetDescription>
          </SheetHeader>
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-5 py-4">
            <div className="grid grid-cols-2 gap-3">
              <F label="Brand" htmlFor="ai-brand">
                <select id="ai-brand" className={selectCls} value={brand} onChange={(e) => { setBrand(e.target.value); setTitleId(editable.find((x) => x.key === e.target.value)?.titles[0]?.id ?? ""); }}>
                  {editable.map((x) => <option key={x.key} value={x.key}>{x.name}</option>)}
                </select>
              </F>
              <F label="Part of the brand" htmlFor="ai-title" hint="Which part of the order register its bookings go into - e.g. the magazine, the events, the awards.">
                <select id="ai-title" className={selectCls} value={titleId} onChange={(e) => setTitleId(e.target.value)}>
                  {b?.titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </F>
            </div>
            <fieldset>
              <legend className="mb-1.5 text-xs font-semibold text-muted-foreground">What is it?</legend>
              <div className="flex flex-wrap gap-1.5">
                {(Object.keys(KIND_LABELS) as IssueKind[]).map((k) => (
                  <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => { setKind(k); setFormat(k === "event" ? "event" : k === "awards" ? "awards" : "print_digital"); }}
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${kind === k ? "border-primary bg-primary/10" : "border-border text-muted-foreground hover:text-foreground"}`}>{KIND_LABELS[k]}</button>
                ))}
              </div>
            </fieldset>
            <F label="Name" htmlFor="ai-name">
              <Input id="ai-name" value={name} onChange={(e) => setName(e.target.value)} placeholder={kind === "issue" ? "e.g. 109, or Spring issue" : kind === "event" ? "e.g. Dinner Club - March" : "e.g. People Awards 2027"} autoFocus />
            </F>
            <div className="grid grid-cols-2 gap-3">
              <F label={kind === "issue" || kind === "guide" ? "Publication date" : "Date"} htmlFor="ai-date">
                <Input id="ai-date" type="date" value={pub} onChange={(e) => setPub(e.target.value)} />
              </F>
              {(kind === "issue" || kind === "guide") && (
                <F label="Format" htmlFor="ai-format">
                  <select id="ai-format" className={selectCls} value={format} onChange={(e) => setFormat(e.target.value as IssueFormat)}>
                    {(["print_digital", "print", "digital"] as IssueFormat[]).map((f) => <option key={f} value={f}>{FORMAT_LABELS[f]}</option>)}
                  </select>
                </F>
              )}
            </div>
            {(kind === "issue" || kind === "guide") && (
              <F label="Months it covers (optional)" htmlFor="ai-period"><Input id="ai-period" value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="e.g. March, April, May" /></F>
            )}
            <F label="Theme (optional)" htmlFor="ai-theme"><Input id="ai-theme" value={theme} onChange={(e) => setTheme(e.target.value)} placeholder="e.g. WTCE preview" /></F>
            <F label={kind === "event" || kind === "awards" ? "Venue (optional)" : "Shows it's handed out at (optional)"} htmlFor="ai-dist">
              <Input id="ai-dist" value={distribution} onChange={(e) => setDistribution(e.target.value)} placeholder={kind === "event" || kind === "awards" ? "e.g. The Dorchester, London" : "e.g. WTCE, Hamburg"} />
            </F>
          </div>
          <SheetFooter className="flex-row justify-end gap-2 border-t border-border/70 px-5 py-3">
            <Button variant="outline" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
            <Button size="sm" onClick={save} disabled={pending || !name.trim() || !titleId}>{pending ? "Adding…" : "Add and open it"}</Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
}
