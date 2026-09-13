"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { AlertTriangle, Check, ChevronDown, ChevronUp, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EntityPicker } from "@/components/entity-picker";
import { cleanNoteBody } from "@/lib/notes";
import { resolveReviewItem, searchContacts } from "@/lib/actions";
import type { ReviewAction, ReviewKind, ReviewQueueItem } from "@/lib/types";

const STYLE_CLASSES: Record<ReviewAction["style"], string> = {
  primary: "",
  secondary: "",
  destructive: "text-destructive hover:text-destructive border-destructive/40 hover:bg-destructive/10",
};

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
  const [confirmingDestructive, setConfirmingDestructive] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [resolved, setResolved] = useState(false);

  const { payload } = item;

  function resetInputs() {
    setNote("");
    setContact(null);
    setFields({});
  }

  function actionNeedsInput(action: ReviewAction): boolean {
    return action.requires_note || action.requires_contact_picker || action.extra_fields.length > 0;
  }

  function canSubmit(action: ReviewAction): boolean {
    if (action.requires_note && !note.trim()) return false;
    if (action.requires_contact_picker && !contact) return false;
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
        });
        toast.success(`${action.label} — done`);
        setResolved(true);
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

  if (resolved) return null; // Removed from the list the instant it's handled - no stale item lingering.

  return (
    <Card className="editorial-card">
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-[10px] font-medium">
              {kind.label}
            </Badge>
            {payload.confidence != null && (
              <span className="text-[11px] text-muted-foreground">
                {Math.round(payload.confidence * 100)}% confidence
              </span>
            )}
            <span className="text-[11px] text-muted-foreground">
              {new Date(item.created_at).toLocaleString()}
            </span>
          </div>
          <p className="mt-1.5 text-sm font-semibold text-foreground">
            {payload.summary || "Needs review"}
          </p>
          {item.entity_type && item.entity_id && (
            <Link
              href={`/${item.entity_type === "contact" ? "contacts" : "companies"}/${item.entity_id}`}
              className="mt-0.5 inline-block text-xs text-primary hover:underline"
            >
              View {item.entity_type} record &rarr;
            </Link>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 text-sm">
        {payload.details && payload.details.length > 0 && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            {payload.details.map((d, i) => (
              <div key={d.key ?? i} className="contents">
                <dt className="text-muted-foreground">{d.label}</dt>
                <dd className="text-foreground">{d.value}</dd>
              </div>
            ))}
          </dl>
        )}

        {payload.related_entities && payload.related_entities.length > 0 && (
          <div className="rounded-md border border-border/70 bg-muted/30 p-2.5">
            <div className="mb-1 text-[11px] font-semibold text-muted-foreground">
              Every record this affects ({payload.related_entities.length})
            </div>
            <div className="flex flex-wrap gap-1.5">
              {payload.related_entities.map((e) => (
                <Link key={e.id} href={`/${e.type === "contact" ? "contacts" : "companies"}/${e.id}`}>
                  <Badge variant="secondary" className="cursor-pointer text-[11px]">
                    {e.label}
                  </Badge>
                </Link>
              ))}
            </div>
          </div>
        )}

        {payload.candidate?.contact_id && (
          <div className="rounded-md border border-primary/20 bg-primary/5 p-2.5 text-xs">
            <span className="text-muted-foreground">Researched candidate: </span>
            <Link href={`/contacts/${payload.candidate.contact_id}`} className="font-semibold text-primary hover:underline">
              {payload.candidate.label || "View candidate"}
            </Link>
            {payload.candidate.source && (
              <span className="text-muted-foreground"> · via {payload.candidate.source}</span>
            )}
          </div>
        )}

        {payload.original_text && (
          <details className="group rounded-md border border-border/70">
            <summary className="flex cursor-pointer list-none items-center gap-1.5 px-2.5 py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
              <ChevronDown className="size-3.5 transition-transform group-open:hidden" />
              <ChevronUp className="hidden size-3.5 transition-transform group-open:block" />
              Original message
            </summary>
            <p className="whitespace-pre-wrap border-t border-border/70 bg-muted/20 px-2.5 py-2 text-xs text-muted-foreground">
              {cleanNoteBody(payload.original_text)}
            </p>
          </details>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2 pt-1">
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
          <div className="flex items-center justify-between gap-3 rounded-md border border-destructive/30 bg-destructive/5 p-2.5 text-xs">
            <span>{kind.actions.find((a) => a.id === confirmingDestructive)?.confirm_message}</span>
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
  pending: boolean;
  canSubmit: boolean;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-primary/30 bg-primary/5 p-3">
      <span className="text-xs font-semibold text-foreground">{action.label}</span>
      {action.confirm_message && (
        <span className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600" />
          {action.confirm_message}
        </span>
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

      {action.extra_fields.map((f) => (
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
      ))}

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
