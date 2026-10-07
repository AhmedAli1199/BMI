"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, CalendarCog, Check, ChevronRight, FileText, Pencil, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { Feature, IssueDetail, IssueFormat, Milestone, PitchList } from "@/lib/editorial-types";
import { FORMAT_LABELS, KIND_LABELS, issueLabel } from "@/lib/editorial-types";
import { addFeature, applyIssueRules, deleteFeature, deleteIssue, editFeature, editIssue, reorderFeatures } from "@/lib/editorial-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtGBP } from "@/components/sales/sales-ui";
import { brandColor } from "@/components/rate-card/brand-style";
import { countdownColor, daysLabel, fmtDay } from "@/components/editorial/editorial-ui";
import { WhoToPitch } from "@/components/editorial/who-to-pitch";

const selectCls = "h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const daysFrom = (iso: string) => Math.round((new Date(iso + "T00:00:00").getTime() - new Date(new Date().toDateString()).getTime()) / 86400000);

/** One issue (or event): its key dates, the features planned for it, its details and how bookings are going. */
export function IssuePage({ issue, pitch }: { issue: IssueDetail; pitch: PitchList | null }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const canEdit = issue.can_edit;
  const isPrint = issue.kind === "issue" || issue.kind === "guide";
  const run = (fn: () => Promise<unknown>, ok?: string) => start(async () => { try { await fn(); if (ok) toast.success(ok); router.refresh(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save that"); } });

  return (
    <>
      <div className="flex flex-col gap-3 border-b border-border/80 pb-5">
        <span className="masthead-rule w-16" style={{ background: brandColor(issue.brand) }} aria-hidden="true" />
        <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1 text-xs font-semibold text-muted-foreground">
          <Link href={`/editorial?year=${issue.year}`} className="hover:text-foreground">Editorial plan</Link><ChevronRight className="size-3.5" aria-hidden="true" />
          <Link href={`/editorial?year=${issue.year}&brand=${issue.brand}`} className="hover:text-foreground">{issue.brand_name}</Link><ChevronRight className="size-3.5" aria-hidden="true" />
          <span className="text-foreground" aria-current="page">{issueLabel(issue)}</span>
        </nav>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h1 className="editorial-title text-2xl font-bold tracking-tight sm:text-3xl">{issue.brand_name}: {issueLabel(issue)}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{[issue.title_name, KIND_LABELS[issue.kind], issue.period_label, issue.format && FORMAT_LABELS[issue.format]].filter(Boolean).join(" · ")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {issue.prev_issue && <Button size="sm" variant="ghost" className="gap-1" nativeButton={false} render={<Link href={`/editorial/issues/${issue.prev_issue.id}`} />}><ArrowLeft className="size-3.5" /> {issue.prev_issue.name}</Button>}
            {issue.next_issue && <Button size="sm" variant="ghost" className="gap-1" nativeButton={false} render={<Link href={`/editorial/issues/${issue.next_issue.id}`} />}>{issue.next_issue.name} <ArrowRight className="size-3.5" /></Button>}
            <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href={`/sales/editions/${issue.id}`} />}><FileText className="size-3.5" /> Bookings in the order register</Button>
            <Button size="sm" className="gap-1.5" nativeButton={false} render={<Link href={`/sales/proposals/new?edition=${issue.id}`} />}>Pitch this issue</Button>
          </div>
        </div>
      </div>

      {issue.needs_check && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
          <AlertTriangle className="size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
          <p className="min-w-0 flex-1"><strong>Please check these dates.</strong> <span className="text-muted-foreground">Some were worked out from the usual rules, estimated from the month, or copied from last year.</span></p>
          {canEdit && <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => run(() => editIssue(issue.id, { needs_check: false }), "Marked as checked")}><Check className="size-3.5" /> The dates are right</Button>}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-5">
          <KeyDates issue={issue} canEdit={canEdit} isPrint={isPrint} />
          <Features issue={issue} canEdit={canEdit} />
          {pitch && <WhoToPitch pitch={pitch} open={isOpen(issue)} />}
          {issue.settings.regular_sections.length > 0 && (
            <details className="rounded-xl border border-border/80 bg-card shadow-2xs">
              <summary className="cursor-pointer px-4 py-3 text-sm font-bold">Regular sections in every issue ({issue.settings.regular_sections.length})</summary>
              <ul className="grid gap-x-6 gap-y-1.5 border-t border-border/70 px-4 py-3 text-sm sm:grid-cols-2">
                {issue.settings.regular_sections.map((s) => <li key={s.name}><strong>{s.name}</strong>{s.description && <span className="text-muted-foreground"> - {s.description}</span>}</li>)}
              </ul>
              <p className="px-4 pb-3 text-xs text-muted-foreground">Change these in <Link href={`/editorial/settings/${issue.brand}`} className="font-semibold text-primary hover:underline">{issue.brand_name}&apos;s settings</Link>.</p>
            </details>
          )}
        </div>

        <aside className="flex flex-col gap-4" aria-label="About this issue">
          <Details issue={issue} canEdit={canEdit} />
          <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs" aria-labelledby="bk-h">
            <h2 id="bk-h" className="flex items-center gap-1 text-sm font-bold">Bookings so far <InfoHint>Live bookings in the order register for this issue, before VAT.</InfoHint></h2>
            <p className="mt-2 text-2xl font-bold tabular-nums">{fmtGBP(issue.booked_gbp)}</p>
            <p className="text-xs text-muted-foreground">{issue.orders} booking{issue.orders === 1 ? "" : "s"}</p>
            {issue.last_year && (
              <p className="mt-2 text-xs text-muted-foreground">Last year&apos;s equivalent (<Link href={`/editorial/issues/${issue.last_year.id}`} className="font-semibold text-primary hover:underline">{issue.last_year.name}</Link>): {fmtGBP(issue.last_year.booked_gbp)} from {issue.last_year.orders} bookings in total.</p>
            )}
          </section>
          <Notes issue={issue} canEdit={canEdit} />
          {canEdit && issue.can_delete && (
            <Button size="sm" variant="ghost" className="gap-1.5 self-start text-destructive hover:text-destructive" disabled={pending}
              onClick={() => { if (window.confirm(`Delete ${issueLabel(issue)} from the plan? Its features go too.`)) start(async () => { try { await deleteIssue(issue.id); router.push(`/editorial?year=${issue.year}&brand=${issue.brand}`); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't delete it"); } }); }}>
              <Trash2 className="size-3.5" /> Delete from the plan
            </Button>
          )}
        </aside>
      </div>
    </>
  );
}

/** Can it still take adverts? (advertising deadline, or failing that the publication date, not passed) */
function isOpen(issue: IssueDetail): boolean {
  const d = issue.ad_deadline ?? issue.edition_date;
  return !d || d >= new Date().toISOString().slice(0, 10);
}

function DateRow({ label, value, hint }: { label: string; value: string | null; hint?: string }) {
  const d = value ? daysFrom(value) : null;
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto_7rem] items-center gap-3 px-4 py-2.5 text-sm">
      <span className="font-medium">{label}{hint && <span className="ml-1.5 text-xs font-normal text-muted-foreground">{hint}</span>}</span>
      <span className="tabular-nums">{value ? fmtDay(value, true) : <span className="text-muted-foreground">Not set</span>}</span>
      <span className="text-right text-xs font-semibold" style={{ color: d !== null && d >= 0 ? countdownColor(d) : undefined }}>{d === null ? "" : d < 0 ? <span className="font-normal text-muted-foreground">Done</span> : daysLabel(d)}</span>
    </li>
  );
}

function KeyDates({ issue, canEdit, isPrint }: { issue: IssueDetail; canEdit: boolean; isPrint: boolean }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [pending, start] = useTransition();
  const [d, setD] = useState({ edition_date: issue.edition_date ?? "", ad_deadline: issue.ad_deadline ?? "", editorial_deadline: issue.editorial_deadline ?? "", copy_deadline: issue.copy_deadline ?? "" });
  const [ms, setMs] = useState<Milestone[]>(issue.milestones);
  const rules = issue.settings.rules_described;
  function save() {
    start(async () => {
      try {
        await editIssue(issue.id, { edition_date: d.edition_date || null, ad_deadline: d.ad_deadline || null, editorial_deadline: d.editorial_deadline || null,
          copy_deadline: d.copy_deadline || null, milestones: ms.filter((m) => m.label.trim() && m.date) });
        toast.success("Dates saved"); setEditing(false); router.refresh();
      } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save the dates"); }
    });
  }
  const allDates = [
    ...(isPrint ? [["ad_deadline", "Advertising deadline", "Last day to book an advert"], ["editorial_deadline", "Editorial deadline", "Copy from the editorial team"], ["copy_deadline", "Copy & artwork deadline", "Advertisers' artwork due"]] : []),
    ["edition_date", isPrint ? "Publication date" : issue.kind === "awards" ? "Ceremony" : "Event day", ""],
  ] as const;

  return (
    <section aria-labelledby="kd-h" className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
      <header className="flex flex-wrap items-center gap-2 border-b border-border/70 px-4 py-3">
        <h2 id="kd-h" className="text-sm font-bold">Key dates</h2>
        {rules.length > 0 && <InfoHint>{`${issue.brand_name}'s usual deadlines: ${rules.join("; ")}.`}</InfoHint>}
        {canEdit && !editing && (
          <span className="ml-auto flex gap-1.5">
            {rules.length > 0 && isPrint && issue.edition_date && (
              <Button size="xs" variant="ghost" className="gap-1" disabled={pending} title="Work the deadlines out again from the publication date and the usual rules"
                onClick={() => start(async () => { try { await applyIssueRules(issue.id); toast.success("Deadlines worked out from the usual rules"); router.refresh(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't work them out"); } })}>
                <CalendarCog className="size-3" /> Use the usual rules
              </Button>
            )}
            <Button size="xs" variant="outline" className="gap-1" onClick={() => setEditing(true)}><Pencil className="size-3" /> Change dates</Button>
          </span>
        )}
      </header>
      {!editing ? (
        <ul className="divide-y divide-border/60">
          {[...allDates.map(([k, label, hint]) => ({ label, hint, value: issue[k as keyof IssueDetail] as string | null })),
            ...issue.milestones.map((m) => ({ label: m.label, hint: "", value: m.date }))]
            .filter((r) => r.value || r.label.startsWith("Publication") || r.label === "Advertising deadline")
            .sort((a, b) => (a.value ?? "9999").localeCompare(b.value ?? "9999"))
            .map((r) => <DateRow key={r.label} label={r.label} value={r.value} hint={r.hint || undefined} />)}
        </ul>
      ) : (
        <div className="flex flex-col gap-3 px-4 py-3">
          <div className="grid gap-3 sm:grid-cols-2">
            {allDates.map(([k, label]) => (
              <label key={k} className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">{label}
                <Input type="date" value={d[k as keyof typeof d]} onChange={(e) => setD({ ...d, [k]: e.target.value })} />
              </label>
            ))}
          </div>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 flex items-center gap-1 text-xs font-semibold text-muted-foreground">Other key dates <InfoHint>Anything else with a date: entries close, voting opens, sponsored content deadline, press day…</InfoHint></legend>
            {ms.map((m, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input aria-label="What" value={m.label} onChange={(e) => setMs(ms.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} placeholder="e.g. Entries close" className="h-8 flex-1 text-sm" />
                <Input aria-label="Date" type="date" value={m.date} onChange={(e) => setMs(ms.map((x, j) => (j === i ? { ...x, date: e.target.value } : x)))} className="h-8 w-40 text-sm" />
                <Button size="icon-xs" variant="ghost" aria-label="Remove this date" onClick={() => setMs(ms.filter((_, j) => j !== i))}><X className="size-3" /></Button>
              </div>
            ))}
            <Button size="xs" variant="ghost" className="self-start gap-1" onClick={() => setMs([...ms, { label: "", date: "" }])}><Plus className="size-3" /> Add a key date</Button>
          </fieldset>
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            <Button size="sm" onClick={save} disabled={pending}>{pending ? "Saving…" : "Save dates"}</Button>
          </div>
        </div>
      )}
    </section>
  );
}

const STATUS_STYLE: Record<Feature["status"], { label: string; color: string }> = {
  planned: { label: "Planned", color: "var(--muted-foreground)" },
  confirmed: { label: "Confirmed", color: "var(--ok)" },
  dropped: { label: "Dropped", color: "var(--bad)" },
};

function Features({ issue, canEdit }: { issue: IssueDetail; canEdit: boolean }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [newTitle, setNewTitle] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const list = issue.feature_list;
  const live = list.filter((f) => f.status !== "dropped");
  const run = (fn: () => Promise<unknown>) => start(async () => { try { await fn(); router.refresh(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save that"); } });

  function add() {
    // Pasting a list ("Seafood; Napkins" or one per line) adds each one.
    const titles = newTitle.split(/\n|;/).map((t) => t.trim()).filter(Boolean);
    if (!titles.length) return;
    start(async () => {
      try { for (const t of titles) await addFeature(issue.id, { title: t }); setNewTitle(""); router.refresh(); }
      catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't add it"); }
    });
  }
  function move(i: number, dir: -1 | 1) {
    const ids = list.map((f) => f.id);
    [ids[i], ids[i + dir]] = [ids[i + dir], ids[i]];
    run(() => reorderFeatures(issue.id, ids));
  }

  return (
    <section aria-labelledby="ft-h" className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
      <header className="flex flex-wrap items-center gap-2 border-b border-border/70 px-4 py-3">
        <h2 id="ft-h" className="text-sm font-bold">Features</h2>
        <InfoHint>What this issue will cover. “Open to sponsors” marks features a client can sponsor or write sponsored content for - proposals mention them.</InfoHint>
        <span className="ml-auto text-xs text-muted-foreground">{live.length} planned · {list.filter((f) => f.status === "confirmed").length} confirmed · {list.filter((f) => f.sponsorable && f.status !== "dropped").length} open to sponsors</span>
      </header>
      {list.length === 0 && <p className="px-4 py-4 text-xs text-muted-foreground">No features yet.{canEdit ? " Add the first one below - or paste a whole list, one per line." : ""}</p>}
      <ul className="divide-y divide-border/60">
        {list.map((f, i) => (
          <li key={f.id} className={`group px-4 py-2 ${f.status === "dropped" ? "opacity-60" : ""}`}>
            <div className="flex items-center gap-2">
              <span className="w-5 shrink-0 text-right text-xs tabular-nums text-muted-foreground">{i + 1}</span>
              <button type="button" disabled={!canEdit} onClick={() => setOpenId(openId === f.id ? null : f.id)} aria-expanded={openId === f.id}
                className={`min-w-0 flex-1 text-left text-sm font-medium ${f.status === "dropped" ? "line-through" : ""} enabled:hover:underline`}>{f.title}</button>
              {f.sponsorable && <span className="shrink-0 rounded-full border border-primary/40 px-2 py-0.5 text-[10.5px] font-semibold text-primary">Open to sponsors</span>}
              <span className="shrink-0 text-[11px] font-semibold" style={{ color: STATUS_STYLE[f.status].color }}>{STATUS_STYLE[f.status].label}</span>
              {canEdit && (
                <span className="flex shrink-0 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                  <Button size="icon-xs" variant="ghost" aria-label={`Move ${f.title} up`} disabled={i === 0 || pending} onClick={() => move(i, -1)}><ArrowUp className="size-3" /></Button>
                  <Button size="icon-xs" variant="ghost" aria-label={`Move ${f.title} down`} disabled={i === list.length - 1 || pending} onClick={() => move(i, 1)}><ArrowDown className="size-3" /></Button>
                </span>
              )}
            </div>
            {f.description && openId !== f.id && <p className="ml-7 text-xs text-muted-foreground">{f.description}</p>}
            {openId === f.id && canEdit && <FeatureEditor feature={f} onDone={() => setOpenId(null)} />}
          </li>
        ))}
      </ul>
      {canEdit && (
        <div className="flex items-start gap-2 border-t border-border/70 px-4 py-3">
          <Textarea aria-label="New feature" rows={1} value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); add(); } }}
            placeholder="Add a feature and press Enter - or paste a list, one per line" className="min-h-8 flex-1 resize-y text-sm" />
          <Button size="sm" className="gap-1" onClick={add} disabled={pending || !newTitle.trim()}><Plus className="size-3.5" /> Add</Button>
        </div>
      )}
    </section>
  );
}

function FeatureEditor({ feature, onDone }: { feature: Feature; onDone: () => void }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [title, setTitle] = useState(feature.title);
  const [desc, setDesc] = useState(feature.description ?? "");
  const [status, setStatus] = useState(feature.status);
  const [spons, setSpons] = useState(feature.sponsorable);
  return (
    <div className="ml-7 mt-2 flex flex-col gap-2 rounded-lg border border-border/70 bg-muted/30 p-3">
      <Input aria-label="Feature title" value={title} onChange={(e) => setTitle(e.target.value)} className="h-8 text-sm" />
      <Textarea aria-label="Description" rows={2} value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="A line or two on what it covers (optional)" className="text-sm" />
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">Status
          <select className={selectCls} value={status} onChange={(e) => setStatus(e.target.value as Feature["status"])}>
            <option value="planned">Planned</option><option value="confirmed">Confirmed</option><option value="dropped">Dropped</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground"><input type="checkbox" checked={spons} onChange={(e) => setSpons(e.target.checked)} className="size-4 accent-[var(--primary)]" /> Open to sponsors</label>
        <span className="ml-auto flex gap-1.5">
          <Button size="sm" variant="ghost" className="gap-1 text-destructive hover:text-destructive" disabled={pending}
            onClick={() => { if (window.confirm("Delete this feature?")) start(async () => { try { await deleteFeature(feature.id); onDone(); router.refresh(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't delete it"); } }); }}><Trash2 className="size-3.5" /> Delete</Button>
          <Button size="sm" variant="outline" onClick={onDone}>Cancel</Button>
          <Button size="sm" disabled={pending || !title.trim()} onClick={() => start(async () => {
            try { await editFeature(feature.id, { title: title.trim(), description: desc.trim() || null, status, sponsorable: spons }); onDone(); router.refresh(); }
            catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save it"); }
          })}>Save</Button>
        </span>
      </div>
    </div>
  );
}

function Details({ issue, canEdit }: { issue: IssueDetail; canEdit: boolean }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [pending, start] = useTransition();
  const [v, setV] = useState({ name: issue.name, theme: issue.theme ?? "", distribution: issue.distribution ?? "", period_label: issue.period_label ?? "", format: issue.format ?? "" });
  const isEvent = issue.kind === "event" || issue.kind === "awards";
  return (
    <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs" aria-labelledby="dt-h">
      <div className="flex items-center gap-2">
        <h2 id="dt-h" className="text-sm font-bold">Details</h2>
        {canEdit && !editing && <Button size="icon-xs" variant="ghost" className="ml-auto" aria-label="Change details" onClick={() => setEditing(true)}><Pencil className="size-3" /></Button>}
      </div>
      {!editing ? (
        <dl className="mt-2 grid gap-2 text-sm">
          <div><dt className="text-xs text-muted-foreground">Theme</dt><dd>{issue.theme ?? "—"}</dd></div>
          <div><dt className="text-xs text-muted-foreground">{isEvent ? "Venue" : "Handed out at"}</dt><dd>{issue.distribution ?? "—"}</dd></div>
          {!isEvent && <div><dt className="text-xs text-muted-foreground">Months it covers</dt><dd>{issue.period_label ?? "—"}</dd></div>}
          {!isEvent && <div><dt className="text-xs text-muted-foreground">Format</dt><dd>{issue.format ? FORMAT_LABELS[issue.format] : "—"}</dd></div>}
        </dl>
      ) : (
        <div className="mt-2 flex flex-col gap-2">
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Name<Input value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} className="h-8 text-sm" /></label>
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Theme<Input value={v.theme} onChange={(e) => setV({ ...v, theme: e.target.value })} className="h-8 text-sm" /></label>
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">{isEvent ? "Venue" : "Handed out at"}<Input value={v.distribution} onChange={(e) => setV({ ...v, distribution: e.target.value })} className="h-8 text-sm" /></label>
          {!isEvent && <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Months it covers<Input value={v.period_label} onChange={(e) => setV({ ...v, period_label: e.target.value })} className="h-8 text-sm" /></label>}
          {!isEvent && (
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Format
              <select className={`${selectCls} w-full`} value={v.format} onChange={(e) => setV({ ...v, format: e.target.value })}>
                <option value="">—</option>{(["print_digital", "print", "digital"] as IssueFormat[]).map((f) => <option key={f} value={f}>{FORMAT_LABELS[f]}</option>)}
              </select>
            </label>
          )}
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            <Button size="sm" disabled={pending || !v.name.trim()} onClick={() => start(async () => {
              try { await editIssue(issue.id, { name: v.name.trim(), theme: v.theme, distribution: v.distribution, period_label: v.period_label, format: v.format || null }); setEditing(false); toast.success("Saved"); router.refresh(); }
              catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save"); }
            })}>Save</Button>
          </div>
        </div>
      )}
    </section>
  );
}

function Notes({ issue, canEdit }: { issue: IssueDetail; canEdit: boolean }) {
  const [text, setText] = useState(issue.notes ?? "");
  const [, start] = useTransition();
  return (
    <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs" aria-labelledby="nt-h">
      <h2 id="nt-h" className="flex items-center gap-1 text-sm font-bold">Notes <InfoHint>The same notes as on this edition in the order register. Saved when you click away.</InfoHint></h2>
      <Textarea rows={4} value={text} disabled={!canEdit} onChange={(e) => setText(e.target.value)} placeholder="Anything the team should know about this issue"
        onBlur={() => { if (text !== (issue.notes ?? "")) start(async () => { try { await editIssue(issue.id, { notes: text.trim() || null }); toast.success("Notes saved"); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save the notes"); } }); }}
        className="mt-2 text-sm" />
    </section>
  );
}
