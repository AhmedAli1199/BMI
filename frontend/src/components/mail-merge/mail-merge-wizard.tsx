"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  FolderTree,
  ListFilter,
  Loader2,
  Mail,
  Paperclip,
  Save,
  Send,
  Tags,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EntityPicker } from "@/components/entity-picker";
import { searchCompanies, searchContacts, searchGroups } from "@/lib/actions";
import {
  deleteAttachment,
  listTemplates,
  previewMerge,
  previewRecipients,
  saveTemplate,
  startEmailMerge,
} from "@/lib/messaging-actions";
import type {
  Attachment,
  MailStatus,
  MailTemplate,
  MergeField,
  MergeOutput,
  MergeRequest,
  RecipientSource,
  RecipientsResult,
} from "@/lib/messaging-types";
import { MERGE_SELECTION_KEY, downloadFile, postJson } from "@/lib/download";

export type InitialSource = { source: RecipientSource | null; label: string; fromSelection?: boolean };

type Option = { id: string; label: string; sublabel?: string | null };

const OUTPUTS: { key: MergeOutput; label: string; hint: string; icon: typeof Mail }[] = [
  { key: "email", label: "E-mail", hint: "Personalised emails sent from your own Outlook", icon: Mail },
  { key: "word", label: "Letters (Word)", hint: "One letter per contact, one per page, ready to print", icon: FileText },
  { key: "labels", label: "Address labels", hint: "21 per A4 sheet (Avery L7160 size)", icon: Tags },
  { key: "data", label: "Merge data", hint: "Excel/CSV of names & addresses - for Word's own merge or Mailchimp", icon: FileSpreadsheet },
];

const STEPS = ["Output", "Contacts", "Message", "Options"] as const;

const selectCls =
  "h-9 w-full rounded-md border border-input bg-background px-2.5 text-sm shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function fmtBytes(n: number) {
  return n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;
}

