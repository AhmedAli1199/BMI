"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import Link from "next/link";
import { Check, ClipboardCopy, Loader2, Send } from "lucide-react";
import { toast } from "sonner";
import type { ComposeResult, MailTemplate } from "@/lib/messaging-types";
import { BRAND_LABEL } from "@/lib/messaging-types";
import type { ContactListItem } from "@/lib/types";
import { composeFromTemplate, listCompanyContacts, listTemplates, sendComposed } from "@/lib/messaging-actions";
import { searchContacts } from "@/lib/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { EntityPicker } from "@/components/entity-picker";
import { ProposalIssuePicker } from "@/components/sales/proposal-issue-picker";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-8 w-full min-w-0 truncate rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60 dark:bg-input/30";
const labelCls = "flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted-foreground";
type Option = { id: string; label: string; sublabel?: string | null };

/** Email one person from a template: the template is filled in for them (and for the issue and feature it's about),
 *  you edit it, then send it from your own Outlook (noted on their history) or copy it into your own email. */
export function EmailFromTemplate({ open, onOpenChange, templates: given, initialTemplateId, contact: initialContact, companyId, titleId, editionId: initialEdition, feature: initialFeature }: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  templates?: MailTemplate[];
  initialTemplateId?: string;
  contact?: Option | null;
  companyId?: string | null;
  titleId?: string | null;
  editionId?: string | null;
  feature?: string | null;
}) {
  const [pending, start] = useTransition();
  const [templates, setTemplates] = useState<MailTemplate[]>(given ?? []);
  const [templateId, setTemplateId] = useState(initialTemplateId ?? "");
  const [contact, setContact] = useState<Option | null>(initialContact ?? null);
  const [companyPeople, setCompanyPeople] = useState<ContactListItem[] | null>(null);
  const [editionId, setEditionId] = useState(initialEdition ?? "");
  const [feature, setFeature] = useState(initialFeature ?? "");
  const [draft, setDraft] = useState<ComposeResult | null>(null);
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [copied, setCopied] = useState(false);
  const tpl = templates.find((t) => t.id === templateId);
  const issueTitle = titleId ?? tpl?.title_id ?? null;

  useEffect(() => {
    if (given || !open) return;
    let live = true;
    listTemplates().then((r) => live && setTemplates(r)).catch(() => undefined);
    return () => { live = false; };
  }, [given, open]);
  useEffect(() => {
    if (!companyId || !open) return;
    let live = true;
    listCompanyContacts(companyId).then((r) => {
      if (!live) return;
      setCompanyPeople(r);
      if (!initialContact && r[0]) setContact({ id: r[0].id, label: r[0].full_name ?? "Contact", sublabel: r[0].primary_email });
    }).catch(() => live && setCompanyPeople([]));
    return () => { live = false; };
  }, [companyId, open, initialContact]);

  // Fill the template in whenever the choices change.
  const key = JSON.stringify([templateId, contact?.id, editionId, feature]);
  useEffect(() => {
    if (!open || !templateId) return;
    let live = true;
    const t = setTimeout(() => {
      composeFromTemplate({ template_id: templateId, contact_id: contact?.id ?? null, edition_id: editionId || null, feature: feature || null })
        .then((r) => {
          if (!live) return;
          setDraft(r); setTo(r.to.join(", ")); setSubject(r.subject); setBody(r.body);
        }).catch((e) => toast.error(friendlyError(e, "Couldn't fill in the template")));
    }, 300);
    return () => { live = false; clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, open]);

  const grouped = useMemo(() => {
    const m = new Map<string, MailTemplate[]>();
    for (const t of templates) {
      const g = t.brand ? BRAND_LABEL[t.brand] : "Any brand";
      m.set(g, [...(m.get(g) ?? []), t]);
    }
    return [...m.entries()];
  }, [templates]);
  const left = /\{\{[^}]+\}\}/.test(subject + body);

  function send() {
    const split = (s: string) => s.split(/[,;]/).map((x) => x.trim()).filter(Boolean);
    start(async () => {
      try {
        await sendComposed({ contact_id: contact?.id ?? null, template_id: templateId || null, to: split(to), cc: split(cc), subject, body });
        toast.success("Sent and noted on their history");
        onOpenChange(false);
      } catch (e) { toast.error(friendlyError(e, "Couldn't send it")); }
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Email from a template</DialogTitle>
          <DialogDescription>Filled in for the person and the issue you choose. Change anything before it goes.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className={labelCls}>Template
            <select className={selectCls} value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
              <option value="">Choose…</option>
              {grouped.map(([g, ts]) => (
                <optgroup key={g} label={g}>{ts.map((t) => <option key={t.id} value={t.id}>{t.name}{t.needs_check ? " (needs a check)" : ""}</option>)}</optgroup>
              ))}
            </select>
          </label>
          {companyPeople && companyPeople.length > 0 ? (
            <label className={labelCls}>Who to
              <select className={selectCls} value={contact?.id ?? ""} onChange={(e) => {
                const c = companyPeople.find((x) => x.id === e.target.value);
                setContact(c ? { id: c.id, label: c.full_name ?? "Contact", sublabel: c.primary_email } : null);
              }}>
                {companyPeople.map((c) => <option key={c.id} value={c.id}>{c.full_name ?? "Unnamed"}{c.job_title ? `, ${c.job_title}` : ""}{c.primary_email ? "" : " (no email)"}</option>)}
              </select>
            </label>
          ) : (
            <EntityPicker label="Who to" placeholder="Search for the contact…" value={contact} onChange={setContact} viewHref={(id) => `/contacts/${id}`}
              search={async (q) => (await searchContacts(q)).map((c) => ({ id: c.id, label: c.full_name ?? "Unnamed", sublabel: c.company_name }))} />
          )}
          {(tpl?.uses_issue || initialEdition) && <>
            <label className={labelCls}>Which issue or event
              {issueTitle ? <ProposalIssuePicker titleId={issueTitle} value={editionId} include={initialEdition} onChange={(id) => setEditionId(id)} emptyLabel="None - use the template's fallback words" />
                : <span className="text-[11px] font-normal">Give the template a title to pick its issues.</span>}
            </label>
            <label className={labelCls}>The feature you&apos;re pitching<Input value={feature} onChange={(e) => setFeature(e.target.value)} placeholder="e.g. Japan (blank = the issue's only feature)" className="h-8 text-sm" /></label>
          </>}
        </div>
        {tpl?.needs_check && <p className="text-xs" style={{ color: "var(--warn)" }}>This template hasn&apos;t been checked since it was brought over{tpl.description ? `: ${tpl.description}` : "."}</p>}
        {draft && (
          <div className="flex flex-col gap-3 border-t border-border/70 pt-3">
            {draft.unsubscribed && <p className="text-xs" style={{ color: "var(--warn)" }}>This person has unsubscribed from emails. Only send if they&apos;ve asked to hear from you.</p>}
            {draft.missing.length > 0 && <p className="text-xs" style={{ color: "var(--warn)" }}>Some details had nothing to fill them: choose the issue, type the feature, or add the brand&apos;s figures in the editorial plan&apos;s brand settings.</p>}
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={labelCls}>To<Input value={to} onChange={(e) => setTo(e.target.value)} placeholder="name@company.com" className="h-8 text-sm" /></label>
              <label className={labelCls}>Copy to (optional)<Input value={cc} onChange={(e) => setCc(e.target.value)} className="h-8 text-sm" /></label>
            </div>
            <label className={labelCls}>Subject<Input value={subject} onChange={(e) => setSubject(e.target.value)} className="h-8 text-sm" /></label>
            <label className={labelCls}>Message<Textarea rows={12} value={body} onChange={(e) => setBody(e.target.value)} className="text-sm" /></label>
            {left && <p className="text-xs" style={{ color: "var(--warn)" }}>Something in {"{{curly brackets}}"} is still to fill in.</p>}
          </div>
        )}
        <DialogFooter className="flex-wrap gap-2">
          {draft && !draft.outlook_connected && <span className="mr-auto text-xs text-muted-foreground">Connect Outlook in <Link href="/settings" className="font-semibold text-primary hover:underline">Settings</Link> to send from here.</span>}
          <DialogClose render={<Button variant="ghost" />}>Close</DialogClose>
          <Button variant="outline" className="gap-1.5" disabled={!draft} onClick={() => {
            navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); }).catch(() => toast.error("Couldn't copy it - select the text and copy it yourself"));
          }}>{copied ? <Check className="size-3.5" /> : <ClipboardCopy className="size-3.5" />} Copy</Button>
          <Button className="gap-1.5" disabled={pending || !draft?.outlook_connected || !to.trim() || left} onClick={send}>
            {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />} Send from Outlook
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
