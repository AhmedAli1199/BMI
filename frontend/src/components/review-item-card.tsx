"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { AlertTriangle, Check, CheckCircle2, ChevronDown, ChevronUp, ExternalLink, Users, X } from "lucide-react";
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
import { resolveReviewItem, searchContacts } from "@/lib/actions";
import type { ReviewAction, ReviewKind, ReviewQueueItem } from "@/lib/types";

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

  const { payload } = item;
  const style = styleForKind(kind.kind);
  const Icon = style.icon;

  useEffect(() => {
    if (!justResolvedLabel) return;
    // Brief success flash so an action feels acknowledged, then the card
    // folds itself away - not an instant pop, which reads as the click
    // "not registering" for a split second.
    const t = setTimeout(() => setCollapsed(true), 900);
    return () => clearTimeout(t);
  }, [justResolvedLabel]);

  function resetInputs() {
    setNote("");
    setContact(null);
    setFields({});
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
    if (actionNeedsInput(action)) {
      setExpandedAction(expandedAction === action.id ? null : action.id);
      resetInputs();
      return;
    }
    if (action.confirm_message) {
      setConfirmingDestructive(action.id);
      return;
    }
    submit(action);
  }

  // Removed from the list right after the success flash plays, rather than
  // instantly - see the useEffect above.
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
              Original message
            </summary>
            <p className="whitespace-pre-wrap border-t border-border/70 bg-muted/20 px-3 py-2.5 text-xs text-muted-foreground">
              {cleanNoteBody(payload.original_text)}
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
      </CardContent>
    </Card>
  );
}

function ExpandedActionForm({
  action,
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
          />
        </div>
      )}

      {action.extra_fields.map((f) =>
        f.field_type === "bool" ? (
          <label key={f.key} className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              className="size-3.5 rounded border-border"
              checked={fields[f.key] === "true"}
              onChange={(e) => setFields({ ...fields, [f.key]: e.target.checked ? "true" : "false" })}
            />
            {f.label}
          </label>
        ) : (
          <div key={f.key} className="flex flex-col gap-1.5">
            <Label className="text-xs">
              {f.label}
              {f.required && <span className="text-destructive"> *</span>}
            </Label>
            <Input
              className="h-8 text-sm"
              placeholder={f.placeholder}
              value={fields[f.key] ?? ""}
              onChange={(e) => setFields({ ...fields, [f.key]: e.target.value })}
            />
          </div>
        )
      )}

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
