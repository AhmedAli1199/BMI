"use client";

import { useEffect, useLayoutEffect, useRef, useState, useTransition } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import {
  AlertTriangle,
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Layers,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EntityPicker } from "@/components/entity-picker";
import { cleanNoteBody } from "@/lib/notes";
import { styleForKind } from "@/lib/automation-style";
import { resolveReviewItem, searchCompanies, searchContacts, searchGroups } from "@/lib/actions";
import { DraftReviewDialog } from "@/components/draft-review-dialog";
import type { CompanyListItem, GroupListItem, ReviewAction, ReviewKind, ReviewQueueItem } from "@/lib/types";

/** Kind+action combos whose payload.original_text is an AI-drafted note/
 * email (not source material) and whose approve action writes it verbatim
 * to a record - these get the full preview/edit/regenerate dialog
 * (draft-review-dialog.tsx) instead of the generic one-click confirm, so
 * a reviewer always sees and can adjust exactly what's about to be
 * written before it happens. See registry.py's ReviewKind.redraft. */
const DRAFT_REVIEW_ACTIONS: Record<string, string> = {
  signal_trigger: "draft_followup",
  followup_due: "mark_sent",
  personal_touchpoint_due: "draft_touchpoint",
};

const STYLE_CLASSES: Record<ReviewAction["style"], string> = {
  primary: "",
  secondary: "",
  destructive: "text-destructive hover:text-destructive border-destructive/40 hover:bg-destructive/10",
};

/** Confidence reads as a color, not just a number - a reviewer scanning a
 * long queue should be able to tell "safe bet" from "coin flip" at a
 * glance, before reading a single word of the summary. */