export function MailMergeWizard({
  status,
  fields,
  templates: initialTemplates,
  initial,
}: {
  status: MailStatus | null;
  fields: MergeField[];
  templates: MailTemplate[];
  initial: InitialSource;
}) {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [output, setOutput] = useState<MergeOutput>("email");

  // ---- Step 2: contacts
  const [source, setSource] = useState<RecipientSource | null>(initial.source);
  const [sourceKind, setSourceKind] = useState<string>(
    initial.fromSelection ? "selection" : initial.source?.kind ?? "group"
  );
  const [sourceLabel, setSourceLabel] = useState(initial.label);
  const [recips, setRecips] = useState<RecipientsResult | null>(null);
  const [loadingRecips, setLoadingRecips] = useState(false);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState("");
  const [picked, setPicked] = useState<Option[]>([]);
  const [group, setGroup] = useState<Option | null>(null);
  const [company, setCompany] = useState<Option | null>(null);
  const [selection, setSelection] = useState<{ ids: string[]; label: string } | null>(null);

  // ---- Step 3: message
  const [templates, setTemplates] = useState(initialTemplates);
  const [templateId, setTemplateId] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("Dear {{salutation|colleague}},\n\n\n\nKind regards,\n{{my_name}}");
  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const subjectRef = useRef<HTMLInputElement>(null);
  const [lastFocus, setLastFocus] = useState<"subject" | "body">("body");
  const [previewIdx, setPreviewIdx] = useState(0);
  const [preview, setPreview] = useState<{ subject: string; body: string; html: string; unknown_fields: string[] } | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [tplName, setTplName] = useState("");
  const [tplShared, setTplShared] = useState(true);

  // ---- Step 4: options
  const [recordHistory, setRecordHistory] = useState<"email_full" | "subject_only" | "none">("email_full");
  const [regarding, setRegarding] = useState("");
  const [cc, setCc] = useState("");
  const [bcc, setBcc] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [noEmail, setNoEmail] = useState<"skip" | "letters">("skip");
  const [includeUnsub, setIncludeUnsub] = useState(false);
  const [dataFormat, setDataFormat] = useState<"xlsx" | "csv">("xlsx");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pending, startTransition] = useTransition();

  // A ticked selection arrives via sessionStorage (too big for a URL) -
  // read after mount, since the server render can't see it.
  /* eslint-disable react-hooks/set-state-in-effect -- syncing from browser storage / clearing on source change */
  useEffect(() => {
    if (!initial.fromSelection) return;
    try {
      const raw = sessionStorage.getItem(MERGE_SELECTION_KEY);
      if (raw) {
        const sel = JSON.parse(raw) as { ids: string[]; label: string };
        setSelection(sel);
        setSource({ kind: "contacts", contact_ids: sel.ids });
        setSourceLabel(sel.label);
      }
    } catch {
      // nothing stashed - the user picks contacts instead
    }
  }, [initial.fromSelection]);

  // Load the recipient list whenever the source changes.
  useEffect(() => {
    if (!source) {
      setRecips(null);
      return;
    }
    let cancelled = false;
    setLoadingRecips(true);
    previewRecipients(source)
      .then((r) => {
        if (cancelled) return;
        setRecips(r);
        setExcluded(new Set());
        setPreviewIdx(0);
        if (!sourceLabel) setSourceLabel(r.label);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Couldn't load those contacts"))
      .finally(() => !cancelled && setLoadingRecips(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const items = useMemo(() => recips?.items ?? [], [recips]);
  const included = useMemo(() => items.filter((r) => !excluded.has(r.contact_id)), [items, excluded]);
  const reachable = useMemo(() => {
    if (output === "email") return included.filter((r) => r.email && (includeUnsub || (!r.unsubscribed && !r.bounced)));
    if (output === "labels") return included.filter((r) => r.has_address);
    return included;
  }, [included, output, includeUnsub]);
  const noEmailCount = included.filter((r) => !r.email).length;
  const optedOutCount = included.filter((r) => r.email && (r.unsubscribed || r.bounced)).length;
  const noAddressCount = included.filter((r) => !r.has_address).length;
  const previewRecipient = included[Math.min(previewIdx, Math.max(0, included.length - 1))];
  const needsMessage = output === "email" || output === "word";

  // Live preview for the chosen recipient.
  useEffect(() => {
    if (!needsMessage || step !== 2) return;
    const t = setTimeout(() => {
      previewMerge({ contact_id: previewRecipient?.contact_id ?? null, subject, body })
        .then(setPreview)
        .catch(() => undefined);
    }, 350);
    return () => clearTimeout(t);
  }, [subject, body, previewRecipient?.contact_id, needsMessage, step]);

  function chooseKind(kind: string) {
    setSourceKind(kind);
    if (kind === "lookup" && initial.source?.kind === "lookup") {
      setSource(initial.source);
      setSourceLabel(initial.label);
    } else if (kind === "selection" && selection) {
      setSource({ kind: "contacts", contact_ids: selection.ids });
      setSourceLabel(selection.label);
    } else if (kind === "group" && group) {
      setSource({ kind: "group", group_id: group.id });
      setSourceLabel(`Group: ${group.label}`);
    } else if (kind === "company" && company) {
      setSource({ kind: "company", company_id: company.id });
      setSourceLabel(`Company: ${company.label}`);
    } else if (kind === "contacts" && picked.length) {
      setSource({ kind: "contacts", contact_ids: picked.map((p) => p.id) });
      setSourceLabel(picked.length === 1 ? picked[0].label : `${picked.length} contacts`);
    } else {
      setSource(null);
      setSourceLabel("");
    }
  }

  function insertField(key: string) {
    const token = `{{${key}}}`;
    const el = lastFocus === "subject" ? subjectRef.current : bodyRef.current;
    const value = lastFocus === "subject" ? subject : body;
    const set = lastFocus === "subject" ? setSubject : setBody;
    const start = el?.selectionStart ?? value.length;
    const end = el?.selectionEnd ?? value.length;
    set(value.slice(0, start) + token + value.slice(end));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(start + token.length, start + token.length);
    });
  }

  function applyTemplate(id: string) {
    setTemplateId(id);
    const t = templates.find((x) => x.id === id);
    if (t) {
      setSubject(t.subject ?? "");
      setBody(t.body);
    }
  }

  function doSaveTemplate(asNew: boolean) {
    startTransition(async () => {
      try {
        const current = templates.find((t) => t.id === templateId);
        const t = await saveTemplate(
          { name: asNew ? tplName.trim() : current!.name, subject, body, shared: asNew ? tplShared : current!.shared },
          asNew ? undefined : templateId
        );
        setTemplates(await listTemplates());
        setTemplateId(t.id);
        setSaveOpen(false);
        toast.success(asNew ? `Saved as “${t.name}”` : "Template updated");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't save the template");
      }
    });
  }

  async function uploadFiles(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    try {
      for (const f of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", f);
        const res = await fetch("/api/files/mail-merge/attachments", { method: "POST", body: fd });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data?.detail || `Couldn't attach ${f.name}`);
        setAttachments((prev) => [...prev, data as Attachment]);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function request(extra: Partial<MergeRequest> = {}): MergeRequest {
    return {
      output,
      source_label: sourceLabel || recips?.label,
      contact_ids: reachable.map((r) => r.contact_id),
      subject: subject || undefined,
      body,
      cc: cc || undefined,
      bcc: bcc || undefined,
      attachment_ids: attachments.map((a) => a.id),
      record_history: recordHistory,
      history_regarding: regarding || undefined,
      no_email: noEmail,
      include_unsubscribed: includeUnsub,
      data_format: dataFormat,
      ...extra,
    };
  }

  function sendTest() {
    startTransition(async () => {
      try {
        const r = await startEmailMerge(
          request({ test_only: true, contact_ids: [previewRecipient?.contact_id ?? reachable[0].contact_id] })
        );
        if ("test_sent_to" in r) toast.success(`Test (as ${r.rendered_for || "first contact"}) sent to ${r.test_sent_to}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Test send failed");
      }
    });
  }

  function run() {
    setConfirmOpen(false);
    startTransition(async () => {
      try {
        if (output === "email") {
          // Letters for the no-email contacts are a merge of their own.
          const r = await startEmailMerge(
            request({
              contact_ids: included.map((x) => x.contact_id),
            })
          );
          if ("id" in r) {
            if (noEmail === "letters" && (r.letters_for_no_email ?? 0) > 0) {
              await downloadFile(`/api/files/mail-merge/${r.id}/letters`, "letters-no-email.docx", { method: "POST" });
            }
            toast.success(`Queued ${(r.total - r.skipped).toLocaleString()} emails - sending now`);
            router.push(`/mail-merge/${r.id}`);
          }
        } else {
          const name = output === "data" ? `merge-data.${dataFormat}` : output === "labels" ? "labels.docx" : "letters.docx";
          await downloadFile("/api/files/mail-merge", name, postJson(request()));
          toast.success(
            output === "word"
              ? `${reachable.length} letters downloaded${recordHistory !== "none" ? " and logged to each contact's history" : ""}`
              : "Downloaded"
          );
        }
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "That didn't work");
      }
    });
  }

  // ---- Validation per step
  const canNext = [
    true,
    !!recips && included.length > 0,
    !needsMessage || (body.trim().length > 0 && (output !== "email" || subject.trim().length > 0) && !(preview?.unknown_fields.length)),
    true,
  ];
  const emailBlocked = output === "email" && (!status?.connected || status.needs_reconnect);

  const filtered = filter.trim()
    ? items.filter((r) =>
        [r.name, r.company, r.email, r.city].some((v) => v?.toLowerCase().includes(filter.trim().toLowerCase()))
      )
    : items;

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      {/* Stepper */}
      <nav aria-label="Mail merge steps" className="flex gap-2 overflow-x-auto lg:flex-col">
        {STEPS.map((label, i) => {
          const done = i < step;
          const active = i === step;
          const reachableStep = i <= step || canNext.slice(0, i).every(Boolean);
          const skip = i === 2 && !needsMessage;
          return (
            <button
              key={label}
              type="button"
              disabled={!reachableStep}
              onClick={() => setStep(i)}
              aria-current={active ? "step" : undefined}
              className={`flex min-w-36 items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors ${
                active
                  ? "border-primary bg-primary/5 font-semibold text-foreground"
                  : "border-border text-muted-foreground hover:bg-accent/40 disabled:opacity-50"
              }`}
            >
              <span
                className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  done ? "bg-emerald-600 text-white" : active ? "bg-primary text-primary-foreground" : "bg-muted"
                }`}
              >
                {done ? <Check className="size-3.5" /> : i + 1}
              </span>
              <span className="flex flex-col">
                <span>{label}</span>
                <span className="text-[11px] font-normal text-muted-foreground">
                  {i === 0 && OUTPUTS.find((o) => o.key === output)?.label}
                  {i === 1 && (recips ? `${included.length.toLocaleString()} contacts` : "Choose who")}
                  {i === 2 && (skip ? "Not needed" : subject || (body ? "Written" : "Write it"))}
                  {i === 3 && "Check & send"}
                </span>
              </span>
            </button>
          );
        })}
      </nav>

      <div className="flex min-w-0 flex-col gap-5">
        {/* ---------------- Step 1: Output ---------------- */}
        {step === 0 && (
          <section className="flex flex-col gap-4">
            <StepTitle title="What do you want to create?" hint="Act!'s “Output to”. You can change this at any point." />
            <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Output">
              {OUTPUTS.map((o) => {
                const Icon = o.icon;
                const active = output === o.key;
                return (
                  <button
                    key={o.key}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setOutput(o.key)}
                    className={`flex items-start gap-3 rounded-xl border p-4 text-left transition-all ${
                      active ? "border-primary bg-primary/5 ring-2 ring-primary/20" : "border-border hover:bg-accent/40"
                    }`}
                  >
                    <span className={`brand-icon size-10 shrink-0 ${active ? "text-primary" : "text-muted-foreground"}`}>
                      <Icon className="size-5" />
                    </span>
                    <span>
                      <span className="block font-semibold">{o.label}</span>
                      <span className="block text-xs text-muted-foreground">{o.hint}</span>
                    </span>
                  </button>
                );
              })}
            </div>
            {output === "email" && status && !status.connected && (
              <Notice tone="warn">
                Emails are sent from your own Outlook, so you need to connect it once first.{" "}
                {status.configured ? (
                  <a className="font-semibold underline" href="/api/outlook/connect?return_to=/mail-merge">
                    Connect Outlook
                  </a>
                ) : (
                  "An administrator still needs to set up the Microsoft connection."
                )}{" "}
                You can still prepare everything now.
              </Notice>
            )}
            {output === "email" && status?.needs_reconnect && (
              <Notice tone="warn">
                Your Outlook connection has expired.{" "}
                <a className="font-semibold underline" href="/api/outlook/connect?return_to=/mail-merge">
                  Reconnect
                </a>
              </Notice>
            )}
            {output === "email" && status?.connected && !status.needs_reconnect && (
              <Notice tone="ok">
                Sending as <strong>{status.email}</strong>, up to {status.per_minute} a minute. Messages appear in
                your Sent Items.
              </Notice>
            )}
          </section>
        )}

        {/* ---------------- Step 2: Contacts ---------------- */}
        {step === 1 && (
          <section className="flex flex-col gap-4">
            <StepTitle
              title="Who is it going to?"
              hint="Pick where the contacts come from, then untick anyone to leave out of this mailing only - they stay in the group."
            />
            <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Contacts from">
              {[
                ...(initial.source?.kind === "lookup" ? [{ k: "lookup", label: "Current lookup", icon: ListFilter }] : []),
                ...(selection ? [{ k: "selection", label: "Ticked contacts", icon: Check }] : []),
                { k: "group", label: "A group", icon: FolderTree },
                { k: "company", label: "A company", icon: Building2 },
                { k: "contacts", label: "Specific contacts", icon: UserRound },
              ].map(({ k, label, icon: Icon }) => (
                <button
                  key={k}
                  type="button"
                  role="radio"
                  aria-checked={sourceKind === k}
                  onClick={() => chooseKind(k)}
                  className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                    sourceKind === k
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border text-muted-foreground hover:bg-accent/50"
                  }`}
                >
                  <Icon className="size-3.5" />
                  {label}
                </button>
              ))}
            </div>

            {sourceKind === "group" && (
              <div className="max-w-md">
                <EntityPicker
                  label="Group"
                  placeholder="Search groups…"
                  value={group}
                  onChange={(g) => {
                    setGroup(g);
                    setSource(g ? { kind: "group", group_id: g.id } : null);
                    setSourceLabel(g ? `Group: ${g.label}` : "");
                  }}
                  search={async (q) =>
                    (await searchGroups(q)).map((g) => ({
                      id: g.id,
                      label: g.name,
                      sublabel: `${g.member_count.toLocaleString()} members`,
                    }))
                  }
                />
                {initial.source?.kind === "group" && !group && (
                  <p className="mt-1 text-xs text-muted-foreground">Currently: {initial.label}</p>
                )}
              </div>
            )}
            {sourceKind === "company" && (
              <div className="max-w-md">
                <EntityPicker
                  label="Company"
                  placeholder="Search companies…"
                  value={company}
                  onChange={(c) => {
                    setCompany(c);
                    setSource(c ? { kind: "company", company_id: c.id } : null);
                    setSourceLabel(c ? `Company: ${c.label}` : "");
                  }}
                  search={async (q) => (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name }))}
                />
                {initial.source?.kind === "company" && !company && (
                  <p className="mt-1 text-xs text-muted-foreground">Currently: everyone at {initial.label}</p>
                )}
              </div>
            )}
            {sourceKind === "contacts" && (
              <div className="flex max-w-xl flex-col gap-2">
                <EntityPicker
                  label="Add a contact"
                  placeholder="Search by name or email…"
                  value={null}
                  onChange={(c) => {
                    if (!c || picked.some((p) => p.id === c.id)) return;
                    const next = [...picked, c];
                    setPicked(next);
                    setSource({ kind: "contacts", contact_ids: next.map((p) => p.id) });
                    setSourceLabel(next.length === 1 ? next[0].label : `${next.length} contacts`);
                  }}
                  search={async (q) =>
                    (await searchContacts(q)).map((c) => ({
                      id: c.id,
                      label: c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "(no name)",
                      sublabel: c.company_name,
                    }))
                  }
                />
                {picked.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {picked.map((p) => (
                      <Badge key={p.id} variant="secondary" className="gap-1">
                        {p.label}
                        <button
                          type="button"
                          aria-label={`Remove ${p.label}`}
                          onClick={() => {
                            const next = picked.filter((x) => x.id !== p.id);
                            setPicked(next);
                            setSource(next.length ? { kind: "contacts", contact_ids: next.map((x) => x.id) } : null);
                          }}
                        >
                          <X className="size-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
                {initial.source?.kind === "contacts" && !picked.length && initial.label && (
                  <p className="text-xs text-muted-foreground">Currently: {initial.label}</p>
                )}
              </div>
            )}

            {loadingRecips && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Loading contacts…
              </p>
            )}

            {recips && !loadingRecips && (
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge variant="outline" className="gap-1">
                    <Users className="size-3" /> {sourceLabel || recips.label}
                  </Badge>
                  <span className="font-semibold">{included.length.toLocaleString()} included</span>
                  {excluded.size > 0 && (
                    <span className="text-muted-foreground">
                      · {excluded.size} left out{" "}
                      <button type="button" className="text-primary underline" onClick={() => setExcluded(new Set())}>
                        include all
                      </button>
                    </span>
                  )}
                  {output === "email" && noEmailCount > 0 && (
                    <Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-300">
                      {noEmailCount} without email
                    </Badge>
                  )}
                  {output === "email" && optedOutCount > 0 && (
                    <Badge variant="outline" className="border-destructive/40 text-destructive">
                      {optedOutCount} unsubscribed/bounced
                    </Badge>
                  )}
                  {output === "labels" && noAddressCount > 0 && (
                    <Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-300">
                      {noAddressCount} without an address
                    </Badge>
                  )}
                </div>
                {recips.truncated && (
                  <Notice tone="warn">
                    Only the first {recips.total.toLocaleString()} contacts are included - for bigger mailings, export
                    the merge data to Mailchimp.
                  </Notice>
                )}
                <div className="flex items-center gap-2">
                  <Input
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder="Filter this list…"
                    aria-label="Filter recipients"
                    className="h-8 max-w-xs text-xs"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 text-xs"
                    onClick={() =>
                      setExcluded((prev) => {
                        const next = new Set(prev);
                        const allOut = filtered.every((r) => next.has(r.contact_id));
                        filtered.forEach((r) => (allOut ? next.delete(r.contact_id) : next.add(r.contact_id)));
                        return next;
                      })
                    }
                  >
                    {filtered.every((r) => excluded.has(r.contact_id)) ? "Tick" : "Untick"} {filter ? "these" : "all"}
                  </Button>
                </div>
                <div className="max-h-[26rem] overflow-y-auto rounded-lg border border-border">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-muted/80 text-left text-[11px] uppercase tracking-wider text-muted-foreground backdrop-blur">
                      <tr>
                        <th className="w-9 px-3 py-2"><span className="sr-only">Include</span></th>
                        <th className="px-2 py-2">Name</th>
                        <th className="hidden px-2 py-2 sm:table-cell">Company</th>
                        <th className="px-2 py-2">{output === "labels" ? "Address" : "Email"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.slice(0, 1000).map((r) => {
                        const on = !excluded.has(r.contact_id);
                        const problem =
                          output === "email"
                            ? !r.email
                              ? "No email"
                              : r.unsubscribed
                                ? "Unsubscribed"
                                : r.bounced
                                  ? "Bounced"
                                  : null
                            : output === "labels" && !r.has_address
                              ? "No address"
                              : null;
                        return (
                          <tr key={r.contact_id} className={`border-t border-border/60 ${on ? "" : "opacity-50"}`}>
                            <td className="px-3 py-1.5">
                              <input
                                type="checkbox"
                                className="size-3.5 accent-primary"
                                checked={on}
                                aria-label={`Include ${r.name}`}
                                onChange={() =>
                                  setExcluded((prev) => {
                                    const next = new Set(prev);
                                    if (next.has(r.contact_id)) next.delete(r.contact_id);
                                    else next.add(r.contact_id);
                                    return next;
                                  })
                                }
                              />
                            </td>
                            <td className="px-2 py-1.5 font-medium">{r.name}</td>
                            <td className="hidden px-2 py-1.5 text-muted-foreground sm:table-cell">{r.company ?? "—"}</td>
                            <td className="px-2 py-1.5">
                              {problem ? (
                                <span className="text-xs font-medium text-amber-700 dark:text-amber-300">
                                  {problem}
                                  {r.email && output === "email" ? ` · ${r.email}` : ""}
                                </span>
                              ) : (
                                <span className="font-mono text-xs text-muted-foreground">
                                  {output === "labels" ? [r.city, r.country].filter(Boolean).join(", ") || "Has address" : r.email ?? "—"}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  {filtered.length > 1000 && (
                    <p className="border-t border-border px-3 py-2 text-xs text-muted-foreground">
                      Showing the first 1,000 - filter the list to find anyone else.
                    </p>
                  )}
                </div>
              </div>
            )}
            {!source && !loadingRecips && (
              <p className="text-sm text-muted-foreground">Choose where the contacts come from.</p>
            )}
          </section>
        )}

        {/* ---------------- Step 3: Message ---------------- */}
        {step === 2 && (
          <section className="flex flex-col gap-4">
            {!needsMessage ? (
              <>
                <StepTitle title="No message needed" hint={output === "labels" ? "Labels use each contact's name, company and address." : "The data file has every merge field as a column."} />
              </>
            ) : (
              <>
                <StepTitle
                  title={output === "email" ? "Write the email" : "Write the letter"}
                  hint="Click a merge field to drop it in where your cursor is. {{first_name|there}} means “use ‘there’ if the contact has no first name”."
                />
                <div className="flex flex-wrap items-end gap-2">
                  <div className="flex min-w-56 flex-1 flex-col gap-1.5">
                    <Label htmlFor="mm-template">Template</Label>
                    <select id="mm-template" className={selectCls} value={templateId} onChange={(e) => applyTemplate(e.target.value)}>
                      <option value="">— Start from blank —</option>
                      {templates.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                          {t.mine ? "" : t.owner_name ? ` (by ${t.owner_name})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                  {templateId && templates.find((t) => t.id === templateId)?.mine && (
                    <Button variant="outline" size="sm" className="h-9" disabled={pending} onClick={() => doSaveTemplate(false)}>
                      <Save className="size-3.5" />
                      Update template
                    </Button>
                  )}
                  <Button variant="outline" size="sm" className="h-9" onClick={() => setSaveOpen(true)}>
                    <Save className="size-3.5" />
                    Save as new template
                  </Button>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="flex flex-col gap-3">
                    {output === "email" && (
                      <div className="flex flex-col gap-1.5">
                        <Label htmlFor="mm-subject">Subject</Label>
                        <Input
                          id="mm-subject"
                          ref={subjectRef}
                          value={subject}
                          onFocus={() => setLastFocus("subject")}
                          onChange={(e) => setSubject(e.target.value)}
                          placeholder="e.g. {{company}} in our spring issue"
                        />
                      </div>
                    )}
                    <div className="flex flex-col gap-1.5">
                      <Label htmlFor="mm-body">{output === "email" ? "Message" : "Letter"}</Label>
                      <Textarea
                        id="mm-body"
                        ref={bodyRef}
                        rows={14}
                        value={body}
                        onFocus={() => setLastFocus("body")}
                        onChange={(e) => setBody(e.target.value)}
                        className="font-[inherit] text-sm leading-relaxed"
                      />
                      <p className="text-[11px] text-muted-foreground">
                        Plain text keeps your line breaks. Pasting HTML (e.g. from an email designer) sends it as-is.
                      </p>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <span className="text-xs font-semibold text-muted-foreground">
                        Insert into {lastFocus === "subject" ? "subject" : "message"}:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {fields.map((f) => (
                          <button
                            key={f.key}
                            type="button"
                            title={`e.g. ${f.example}`}
                            onMouseDown={(e) => e.preventDefault()}
                            onClick={() => insertField(f.key)}
                            className="rounded border border-border bg-muted/40 px-1.5 py-0.5 text-[11px] font-medium hover:border-primary hover:text-primary"
                          >
                            {f.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Preview</span>
                      {included.length > 0 && (
                        <div className="flex items-center gap-1 text-xs">
                          <Button size="icon" variant="ghost" className="size-7" aria-label="Previous contact"
                            disabled={previewIdx === 0} onClick={() => setPreviewIdx((i) => Math.max(0, i - 1))}>
                            <ChevronLeft className="size-4" />
                          </Button>
                          <span className="max-w-40 truncate font-medium">{previewRecipient?.name}</span>
                          <Button size="icon" variant="ghost" className="size-7" aria-label="Next contact"
                            disabled={previewIdx >= included.length - 1} onClick={() => setPreviewIdx((i) => Math.min(included.length - 1, i + 1))}>
                            <ChevronRight className="size-4" />
                          </Button>
                        </div>
                      )}
                    </div>
                    <div className="min-h-64 rounded-lg border border-border bg-card p-4 shadow-2xs">
                      {output === "email" && (
                        <div className="mb-3 border-b border-border pb-2 text-sm">
                          <div className="text-xs text-muted-foreground">
                            To: {previewRecipient?.email ?? "—"}
                          </div>
                          <div className="font-semibold">{preview?.subject || <span className="text-muted-foreground">(no subject)</span>}</div>
                        </div>
                      )}
                      {preview ? (
                        /* Rendered server-side from the user's own text; the preview
                           pane is sandboxed so pasted HTML can't run scripts. */
                        <iframe
                          title="Message preview"
                          sandbox=""
                          srcDoc={`<body style="margin:0;font-family:Calibri,Arial,sans-serif;font-size:14px;color:#1f2937">${preview.html}</body>`}
                          className="h-72 w-full rounded bg-white"
                        />
                      ) : (
                        <p className="text-sm text-muted-foreground">Start typing to see it for each contact.</p>
                      )}
                    </div>
                    {preview && preview.unknown_fields.length > 0 && (
                      <Notice tone="warn">
                        Unknown merge field{preview.unknown_fields.length > 1 ? "s" : ""}:{" "}
                        {preview.unknown_fields.map((f) => `{{${f}}}`).join(", ")} - check the spelling.
                      </Notice>
                    )}
                  </div>
                </div>
              </>
            )}
          </section>
        )}

        {/* ---------------- Step 4: Options ---------------- */}
        {step === 3 && (
          <section className="flex flex-col gap-5">
            <StepTitle title="Options" hint="Act!'s e-mail and printer options." />

            {(output === "email" || output === "word") && (
              <fieldset className="flex flex-col gap-2 rounded-lg border border-border p-4">
                <legend className="px-1 text-sm font-semibold">Record history</legend>
                {(output === "email"
                  ? [
                      { v: "email_full", l: "Subject and message", h: "The whole email is saved to each contact's history" },
                      { v: "subject_only", l: "Subject only", h: "Just a line saying the email was sent" },
                      { v: "none", l: "Don't record", h: "Nothing added to history" },
                    ]
                  : [
                      { v: "subject_only", l: "Record a “Letter Sent”", h: "One line per contact, with the ‘Regarding’ below" },
                      { v: "none", l: "Don't record", h: "Nothing added to history" },
                    ]
                ).map((o) => (
                  <label key={o.v} className="flex items-start gap-2 text-sm">
                    <input
                      type="radio"
                      name="history"
                      className="mt-1 accent-primary"
                      checked={recordHistory === o.v || (output === "word" && o.v === "subject_only" && recordHistory === "email_full")}
                      onChange={() => setRecordHistory(o.v as typeof recordHistory)}
                    />
                    <span>
                      <span className="font-medium">{o.l}</span>
                      <span className="block text-xs text-muted-foreground">{o.h}</span>
                    </span>
                  </label>
                ))}
                {output === "word" && recordHistory !== "none" && (
                  <div className="mt-1 flex max-w-md flex-col gap-1.5">
                    <Label htmlFor="mm-regarding">Regarding</Label>
                    <Input id="mm-regarding" value={regarding} onChange={(e) => setRegarding(e.target.value)} placeholder="e.g. Spring issue media pack" />
                  </div>
                )}
              </fieldset>
            )}

            {output === "email" && (
              <>
                <fieldset className="grid gap-3 rounded-lg border border-border p-4 sm:grid-cols-2">
                  <legend className="px-1 text-sm font-semibold">Copies</legend>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="mm-cc">Cc (on every email)</Label>
                    <Input id="mm-cc" value={cc} onChange={(e) => setCc(e.target.value)} placeholder="colleague@bmipublishing.co.uk" />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="mm-bcc">Bcc (on every email)</Label>
                    <Input id="mm-bcc" value={bcc} onChange={(e) => setBcc(e.target.value)} />
                  </div>
                </fieldset>

                <fieldset className="flex flex-col gap-2 rounded-lg border border-border p-4">
                  <legend className="px-1 text-sm font-semibold">Attachments</legend>
                  {attachments.map((a) => (
                    <div key={a.id} className="flex items-center gap-2 text-sm">
                      <Paperclip className="size-3.5 text-muted-foreground" />
                      <span className="truncate">{a.filename}</span>
                      <span className="text-xs text-muted-foreground">{fmtBytes(a.size)}</span>
                      <button
                        type="button"
                        aria-label={`Remove ${a.filename}`}
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => {
                          setAttachments((prev) => prev.filter((x) => x.id !== a.id));
                          deleteAttachment(a.id).catch(() => undefined);
                        }}
                      >
                        <X className="size-3.5" />
                      </button>
                    </div>
                  ))}
                  <label className="flex w-fit cursor-pointer items-center gap-1.5 rounded-md border border-dashed border-border px-3 py-1.5 text-sm hover:bg-accent/40">
                    {uploading ? <Loader2 className="size-3.5 animate-spin" /> : <Paperclip className="size-3.5" />}
                    {uploading ? "Uploading…" : "Attach a file"}
                    <input type="file" multiple className="sr-only" onChange={(e) => uploadFiles(e.target.files)} />
                  </label>
                  <p className="text-[11px] text-muted-foreground">
                    Up to 3 MB in total. For bigger files (a full media kit), put a link in the message instead.
                  </p>
                </fieldset>

                <fieldset className="flex flex-col gap-2 rounded-lg border border-border p-4">
                  <legend className="px-1 text-sm font-semibold">Contacts who can&apos;t be emailed</legend>
                  <label className="flex items-start gap-2 text-sm">
                    <input type="radio" name="noemail" className="mt-1 accent-primary" checked={noEmail === "skip"} onChange={() => setNoEmail("skip")} />
                    <span>
                      <span className="font-medium">Skip them</span>
                      <span className="block text-xs text-muted-foreground">{noEmailCount} have no email address</span>
                    </span>
                  </label>
                  <label className="flex items-start gap-2 text-sm">
                    <input type="radio" name="noemail" className="mt-1 accent-primary" checked={noEmail === "letters"} onChange={() => setNoEmail("letters")} />
                    <span>
                      <span className="font-medium">Make Word letters for them</span>
                      <span className="block text-xs text-muted-foreground">Downloads straight after the emails are queued</span>
                    </span>
                  </label>
                  <label className="mt-1 flex items-start gap-2 border-t border-border/60 pt-2 text-sm">
                    <input type="checkbox" className="mt-1 accent-primary" checked={includeUnsub} onChange={(e) => setIncludeUnsub(e.target.checked)} />
                    <span>
                      <span className="font-medium">Include unsubscribed and bounced contacts</span>
                      <span className="block text-xs text-muted-foreground">
                        Off by default - only for essential, non-marketing messages (e.g. an invoice query). {optedOutCount} affected.
                      </span>
                    </span>
                  </label>
                </fieldset>
              </>
            )}

            {output === "data" && (
              <fieldset className="flex flex-col gap-2 rounded-lg border border-border p-4">
                <legend className="px-1 text-sm font-semibold">File type</legend>
                {(["xlsx", "csv"] as const).map((f) => (
                  <label key={f} className="flex items-center gap-2 text-sm">
                    <input type="radio" name="fmt" className="accent-primary" checked={dataFormat === f} onChange={() => setDataFormat(f)} />
                    {f === "xlsx" ? "Excel (.xlsx) - for Word's own mail merge" : "CSV - for Mailchimp and most other tools"}
                  </label>
                ))}
              </fieldset>
            )}

            {/* Summary */}
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4">
              <p className="text-sm">
                <strong>{OUTPUTS.find((o) => o.key === output)?.label}</strong> for{" "}
                <strong>{reachable.length.toLocaleString()}</strong> of {included.length.toLocaleString()} contacts
                {sourceLabel ? <> from <strong>{sourceLabel}</strong></> : null}.
                {output === "email" && status?.per_minute
                  ? ` About ${Math.max(1, Math.ceil(reachable.length / status.per_minute))} min to send.`
                  : ""}
              </p>
              {output === "email" && reachable.length < included.length && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {included.length - reachable.length} will be skipped (no email, unsubscribed or bounced) and listed on the progress page.
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {output === "email" ? (
                  <>
                    <Button variant="outline" disabled={pending || emailBlocked || reachable.length === 0} onClick={sendTest}>
                      <Send className="size-4" />
                      Send a test to myself
                    </Button>
                    <Button disabled={pending || emailBlocked || reachable.length === 0} onClick={() => setConfirmOpen(true)}>
                      {pending ? <Loader2 className="size-4 animate-spin" /> : <Mail className="size-4" />}
                      Send {reachable.length.toLocaleString()} emails
                    </Button>
                  </>
                ) : (
                  <Button disabled={pending || reachable.length === 0} onClick={run}>
                    {pending ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}
                    {output === "word" ? `Create ${reachable.length} letters` : output === "labels" ? "Create labels" : "Download merge data"}
                  </Button>
                )}
              </div>
              {emailBlocked && (
                <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
                  Connect your Outlook first (Settings › Email) to send.
                </p>
              )}
            </div>
          </section>
        )}

        {/* Nav */}
        <div className="flex items-center justify-between border-t border-border pt-4">
          <Button variant="ghost" disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))}>
            <ArrowLeft className="size-4" />
            Back
          </Button>
          {step < 3 && (
            <Button disabled={!canNext[step]} onClick={() => setStep((s) => Math.min(3, s + 1))}>
              Next
              <ArrowRight className="size-4" />
            </Button>
          )}
          {step === 3 && (
            <Link href="/mail-merge/history" className="text-xs font-medium text-muted-foreground hover:text-foreground">
              See earlier mail merges
            </Link>
          )}
        </div>
      </div>

      <Dialog open={saveOpen} onOpenChange={setSaveOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Save as a template</DialogTitle>
            <DialogDescription>Reuse this subject and message next time - merge fields are kept as fields.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="tpl-name">Template name</Label>
              <Input id="tpl-name" value={tplName} onChange={(e) => setTplName(e.target.value)} placeholder="e.g. Renewal – onboard titles" autoFocus />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="accent-primary" checked={tplShared} onChange={(e) => setTplShared(e.target.checked)} />
              Share with the team
            </label>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button disabled={pending || !tplName.trim()} onClick={() => doSaveTemplate(true)}>
              Save template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Send {reachable.length.toLocaleString()} emails?</DialogTitle>
            <DialogDescription>
              From {status?.email}, subject “{preview?.subject || subject}”. They go out over the next{" "}
              {Math.max(1, Math.ceil(reachable.length / Math.max(1, status?.per_minute ?? 25)))} minute(s); you can pause
              or cancel from the progress page.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Not yet</DialogClose>
            <Button onClick={run} disabled={pending}>
              <Send className="size-4" />
              Send now
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StepTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <div>
      <h2 className="text-lg font-bold">{title}</h2>
      {hint && <p className="text-xs text-muted-foreground sm:text-sm">{hint}</p>}
    </div>
  );
}

function Notice({ tone, children }: { tone: "warn" | "ok"; children: React.ReactNode }) {
  return (
    <div
      className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${
        tone === "warn"
          ? "border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200"
          : "border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200"
      }`}
    >
      {tone === "warn" ? <AlertTriangle className="mt-0.5 size-4 shrink-0" /> : <Check className="mt-0.5 size-4 shrink-0" />}
      <span>{children}</span>
    </div>
  );
}
