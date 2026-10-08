"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowDown, ArrowUp, BadgePercent, CalendarDays, CheckCircle2, Download, ExternalLink, Eye, Loader2, Mail, Pencil, Plus, Save, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { TEMPLATE_OPTIONS, type Proposal, type ProposalEmailDraft, type ProposalSection } from "@/lib/proposals-types";
import { deleteProposal, finishProposal, getProposalEmailDraft, redraftProposal, saveProposal, sendProposal } from "@/lib/proposals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { downloadFile } from "@/lib/download";
import { InfoHint } from "@/components/sales/info-hint";
import { SectionTitle, fmtDate, fmtGBP } from "@/components/sales/sales-ui";
import { ProposalIssuePicker } from "@/components/sales/proposal-issue-picker";
import { ProposalAiRevise } from "@/components/sales/proposal-ai-revise";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

type Line = Proposal["lines"][number];

/** Offer lines are worked out by the server from the rate card's offers, so they're never sent back. */
const toSave = (lines: Line[]) => lines.filter((l) => l.source !== "offer").map((l) => ({ ...l, unit_price: l.source === "manual" ? l.unit_price : null }));

/** Renders **bold** and "- " bullets the way the Word file will. */
function Rich({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).filter((b) => b.trim());
  const inline = (s: string) => s.split(/(\*\*.+?\*\*)/g).map((part, i) => (part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part));
  return (
    <>
      {blocks.map((b, i) => {
        const lines = b.split("\n");
        return lines.every((l) => l.startsWith("- ")) ? (
          <ul key={i} className="my-2 list-disc pl-5">{lines.map((l, j) => <li key={j}>{inline(l.slice(2))}</li>)}</ul>
        ) : (
          <p key={i} className="my-2 whitespace-pre-line">{inline(b)}</p>
        );
      })}
    </>
  );
}