function confidenceTone(confidence: number): { dot: string; text: string } {
  if (confidence >= 0.75) return { dot: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400" };
  if (confidence >= 0.45) return { dot: "bg-amber-500", text: "text-amber-600 dark:text-amber-400" };
  return { dot: "bg-rose-500", text: "text-rose-600 dark:text-rose-400" };
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

/** Extracts all available contact, company, phone, and group details from the
 * payload (including signature, details list, card OCR, and replacements) to
 * prefill review action form inputs automatically. */
function computeInitialFields(
  payload: ReviewQueueItem["payload"],
  action: ReviewAction
): Record<string, string> {
  const initial: Record<string, string> = { ...(payload.prefill ?? {}) };

  // 1. Signature extraction (SALES-011 Inbound Capture)
  const sig = payload.signature as {
    full_name?: string | null;
    job_title?: string | null;
    company_name?: string | null;
    phone?: string | null;
    mobile?: string | null;
  } | undefined;

  if (sig) {
    if (sig.full_name && !initial["name"]) initial["name"] = sig.full_name;
    if (sig.job_title && !initial["job_title"]) initial["job_title"] = sig.job_title;
    if (sig.company_name && !initial["company_name"]) initial["company_name"] = sig.company_name;
    if (sig.phone && !initial["phone"] && sig.phone !== "-") initial["phone"] = sig.phone;
    if (sig.mobile && !initial["mobile"] && sig.mobile !== "-") initial["mobile"] = sig.mobile;
  }

  // 2. Scan details array for any remaining gaps
  if (payload.details && Array.isArray(payload.details)) {
    for (const d of payload.details) {
      const val = (d.value ?? "").trim();
      if (!val || val === "-" || val.startsWith("(none")) continue;

      if ((d.key === "sig_name" || d.label === "Name (from signature)") && !initial["name"]) {
        initial["name"] = val;
      }
      if ((d.key === "sig_title" || d.label === "Job title (from signature)") && !initial["job_title"]) {
        initial["job_title"] = val;
      }
      if ((d.key === "sig_company" || d.label === "Company (from signature)") && !initial["company_name"]) {
        initial["company_name"] = val;
      }
      if ((d.key === "suggested_company" || d.label === "Suggested company") && !initial["company_name"]) {
        initial["company_name"] = val;
      }
      if ((d.key === "sig_phone" || d.label === "Phone (from signature)") && !initial["phone"]) {
        initial["phone"] = val;
      }
      if ((d.key === "sig_mobile" || d.label === "Mobile (from signature)") && !initial["mobile"]) {
        initial["mobile"] = val;
      }
      if ((d.key === "suggested_groups" || d.label === "Suggested groups") && !initial["groups"]) {
        initial["groups"] = val;
      }
    }
  }

  // 3. Fallback for suggested company if not in signature
  if (!initial["company_name"]) {
    const suggestedCompanyDetail = payload.details?.find(
      (d) => (d.key === "suggested_company" || d.label === "Suggested company") && !d.value?.startsWith("(none")
    );
    if (suggestedCompanyDetail?.value) {
      initial["company_name"] = suggestedCompanyDetail.value.trim();
    }
  }

  // 4. Source db - only meaningful (and only ever shown) when the item
  // came in on a genuinely shared inbox ("*"): a normal per-title mailbox
  // already resolved its own database server-side, so there's nothing to
  // ask and nothing to prefill here - leaving initial["source_db"] unset
  // in that case is what keeps the picker hidden below.

  // 5. OOO replacements prefill (for create_new_contact)
  const replacements = payload.replacements as Array<{
    name?: string | null;
    email?: string | null;
    phone?: string | null;
    role?: string | null;
  }> | undefined;

  if (replacements && replacements.length > 0) {
    const first = replacements[0];
    if (first.name && !initial["name"]) initial["name"] = first.name;
    if (first.email && !initial["email"]) initial["email"] = first.email;
    if (first.phone && !initial["phone"]) initial["phone"] = first.phone;
    if (first.role && !initial["job_title"]) initial["job_title"] = first.role;
  }

  // 6. Business card prefill
  const card = payload.card as {
    full_name?: string | null;
    job_title?: string | null;
    company_name?: string | null;
    email?: string | null;
    phone?: string | null;
    mobile?: string | null;
  } | undefined;

  if (card) {
    if (card.full_name && !initial["name"]) initial["name"] = card.full_name;
    if (card.job_title && !initial["job_title"]) initial["job_title"] = card.job_title;
    if (card.company_name && !initial["company_name"]) initial["company_name"] = card.company_name;
    if (card.email && !initial["email"]) initial["email"] = card.email;
    if (card.phone && !initial["phone"]) initial["phone"] = card.phone;
    if (card.mobile && !initial["mobile"]) initial["mobile"] = card.mobile;
  }

  const suggestedGroups = payload.suggested_groups as string[] | undefined;
  if (suggestedGroups && Array.isArray(suggestedGroups) && !initial["groups"]) {
    initial["groups"] = suggestedGroups.join(", ");
  }

  // 7. Initialize every extra_field so inputs are strictly controlled
  for (const f of action.extra_fields) {
    if (!(f.key in initial)) {
      initial[f.key] = f.field_type === "bool" ? "false" : "";
    }
  }

  return initial;
}

function getSuggestionHints(payload: ReviewQueueItem["payload"]) {
  const companySuggestions: string[] = [];
  const groupSuggestions: string[] = [];

  const sig = payload.signature as { company_name?: string | null } | undefined;
  if (sig?.company_name && !companySuggestions.includes(sig.company_name)) {
    companySuggestions.push(sig.company_name);
  }

  if (payload.details && Array.isArray(payload.details)) {
    for (const d of payload.details) {
      const val = (d.value ?? "").trim();
      if (!val || val === "-" || val.startsWith("(none")) continue;

      if ((d.key === "suggested_company" || d.label === "Suggested company") && !companySuggestions.includes(val)) {
        companySuggestions.push(val);
      }
      if ((d.key === "sig_company" || d.label === "Company (from signature)") && !companySuggestions.includes(val)) {
        companySuggestions.push(val);
      }
      if (d.key === "suggested_groups" || d.label === "Suggested groups") {
        val
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .forEach((g) => {
            if (!groupSuggestions.includes(g)) groupSuggestions.push(g);
          });
      }
      if (d.key === "newsletter_group" || d.label === "Newsletter group for this database") {
        if (!val.startsWith("(none") && !groupSuggestions.includes(val)) {
          groupSuggestions.push(val);
        }
      }
    }
  }

  const rawSuggestedGroups = payload.suggested_groups as string[] | undefined;
  if (rawSuggestedGroups && Array.isArray(rawSuggestedGroups)) {
    rawSuggestedGroups.forEach((g) => {
      if (!groupSuggestions.includes(g)) groupSuggestions.push(g);
    });
  }

  return { companySuggestions, groupSuggestions };
}

/**
 * Renders ANY review-queue item, for any automation, from data alone - it
 * never hardcodes "bounce" or "departure" anywhere. What it draws comes
 * entirely from the item's payload (see registry.py's payload contract)
 * and the kind's registered actions (label, style, what input each one
 * needs). A brand-new automation shows up here correctly the moment it
 * registers a kind on the backend - no frontend change required.
 */
export function ReviewItemCard({ item, kind }: { item: ReviewQueueItem; kind: ReviewKind }) {
  const [expandedAction, setExpandedAction] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [contact, setContact] = useState<{ id: string; label: string } | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [chosenEntityId, setChosenEntityId] = useState<string | null>(null);
  const [confirmingDestructive, setConfirmingDestructive] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [justResolvedLabel, setJustResolvedLabel] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [draftDialogOpen, setDraftDialogOpen] = useState(false);

  const { payload } = item;
  const style = styleForKind(kind.kind);
  const Icon = style.icon;

  useEffect(() => {
    if (!justResolvedLabel) return;
    const t = setTimeout(() => setCollapsed(true), 900);
    return () => clearTimeout(t);
  }, [justResolvedLabel]);

  function resetInputs(action?: ReviewAction) {
    setNote("");
    setContact(null);
    if (action) {
      setFields(computeInitialFields(payload, action));
    } else {
      setFields({ ...(payload.prefill ?? {}) });
    }
    setChosenEntityId(null);
  }

  function actionNeedsInput(action: ReviewAction): boolean {
    return (
      action.requires_note ||
      action.requires_contact_picker ||
      action.requires_related_entity_choice ||
      action.extra_fields.length > 0
    );
  }

  function canSubmit(action: ReviewAction): boolean {
    if (action.requires_note && !note.trim()) return false;
    if (action.requires_contact_picker && !contact) return false;
    if (action.requires_related_entity_choice && !chosenEntityId) return false;
    for (const f of action.extra_fields) {
      if (f.required && !(fields[f.key] ?? "").trim()) return false;
    }
    return true;
  }

  function submit(action: ReviewAction) {
    startTransition(async () => {
      try {
        await resolveReviewItem(item.id, action.id, {
          note: note.trim() || undefined,
          contact_id: contact?.id,
          fields,
          chosen_entity_id: chosenEntityId ?? undefined,
        });
        toast.success(`${action.label} — done`);
        setJustResolvedLabel(action.label);
        setExpandedAction(null);
        setConfirmingDestructive(null);
        resetInputs();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't complete this action");
      }
    });
  }

  function handleActionClick(action: ReviewAction) {
    if (DRAFT_REVIEW_ACTIONS[kind.kind] === action.id) {
      setDraftDialogOpen(true);
      return;
    }
    if (actionNeedsInput(action)) {
      const isOpening = expandedAction !== action.id;
      setExpandedAction(isOpening ? action.id : null);
      if (isOpening) {
        resetInputs(action);
      }
      return;
    }
    if (action.confirm_message) {
      setConfirmingDestructive(action.id);
      return;
    }
    submit(action);
  }

  if (collapsed) return null;

  if (justResolvedLabel) {
    return (
      <Card className="editorial-card overflow-hidden border-emerald-500/30 bg-emerald-500/5">
        <CardContent className="flex items-center gap-3 p-5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-600">
            <CheckCircle2 className="size-5" />
          </span>
          <div>
            <p className="text-sm font-bold text-foreground">{justResolvedLabel}</p>
            <p className="text-xs text-muted-foreground">Recorded on the CRM. Moving to the next item…</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const confidence = payload.confidence != null ? confidenceTone(payload.confidence) : null;

  return (
    <Card className={`editorial-card overflow-hidden transition-shadow hover:shadow-xs`}>
      <div className={`masthead-rule w-full ${style.accent}`} />
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <span
            className={`mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg border ${style.chipBg} ${style.color}`}
          >
            <Icon className="size-4" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
                {kind.label}
              </span>
              {confidence && (
                <span className={`flex items-center gap-1 text-[11px] font-semibold ${confidence.text}`}>
                  <span className={`size-1.5 rounded-full ${confidence.dot}`} />
                  {Math.round(payload.confidence! * 100)}% confidence
                </span>
              )}
              <span className="text-[11px] text-muted-foreground">{timeAgo(item.created_at)}</span>
            </div>
            <p className="mt-1 text-sm font-bold text-foreground">{payload.summary || "Needs review"}</p>
            {item.entity_type && item.entity_id && (
              <Link
                href={`/${item.entity_type === "contact" ? "contacts" : "companies"}/${item.entity_id}`}
                className="mt-0.5 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
              >
                View {item.entity_type} record
                <ExternalLink className="size-3" />
              </Link>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 text-sm">
        {payload.details && payload.details.length > 0 && (
          <dl className="grid grid-cols-1 gap-x-4 gap-y-1.5 rounded-lg bg-muted/30 p-3 text-xs sm:grid-cols-2">
            {payload.details.map((d, i) => (
              <div key={d.key ?? i} className="flex items-baseline justify-between gap-2 sm:justify-start">
                <dt className="shrink-0 text-muted-foreground">{d.label}</dt>
                {/* No truncation - a long extracted summary getting cut to
                    "...the eNewsletter Banner place…" hides exactly the
                    detail (a figure, a date) the rep needs to judge the
                    signal, which defeats the point of showing it. */}
                <dd className="whitespace-pre-wrap break-words text-right font-medium text-foreground sm:text-left">{d.value}</dd>
              </div>
            ))}
          </dl>
        )}

        {payload.related_entities && payload.related_entities.length > 0 && (
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground">
              <Users className="size-3.5" />
              Every record this affects ({payload.related_entities.length})
            </div>
            <div className="flex flex-wrap gap-1.5">
              {payload.related_entities.map((e) => (
                <Link key={e.id} href={`/${e.type === "contact" ? "contacts" : "companies"}/${e.id}`}>
                  <Badge variant="secondary" className="cursor-pointer text-[11px] hover:bg-secondary/70">
                    {e.label}
                  </Badge>
                </Link>
              ))}
            </div>
          </div>
        )}

        {payload.candidate?.contact_id && (
          <div className="flex items-center gap-2.5 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
              <Users className="size-3.5" />
            </span>
            <div className="min-w-0 flex-1">
              <span className="text-muted-foreground">Researched candidate: </span>
              <Link
                href={`/contacts/${payload.candidate.contact_id}`}
                className="font-semibold text-primary hover:underline"
              >
                {payload.candidate.label || "View candidate"}
              </Link>
              {payload.candidate.source && (
                <span className="text-muted-foreground"> · via {payload.candidate.source}</span>
              )}
            </div>
          </div>
        )}

        {payload.original_text && (
          <details className="group rounded-lg border border-border/70">
            <summary className="flex cursor-pointer list-none items-center gap-1.5 px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
              <ChevronDown className="size-3.5 transition-transform group-open:hidden" />
              <ChevronUp className="hidden size-3.5 transition-transform group-open:block" />
              {/* "Drafted note" for a kind that writes an AI-drafted note/
                  email (see DRAFT_REVIEW_ACTIONS above) - "Original
                  message" would wrongly imply this is the source email,
                  when it's actually the generated draft. Every other kind
                  really is showing the original source message, so keeps
                  that accurate label. */}
              {DRAFT_REVIEW_ACTIONS[kind.kind] ? "Drafted note" : "Original message"}
            </summary>
            <p className="whitespace-pre-wrap border-t border-border/70 bg-muted/20 px-3 py-2.5 text-xs text-muted-foreground">
              {cleanNoteBody(payload.original_text)}
            </p>
          </details>
        )}

        {/* Separate from "Original message" above (that's the drafted
            action for this kind, not source material) - the actual email
            excerpt a signal was pulled from, so a rep can judge the AI's
            summary against the real context before acting on it. */}
        {payload.source_context && (
          <details className="group rounded-lg border border-border/70">
            <summary className="flex cursor-pointer list-none items-center gap-1.5 px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
              <ChevronDown className="size-3.5 transition-transform group-open:hidden" />
              <ChevronUp className="hidden size-3.5 transition-transform group-open:block" />
              Original email excerpt
            </summary>
            <p className="whitespace-pre-wrap border-t border-border/70 bg-muted/20 px-3 py-2.5 text-xs text-muted-foreground">
              {cleanNoteBody(payload.source_context)}
            </p>
          </details>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2 border-t border-border/70 pt-3">
          {kind.actions.map((action) => (
            <Button
              key={action.id}
              size="sm"
              variant={action.style === "primary" ? "default" : "outline"}
              className={STYLE_CLASSES[action.style]}
              disabled={pending}
              onClick={() => handleActionClick(action)}
            >
              {action.style === "destructive" && <AlertTriangle className="size-3.5" />}
              {action.label}
            </Button>
          ))}
        </div>

        {/* Inline confirm for a no-input destructive/high-stakes action */}
        {confirmingDestructive && (
          <div className="flex items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs">
            <span className="flex items-start gap-1.5">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-destructive" />
              {kind.actions.find((a) => a.id === confirmingDestructive)?.confirm_message}
            </span>
            <div className="flex shrink-0 gap-2">
              <Button size="sm" variant="outline" onClick={() => setConfirmingDestructive(null)}>
                <X className="size-3.5" />
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={pending}
                onClick={() => submit(kind.actions.find((a) => a.id === confirmingDestructive)!)}
              >
                <Check className="size-3.5" />
                {pending ? "Working…" : "Confirm"}
              </Button>
            </div>
          </div>
        )}

        {/* Inline input form for an action that needs a note/contact/fields */}
        {expandedAction && (
          <ExpandedActionForm
            action={kind.actions.find((a) => a.id === expandedAction)!}
            payload={payload}
            note={note}
            setNote={setNote}
            contact={contact}
            setContact={setContact}
            fields={fields}
            setFields={setFields}
            relatedEntities={payload.related_entities ?? []}
            chosenEntityId={chosenEntityId}
            setChosenEntityId={setChosenEntityId}
            pending={pending}
            canSubmit={canSubmit(kind.actions.find((a) => a.id === expandedAction)!)}
            onCancel={() => {
              setExpandedAction(null);
              resetInputs();
            }}
            onSubmit={() => submit(kind.actions.find((a) => a.id === expandedAction)!)}
          />
        )}

        {DRAFT_REVIEW_ACTIONS[kind.kind] && (
          <DraftReviewDialog
            open={draftDialogOpen}
            onOpenChange={setDraftDialogOpen}
            itemId={item.id}
            actionId={DRAFT_REVIEW_ACTIONS[kind.kind]}
            actionLabel={kind.actions.find((a) => a.id === DRAFT_REVIEW_ACTIONS[kind.kind])?.label ?? "Approve"}
            initialDraft={payload.original_text ?? ""}
            onApproved={(label) => {
              toast.success(`${label} — done`);
              setJustResolvedLabel(label);
            }}
          />
        )}
      </CardContent>
    </Card>
  );
}

function CompanyAutocomplete({
  label,
  required,
  placeholder,
  value,
  onChange,
  suggestions,
  initialCompanyId,
}: {
  label: string;
  required?: boolean;
  placeholder?: string;
  value: string;
  onChange: (name: string, companyId?: string | null) => void;
  suggestions: string[];
  initialCompanyId?: string | null;
}) {
  const [query, setQuery] = useState(value);
  const [options, setOptions] = useState<CompanyListItem[]>([]);
  const [open, setOpen] = useState(false);
  const [companyId, setCompanyId] = useState<string | null>(initialCompanyId ?? null);
  const [rect, setRect] = useState<{ top: number; left: number; width: number } | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const inputWrapRef = useRef<HTMLDivElement>(null);

  // Sync external value changes (e.g. from suggestions or reset)
  useEffect(() => {
    setQuery(value);
  }, [value]);

  // Attempt to resolve companyId if we have a company name but no ID yet
  useEffect(() => {
    if (!value.trim() || companyId) return;
    let active = true;
    searchCompanies(value.trim()).then((matches) => {
      if (!active) return;
      const exact = matches.find((m) => m.name.toLowerCase() === value.trim().toLowerCase());
      if (exact) {
        setCompanyId(exact.id);
      }
    });
    return () => {
      active = false;
    };
  }, [value, companyId]);

  // Debounced search when user types
  useEffect(() => {
    if (!query.trim()) {
      setOptions([]);
      return;
    }
    const id = setTimeout(() => {
      searchCompanies(query.trim()).then((res) => {
        setOptions(res);
      });
    }, 180);
    return () => clearTimeout(id);
  }, [query]);

  // Click outside to close floating dropdown
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      if (boxRef.current?.contains(target)) return;
      if (inputWrapRef.current?.contains(target)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  // Update floating rect to avoid overflow clipping
  useLayoutEffect(() => {
    if (!open) return;
    function updateRect() {
      const el = inputWrapRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      setRect({ top: r.bottom + window.scrollY + 4, left: r.left + window.scrollX, width: r.width });
    }
    updateRect();
    window.addEventListener("scroll", updateRect, true);
    window.addEventListener("resize", updateRect);
    return () => {
      window.removeEventListener("scroll", updateRect, true);
      window.removeEventListener("resize", updateRect);
    };
  }, [open]);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-xs">
          {label}
          {required && <span className="text-destructive"> *</span>}
        </Label>
        <div className="flex items-center gap-2">
          {companyId && (
            <Link
              href={`/companies/${companyId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary hover:bg-primary/20 transition-colors"
              title="Open this company's profile in a new tab"
            >
              <Building2 className="size-3" />
              View company
              <ExternalLink className="size-2.5" />
            </Link>
          )}
          {value && (
            <button
              type="button"
              onClick={() => {
                onChange("", null);
                setCompanyId(null);
                setQuery("");
              }}
              className="text-[11px] font-medium text-muted-foreground hover:text-destructive transition-colors"
            >
              Remove company
            </button>
          )}
        </div>
      </div>

      <div ref={inputWrapRef} className="relative">
        <Input
          className="h-8 pr-7 text-sm"
          placeholder={placeholder || "Type to search companies…"}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            onChange(e.target.value, null);
            setCompanyId(null);
            setOpen(true);
          }}
          onFocus={() => {
            if (query.trim()) setOpen(true);
          }}
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              onChange("", null);
              setCompanyId(null);
              setOptions([]);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            title="Clear"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>

      {open && rect && (options.length > 0 || query.trim().length >= 2) &&
        createPortal(
          <div
            ref={boxRef}
            style={{ position: "absolute", top: rect.top, left: rect.left, width: rect.width }}
            className="z-50 max-h-56 overflow-y-auto rounded-md border border-border bg-popover text-popover-foreground shadow-lg"
          >
            {options.length > 0 ? (
              options.map((comp) => (
                <button
                  key={comp.id}
                  type="button"
                  className="flex w-full items-center justify-between border-b border-border/40 px-3 py-2 text-left text-xs transition-colors hover:bg-accent hover:text-accent-foreground last:border-0"
                  onClick={() => {
                    onChange(comp.name, comp.id);
                    setQuery(comp.name);
                    setCompanyId(comp.id);
                    setOpen(false);
                  }}
                >
                  <div className="flex flex-col">
                    <span className="font-semibold text-foreground">{comp.name}</span>
                    <span className="text-[10.5px] text-muted-foreground">
                      {[comp.industry, comp.category].filter(Boolean).join(" · ") || "Existing company"}
                    </span>
                  </div>
                  {comp.contact_count > 0 && (
                    <span className="text-[10.5px] text-muted-foreground shrink-0">
                      {comp.contact_count} {comp.contact_count === 1 ? "contact" : "contacts"}
                    </span>
                  )}
                </button>
              ))
            ) : (
              <div className="px-3 py-2 text-xs text-muted-foreground italic">
                No matching companies found — will create new company &ldquo;{query}&rdquo;
              </div>
            )}
          </div>,
          document.body
        )}

      {suggestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span className="text-[10.5px] text-muted-foreground">Suggestions:</span>
          {suggestions.map((comp) => (
            <button
              key={comp}
              type="button"
              onClick={() => {
                onChange(comp);
                setQuery(comp);
                setCompanyId(null);
              }}
              className={`rounded border px-2 py-0.5 text-[11px] transition-colors ${
                value === comp
                  ? "border-primary bg-primary/10 font-semibold text-primary"
                  : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {comp}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function GroupsAutocomplete({
  label,
  required,
  placeholder,
  value,
  onChange,
  suggestions,
}: {
  label: string;
  required?: boolean;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  suggestions: string[];
}) {
  const [options, setOptions] = useState<GroupListItem[]>([]);
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState<{ top: number; left: number; width: number } | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const inputWrapRef = useRef<HTMLDivElement>(null);

  // Extract the active query token being typed (after the last comma)
  const lastToken = (value.split(",").pop() || "").trim();

  // Debounced search for groups
  useEffect(() => {
    if (!lastToken) {
      setOptions([]);
      return;
    }
    const id = setTimeout(() => {
      searchGroups(lastToken).then(setOptions);
    }, 180);
    return () => clearTimeout(id);
  }, [lastToken]);

  // Click outside listener
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      if (boxRef.current?.contains(target)) return;
      if (inputWrapRef.current?.contains(target)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  // Update floating rect
  useLayoutEffect(() => {
    if (!open) return;
    function updateRect() {
      const el = inputWrapRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      setRect({ top: r.bottom + window.scrollY + 4, left: r.left + window.scrollX, width: r.width });
    }
    updateRect();
    window.addEventListener("scroll", updateRect, true);
    window.addEventListener("resize", updateRect);
    return () => {
      window.removeEventListener("scroll", updateRect, true);
      window.removeEventListener("resize", updateRect);
    };
  }, [open]);

  const currentGroups = value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  function selectGroup(groupName: string) {
    const parts = value.split(",");
    parts.pop(); // remove incomplete token
    const cleanPrefix = parts.map((s) => s.trim()).filter(Boolean);
    if (!cleanPrefix.includes(groupName)) {
      cleanPrefix.push(groupName);
    }
    onChange(cleanPrefix.join(", ") + ", ");
    setOpen(false);
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-xs">
          {label}
          {required && <span className="text-destructive"> *</span>}
        </Label>
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className="text-[11px] font-medium text-muted-foreground hover:text-destructive transition-colors"
          >
            Clear groups
          </button>
        )}
      </div>

      <div ref={inputWrapRef} className="relative">
        <Input
          className="h-8 pr-7 text-sm"
          placeholder={placeholder || "Type to search and add groups…"}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (lastToken) setOpen(true);
          }}
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            title="Clear"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>

      {open && rect && options.length > 0 &&
        createPortal(
          <div
            ref={boxRef}
            style={{ position: "absolute", top: rect.top, left: rect.left, width: rect.width }}
            className="z-50 max-h-56 overflow-y-auto rounded-md border border-border bg-popover text-popover-foreground shadow-lg"
          >
            {options.map((grp) => (
              <button
                key={grp.id}
                type="button"
                className="flex w-full items-center justify-between border-b border-border/40 px-3 py-2 text-left text-xs transition-colors hover:bg-accent hover:text-accent-foreground last:border-0"
                onClick={() => selectGroup(grp.name)}
              >
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">{grp.name}</span>
                  {grp.description && (
                    <span className="text-[10.5px] text-muted-foreground line-clamp-1">{grp.description}</span>
                  )}
                </div>
                {grp.member_count > 0 && (
                  <span className="text-[10.5px] text-muted-foreground shrink-0">
                    {grp.member_count} {grp.member_count === 1 ? "member" : "members"}
                  </span>
                )}
              </button>
            ))}
          </div>,
          document.body
        )}

      {suggestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span className="text-[10.5px] text-muted-foreground">Suggested groups:</span>
          {suggestions.map((grp) => {
            const isSelected = currentGroups.includes(grp);
            return (
              <button
                key={grp}
                type="button"
                onClick={() => {
                  let updated: string[];
                  if (isSelected) {
                    updated = currentGroups.filter((g) => g !== grp);
                  } else {
                    updated = [...currentGroups, grp];
                  }
                  onChange(updated.join(", "));
                }}
                className={`rounded border px-2 py-0.5 text-[11px] transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/10 font-semibold text-primary"
                    : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground"
                }`}
              >
                {isSelected ? `✓ ${grp}` : `+ ${grp}`}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ExpandedActionForm({
  action,
  payload,
  note,
  setNote,
  contact,
  setContact,
  fields,
  setFields,
  relatedEntities,
  chosenEntityId,
  setChosenEntityId,
  pending,
  canSubmit,
  onCancel,
  onSubmit,
}: {
  action: ReviewAction;
  payload: ReviewQueueItem["payload"];
  note: string;
  setNote: (v: string) => void;
  contact: { id: string; label: string } | null;
  setContact: (v: { id: string; label: string } | null) => void;
  fields: Record<string, string>;
  setFields: (v: Record<string, string>) => void;
  relatedEntities: { type: "contact" | "company"; id: string; label: string }[];
  chosenEntityId: string | null;
  setChosenEntityId: (v: string | null) => void;
  pending: boolean;
  canSubmit: boolean;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  const choiceOptions = relatedEntities.filter((e) => e.type === "contact");
  const { companySuggestions, groupSuggestions } = getSuggestionHints(payload);
  const initialCompanyId =
    (payload.matched_entity_type === "company" ? (payload.matched_entity_id as string) : null) ||
    (payload.company_id as string) ||
    (payload.suggested_company_id as string) ||
    (relatedEntities.find((e) => e.type === "company")?.id ?? null);

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-primary/30 bg-primary/5 p-3.5">
      <span className="text-xs font-bold text-foreground">{action.label}</span>
      {action.confirm_message && (
        <span className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600" />
          {action.confirm_message}
        </span>
      )}

      {action.requires_related_entity_choice && (
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs">Which one do you want to keep?</Label>
          <div className="flex flex-col gap-1.5">
            {choiceOptions.map((e) => (
              <div
                key={e.id}
                className={`flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                  chosenEntityId === e.id
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border bg-background text-muted-foreground hover:border-primary/40"
                }`}
              >
                <button
                  type="button"
                  onClick={() => setChosenEntityId(e.id)}
                  className="flex-1 text-left"
                >
                  {e.label}
                </button>
                <Link
                  href={`/contacts/${e.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Open this contact's full details in a new tab - useful when two contacts share the same name"
                  className="flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"
                  onClick={(ev) => ev.stopPropagation()}
                >
                  <ExternalLink className="size-3" />
                  View
                </Link>
                {chosenEntityId === e.id && (
                  <span className="flex shrink-0 items-center gap-1 text-[11px] font-bold text-primary">
                    <Check className="size-3.5" />
                    Keep this one
                  </span>
                )}
              </div>
            ))}
          </div>
          {choiceOptions.length > 0 && !chosenEntityId && (
            <span className="text-[11px] text-muted-foreground">
              The other record will be retired (kept, just marked merged - never deleted).
            </span>
          )}
        </div>
      )}

      {action.requires_contact_picker && (
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs">Contact</Label>
          <EntityPicker
            label="contact"
            placeholder="Search contacts by name or email…"
            search={async (q) =>
              (await searchContacts(q)).map((c) => ({
                id: c.id,
                label: c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "(no name)",
                sublabel: c.company_name,
              }))
            }
            value={contact}
            onChange={setContact}
            viewHref={(id) => `/contacts/${id}`}
          />
        </div>
      )}

      {action.extra_fields.map((f) => {
        if (f.field_type === "bool") {
          return (
            <label key={f.key} className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                className="size-3.5 rounded border-border"
                checked={fields[f.key] === "true"}
                onChange={(e) => setFields({ ...fields, [f.key]: e.target.checked ? "true" : "false" })}
              />
              {f.label}
            </label>
          );
        }

        if (f.key === "company_name") {
          return (
            <CompanyAutocomplete
              key={f.key}
              label={f.label}
              required={f.required}
              placeholder={f.placeholder}
              value={fields[f.key] ?? ""}
              onChange={(name) => setFields({ ...fields, [f.key]: name })}
              suggestions={companySuggestions}
              initialCompanyId={initialCompanyId}
            />
          );
        }

        if (f.key === "groups") {
          return (
            <GroupsAutocomplete
              key={f.key}
              label={f.label}
              required={f.required}
              placeholder={f.placeholder}
              value={fields[f.key] ?? ""}
              onChange={(val) => setFields({ ...fields, [f.key]: val })}
              suggestions={groupSuggestions}
            />
          );
        }

        if (f.key === "source_db") {
          // Only relevant when this item came in on a genuinely shared
          // inbox (payload.source_db === "*") - a normal per-title
          // mailbox already knows its own database, so this field is
          // silently skipped rather than shown empty/pre-filled and
          // confusing every other item of this kind.
          if (payload.source_db !== "*") return null;
          return (
            <div key={f.key} className="flex flex-col gap-1.5">
              <Label className="text-xs">Which BMI title does this belong to?</Label>
              <p className="text-[11px] text-muted-foreground">
                This came in on a shared inbox, not one tied to a single title - pick which database this contact belongs to.
              </p>
              <div className="flex flex-wrap items-center gap-1.5">
                {["prospects", "onboard", "sellingtravel"].map((dbName) => (
                  <button
                    key={dbName}
                    type="button"
                    onClick={() => setFields({ ...fields, [f.key]: dbName })}
                    className={`rounded border px-2.5 py-1 text-xs transition-colors ${
                      fields[f.key] === dbName
                        ? "border-primary bg-primary/10 font-semibold text-primary"
                        : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground"
                    }`}
                  >
                    {dbName}
                  </button>
                ))}
              </div>
            </div>
          );
        }

        return (
          <div key={f.key} className="flex flex-col gap-1.5">
            <Label className="text-xs">
              {f.label}
              {f.required && <span className="text-destructive"> *</span>}
            </Label>
            <div className="relative">
              <Input
                className="h-8 pr-7 text-sm"
                placeholder={f.placeholder}
                value={fields[f.key] ?? ""}
                onChange={(e) => setFields({ ...fields, [f.key]: e.target.value })}
              />
              {fields[f.key] && (
                <button
                  type="button"
                  onClick={() => setFields({ ...fields, [f.key]: "" })}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  title="Clear"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </div>
          </div>
        );
      })}

      {action.requires_note && (
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs">Note</Label>
          <Textarea
            className="text-sm"
            rows={2}
            placeholder="Why, or any context worth keeping on the record…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
      )}

      <div className="flex justify-end gap-2">
        <Button size="sm" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button size="sm" disabled={pending || !canSubmit} onClick={onSubmit}>
          {pending ? "Working…" : `Confirm ${action.label.toLowerCase()}`}
        </Button>
      </div>
    </div>
  );
}