export function ProposalEditor({ proposal }: { proposal: Proposal }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [campaign, setCampaign] = useState(proposal.campaign_name);
  const [template, setTemplate] = useState<string>(proposal.template);
  const [sections, setSections] = useState<ProposalSection[]>(proposal.sections);
  const [lines, setLines] = useState<Line[]>(proposal.lines);
  const [linesTouched, setLinesTouched] = useState(false);
  const [issueChanged, setIssueChanged] = useState(false);
  const [preview, setPreview] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const [via, setVia] = useState<"downloaded" | "other">("downloaded");
  const [days, setDays] = useState(14);
  const [mailOpen, setMailOpen] = useState(false);
  const [mail, setMail] = useState<ProposalEmailDraft | null>(null);
  const [mailTo, setMailTo] = useState("");
  const [mailCc, setMailCc] = useState("");
  const sent = proposal.status === "sent";
  const total = lines.reduce((s, l) => s + l.qty * l.unit_price, 0);
  const h = proposal.context.history;

  const touch = <T,>(fn: (v: T) => void) => (v: T) => { fn(v); setDirty(true); };

  function save(after?: () => void) {
    start(async () => {
      try {
        const p = await saveProposal(proposal.id, { campaign_name: campaign, template, sections, lines: toSave(lines) });
        setLines(p.lines);
        setLinesTouched(false);
        setDirty(false);
        toast.success("Saved");
        router.refresh();
        after?.();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save"));
      }
    });
  }

  const saved = () => ({ campaign_name: campaign, template, sections, lines: toSave(lines) });
  const editLines = (next: Line[]) => { editLines(next); setLinesTouched(true); };

  function changeIssue(id: string) {
    start(async () => {
      try {
        await saveProposal(proposal.id, { edition_id: id || null });
        setIssueChanged(true);
        toast.success(id ? "Issue changed - redraft the wording to use its details" : "Issue removed");
        router.refresh();
      } catch (e) { toast.error(friendlyError(e, "Couldn't change the issue")); }
    });
  }
  const split = (v: string) => v.split(/[,;\s]+/).filter(Boolean);

  function openMail() {
    start(async () => {
      try {
        if (dirty) { await saveProposal(proposal.id, saved()); setDirty(false); }
        const d = await getProposalEmailDraft(proposal.id);
        setMail(d);
        setMailTo(d.to.join(", "));
        setMailCc("");
        setMailOpen(true);
      } catch (e) { toast.error(friendlyError(e, "Couldn't prepare the email")); }
    });
  }

  function move(i: number, d: -1 | 1) {
    const next = [...sections];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    touch(setSections)(next);
  }

  function download() {
    const go = () => downloadFile(`/api/proposals/${proposal.id}/download`, "proposal.docx").catch((e) => toast.error(friendlyError(e, "Couldn't download")));
    if (dirty) save(go);
    else go();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="flex min-w-0 flex-col gap-5">
        {sent && (
          <div className="flex items-start gap-2 rounded-xl border border-primary/30 bg-primary/5 p-3 text-sm">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            <span>
              Logged as sent{proposal.sent_via === "outlook" ? " from Outlook" : ""} on {fmtDate(proposal.sent_at?.slice(0, 10))} and noted on <Link href={`/companies/${proposal.company_id}`} className="font-semibold underline">{proposal.company_name}</Link>.
              {proposal.follow_up_due && <> Follow-up reminder: {fmtDate(proposal.follow_up_due.slice(0, 10))}.</>}
            </span>
          </div>
        )}
        {proposal.flags.length > 0 && !sent && (
          <ul className="flex flex-col gap-1.5 rounded-xl border border-[color-mix(in_oklab,var(--warn)_40%,transparent)] bg-[color-mix(in_oklab,var(--warn)_8%,transparent)] p-3 text-xs">
            {proposal.flags.map((f) => (
              <li key={f} className="flex items-start gap-2"><AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-[var(--warn)]" aria-hidden="true" />{f}</li>
            ))}
          </ul>
        )}

        <section className="grid gap-3 rounded-xl border border-border/80 bg-card p-4 shadow-2xs sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
            Campaign name (Word header)
            <Input value={campaign} disabled={sent} onChange={(e) => touch(setCampaign)(e.target.value)} className="h-8 text-sm" />
          </label>
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
            Word template
            <select className={selectCls} value={template} disabled={sent} onChange={(e) => touch(setTemplate)(e.target.value)}>
              {TEMPLATE_OPTIONS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </label>
        </section>

        <section aria-labelledby="lines-h">
          <SectionTitle id="lines-h" hint="Prices from the rate card are fixed. Your own lines can have any price. Everything is before VAT.">Products and prices</SectionTitle>
          <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
            <table className="w-full text-sm">
              <caption className="sr-only">Products in this proposal</caption>
              <thead><tr className="text-left text-xs text-muted-foreground">
                <th scope="col" className="px-4 py-2 font-semibold">Product</th>
                <th scope="col" className="w-20 px-2 py-2 text-right font-semibold">Qty</th>
                <th scope="col" className="w-28 px-2 py-2 text-right font-semibold">Each</th>
                <th scope="col" className="w-28 px-2 py-2 text-right font-semibold">Subtotal</th>
                <th scope="col" className="w-10 px-2 py-2"><span className="sr-only">Remove</span></th>
              </tr></thead>
              <tbody>
                {lines.map((l, i) => l.source === "offer" ? (
                  <tr key={l.id ?? i} className={`border-t border-border/60 ${linesTouched ? "opacity-50" : ""}`}>
                    <td className="px-4 py-1.5" colSpan={3}>
                      <span className="inline-flex items-center gap-1.5 font-medium text-[var(--ok)]"><BadgePercent className="size-3.5" aria-hidden="true" />{l.product.replace(/^Offer: /, "")}</span>
                      <span className="block text-[11px] text-muted-foreground">Rate card offer - added for you, and worked out again whenever the products change</span>
                    </td>
                    <td className="px-2 py-1.5 text-right font-semibold tabular-nums text-[var(--ok)]">{fmtGBP(l.qty * l.unit_price)}</td>
                    <td />
                  </tr>
                ) : (
                  <tr key={l.id ?? i} className="border-t border-border/60">
                    <td className="px-4 py-1.5">
                      {l.source === "rate_card" || sent ? <span className="font-medium">{l.product}</span> : (
                        <Input aria-label="Product" value={l.product} onChange={(e) => editLines(lines.map((x, j) => (j === i ? { ...x, product: e.target.value } : x)))} className="h-8 text-sm" />
                      )}
                      {l.source === "rate_card" && <span className="ml-2 text-[11px] text-muted-foreground">rate card</span>}
                    </td>
                    <td className="px-2 py-1.5 text-right">
                      {sent ? l.qty : <Input aria-label="Quantity" type="number" min={1} value={l.qty} onChange={(e) => editLines(lines.map((x, j) => (j === i ? { ...x, qty: Math.max(1, Number(e.target.value) || 1) } : x)))} className="h-8 text-right text-sm tabular-nums" />}
                    </td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      {l.source === "rate_card" || sent ? fmtGBP(l.unit_price) : (
                        <Input aria-label="Price each" type="number" min={0} value={l.unit_price} onChange={(e) => editLines(lines.map((x, j) => (j === i ? { ...x, unit_price: Number(e.target.value) || 0 } : x)))} className="h-8 text-right text-sm tabular-nums" />
                      )}
                    </td>
                    <td className="px-2 py-1.5 text-right font-semibold tabular-nums">{fmtGBP(l.qty * l.unit_price)}</td>
                    <td className="px-2 py-1.5">
                      {!sent && <Button size="icon-sm" variant="ghost" aria-label={`Remove ${l.product}`} onClick={() => editLines(lines.filter((_, j) => j !== i))}><Trash2 className="size-3.5" /></Button>}
                    </td>
                  </tr>
                ))}
                {lines.length === 0 && <tr className="border-t border-border/60"><td colSpan={5} className="px-4 py-4 text-xs text-muted-foreground">No products yet.</td></tr>}
              </tbody>
              <tfoot><tr className="border-t border-border/70 bg-muted/30">
                <td colSpan={3} className="px-4 py-2 text-xs text-muted-foreground">
                  {!sent && <Button size="sm" variant="ghost" className="-ml-2 gap-1.5" onClick={() => editLines([...lines, { id: crypto.randomUUID(), product: "", qty: 1, unit_price: 0, source: "manual" }])}><Plus className="size-3.5" /> Add my own line</Button>}
                </td>
                <td className="px-2 py-2 text-right font-bold tabular-nums">{fmtGBP(total)}</td>
                <td />
              </tr></tfoot>
            </table>
          </div>
          {dirty && <p className="mt-1.5 text-xs text-muted-foreground">Save to update the Investment section&apos;s figures in the Word file{linesTouched ? " - any rate card offers are worked out again when you save" : ""}.</p>}
        </section>

        <section aria-labelledby="secs-h">
          <SectionTitle id="secs-h" hint="These headings and paragraphs go into the Word file in this order. Use **double asterisks** for bold, and start a line with “- ” for a bullet. The Investment section's prices are added from the table above automatically." aside={
            <div className="flex items-center gap-1.5">
              <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setPreview(!preview)}>{preview ? <><Pencil className="size-3.5" /> Edit</> : <><Eye className="size-3.5" /> Preview</>}</Button>
              {!sent && (
                <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => {
                  if (!window.confirm("Write every section again from scratch? Your edits to the wording will be replaced.")) return;
                  start(async () => { try { if (dirty) await saveProposal(proposal.id, saved()); const p = await redraftProposal(proposal.id); setSections(p.sections); setLines(p.lines); setLinesTouched(false); setIssueChanged(false); setDirty(false); toast.success("Wording redrafted"); router.refresh(); } catch (e) { toast.error(friendlyError(e, "Couldn't redraft")); } });
                }}><Sparkles className="size-3.5" /> Start again</Button>
              )}
            </div>
          }>Wording</SectionTitle>

          {!sent && !preview && (
            <div className="mb-3">
              <ProposalAiRevise proposalId={proposal.id} sections={sections}
                onBeforeApply={async () => { if (dirty) { await saveProposal(proposal.id, saved()); setDirty(false); } }}
                onApplied={(next) => { setSections(next); setIssueChanged(false); router.refresh(); }} />
            </div>
          )}
          {preview ? (
            <article className="rounded-xl border border-border/80 bg-card p-6 text-sm shadow-2xs" aria-label="Proposal preview">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{campaign}</p>
              {sections.map((s) => (
                <div key={s.id} className="mt-4">
                  <h3 className="text-base font-bold">{s.heading}</h3>
                  {s.kind === "investment" && (
                    <ul className="my-2">
                      {lines.map((l, i) => <li key={i}>{l.product}: {l.qty > 1 ? `${l.qty} × ${fmtGBP(l.unit_price)} = ` : ""}{fmtGBP(l.qty * l.unit_price)}</li>)}
                      <li className="mt-1 font-bold">Total: {fmtGBP(total)}</li>
                    </ul>
                  )}
                  <Rich text={s.body} />
                </div>
              ))}
            </article>
          ) : (
            <div className="flex flex-col gap-3">
              {sections.map((s, i) => (
                <div key={s.id} className="rounded-xl border border-border/80 bg-card p-3 shadow-2xs">
                  <div className="flex items-center gap-1.5">
                    <Input aria-label="Section heading" value={s.heading} disabled={sent} onChange={(e) => touch(setSections)(sections.map((x) => (x.id === s.id ? { ...x, heading: e.target.value } : x)))} className="h-8 text-sm font-semibold" />
                    {!sent && <>
                      <Button size="icon-sm" variant="ghost" aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp className="size-3.5" /></Button>
                      <Button size="icon-sm" variant="ghost" aria-label="Move down" disabled={i === sections.length - 1} onClick={() => move(i, 1)}><ArrowDown className="size-3.5" /></Button>
                      <Button size="icon-sm" variant="ghost" aria-label={`Remove ${s.heading}`} onClick={() => touch(setSections)(sections.filter((x) => x.id !== s.id))}><Trash2 className="size-3.5" /></Button>
                    </>}
                  </div>
                  <Textarea aria-label={`${s.heading} text`} value={s.body} disabled={sent} rows={s.kind === "investment" ? 2 : 4} onChange={(e) => touch(setSections)(sections.map((x) => (x.id === s.id ? { ...x, body: e.target.value } : x)))} className="mt-2 text-sm" />
                </div>
              ))}
              {!sent && <Button size="sm" variant="ghost" className="gap-1.5 self-start" onClick={() => touch(setSections)([...sections, { id: crypto.randomUUID(), kind: "custom", heading: "New section", body: "" }])}><Plus className="size-3.5" /> Add a section</Button>}
            </div>
          )}
        </section>

        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border/80 pt-4">
          {!sent && (
            <Button variant="ghost" size="sm" className="mr-auto gap-1.5 text-muted-foreground" disabled={pending} onClick={() => {
              if (!window.confirm("Delete this draft?")) return;
              start(async () => { await deleteProposal(proposal.id); router.push("/sales/proposals"); });
            }}><Trash2 className="size-3.5" /> Delete draft</Button>
          )}
          {!sent && <Button variant="outline" disabled={pending || !dirty} onClick={() => save()} className="gap-1.5">{pending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />} Save</Button>}
          <Button variant={sent ? "default" : "outline"} onClick={download} disabled={pending} className="gap-1.5"><Download className="size-4" /> Download Word file</Button>
          {!sent && <Button variant="outline" onClick={openMail} disabled={pending} className="gap-1.5"><Mail className="size-4" /> Email it from Outlook</Button>}
          {!sent && <Button onClick={() => setSendOpen(true)} disabled={pending} className="gap-1.5"><CheckCircle2 className="size-4" /> I&apos;ve sent it myself</Button>}
        </div>
      </div>

      <aside className="flex flex-col gap-4" aria-label="About this client">
        <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
          <h2 className="mb-2 flex items-center gap-1.5 text-sm font-bold"><CalendarDays className="size-4 text-muted-foreground" aria-hidden="true" />The issue <InfoHint>From the editorial plan. Its date, advertising deadline and features are what the wording mentions.</InfoHint></h2>
          {proposal.issue ? (
            <div className="flex flex-col gap-1 text-xs">
              <Link href={`/editorial/issues/${proposal.issue.id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
                {proposal.issue.label.startsWith("Issue ") ? `${proposal.title_name} ${proposal.issue.label}` : proposal.issue.label} <ExternalLink className="size-3" aria-hidden="true" />
              </Link>
              {proposal.issue.publication_text && <span className="text-muted-foreground">{proposal.issue.kind === "issue" || proposal.issue.kind === "guide" ? "Out" : "On"} {proposal.issue.publication_text}</span>}
              {proposal.issue.ad_deadline_text && <span className="text-muted-foreground">Advertising deadline {proposal.issue.ad_deadline_text}</span>}
              {proposal.issue.theme && <span className="text-muted-foreground">Theme: {proposal.issue.theme}</span>}
              {proposal.issue.features.length > 0 && (
                <ul className="mt-1 list-disc pl-4 text-muted-foreground">
                  {proposal.issue.features.slice(0, 6).map((f) => <li key={f}>{f}{proposal.issue?.sponsorable.includes(f) ? " · can be sponsored" : ""}</li>)}
                </ul>
              )}
            </div>
          ) : <p className="text-xs text-muted-foreground">No issue chosen, so the wording doesn&apos;t mention one.</p>}
          {!sent && proposal.title_id && (
            <label className="mt-3 flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
              Change the issue
              <ProposalIssuePicker titleId={proposal.title_id} value={proposal.edition_id ?? ""} include={proposal.edition_id} disabled={pending}
                onChange={(id) => changeIssue(id)} emptyLabel="No particular issue" />
            </label>
          )}
          {issueChanged && !sent && <p className="mt-2 text-xs text-muted-foreground">Press <strong>Start again</strong>, or ask the AI below, to bring the new issue&apos;s details into the text.</p>}
        </section>
        <section className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
          <h2 className="mb-2 flex items-center gap-1.5 text-sm font-bold">History with BMI <InfoHint>From the order register. The draft wording only uses these figures.</InfoHint></h2>
          {h && h.count > 0 ? (
            <>
              <p className="text-xs text-muted-foreground">{h.count} booking{h.count === 1 ? "" : "s"} · {fmtGBP(h.total_gbp)} before VAT</p>
              <ul className="mt-2 flex flex-col gap-1 text-xs">
                {h.bookings.slice(0, 8).map((b, i) => (
                  <li key={i} className="flex justify-between gap-2"><span className="truncate">{b.title} {b.edition} {b.size ? `· ${b.size}` : ""}</span><span className="tabular-nums">{fmtGBP(b.value_gbp)}</span></li>
                ))}
              </ul>
            </>
          ) : <p className="text-xs text-muted-foreground">No bookings on record - a new client.</p>}
          <Link href={`/companies/${proposal.company_id}`} className="mt-3 inline-block text-xs font-semibold text-primary hover:underline">Open {proposal.company_name}</Link>
        </section>
        <p className="text-xs text-muted-foreground">
          {proposal.drafted_by === "ai" ? "The wording was drafted by the brain; any figure it wasn't given was removed." : "The wording is standard text - edit it freely."}
        </p>
      </aside>


      <Dialog open={mailOpen} onOpenChange={setMailOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Email the proposal</DialogTitle>
            <DialogDescription>
              {mail?.outlook_connected
                ? `Sent from your Outlook (${mail.outlook_email}) with the Word file attached. Nothing goes until you press Send.`
                : "Connect your Outlook in Settings first - proposals are sent from your own account."}
            </DialogDescription>
          </DialogHeader>
          {mail && (
            <div className="grid gap-3">
              <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">To
                <Input value={mailTo} onChange={(e) => setMailTo(e.target.value)} placeholder="name@company.com" className="h-8 text-sm" />
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Cc (optional)
                <Input value={mailCc} onChange={(e) => setMailCc(e.target.value)} className="h-8 text-sm" />
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Subject
                <Input value={mail.subject} onChange={(e) => setMail({ ...mail, subject: e.target.value })} className="h-8 text-sm" />
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Message
                <Textarea rows={8} value={mail.body} onChange={(e) => setMail({ ...mail, body: e.target.value })} className="text-sm" />
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">Remind me to follow up in (days)
                <Input type="number" min={0} max={365} value={days} onChange={(e) => setDays(Number(e.target.value) || 0)} className="h-8 text-sm" />
              </label>
            </div>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>Cancel</DialogClose>
            <Button disabled={pending || !mail?.outlook_connected || split(mailTo).length === 0} onClick={() => mail && start(async () => {
              try {
                await sendProposal(proposal.id, { to: split(mailTo), cc: split(mailCc), subject: mail.subject, body: mail.body, follow_up_days: days });
                toast.success("Sent and logged on the client");
                setMailOpen(false);
                router.refresh();
              } catch (e) { toast.error(friendlyError(e, "Couldn't send it")); }
            })}>{pending && <Loader2 className="size-4 animate-spin" />} Send</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={sendOpen} onOpenChange={setSendOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Log this proposal as sent</DialogTitle>
            <DialogDescription>It&apos;s noted on {proposal.company_name} with the products and total, and a follow-up reminder is set for you.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
              How did you send it?
              <select className={selectCls} value={via} onChange={(e) => setVia(e.target.value as typeof via)}>
                <option value="downloaded">Emailed the downloaded file</option>
                <option value="other">Another way</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
              Remind me to follow up in (days)
              <Input type="number" min={0} max={365} value={days} onChange={(e) => setDays(Number(e.target.value) || 0)} className="h-8 text-sm" />
            </label>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>Cancel</DialogClose>
            <Button disabled={pending} onClick={() => start(async () => {
              try {
                if (dirty) await saveProposal(proposal.id, saved());
                await finishProposal(proposal.id, via, days);
                toast.success("Logged on the client");
                setSendOpen(false);
                router.refresh();
              } catch (e) { toast.error(friendlyError(e, "Couldn't log it")); }
            })}>Log it</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
