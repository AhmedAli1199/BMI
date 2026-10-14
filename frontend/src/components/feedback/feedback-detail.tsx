"use client";

import { useEffect, useState, useTransition } from "react";
import { Code2, ExternalLink, Loader2, MapPin, Pencil, RefreshCw, ThumbsUp, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { FEEDBACK_KINDS, FEEDBACK_STATUSES, feedbackImageUrl, type FeedbackItem, type FeedbackKind, type FeedbackStatus } from "@/lib/feedback-types";
import { commentOnFeedback, deleteFeedback, editFeedback, getFeedback, retryFeedbackGithub, setFeedbackStatus, toggleMeToo } from "@/lib/feedback-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { fmtWhen, statusTone } from "@/components/feedback/feedback-ui";

const selectCls = "h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

/** One piece of feedback in full: screenshots, what was pointed at, votes, comments and where it's up to. */
export function FeedbackDetail({ id, onClose, onChange, onDeleted }: {
  id: string | null; onClose: () => void; onChange: (f: FeedbackItem) => void; onDeleted: (id: string) => void;
}) {
  const [f, setF] = useState<FeedbackItem | null>(null);
  const [pending, start] = useTransition();
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<FeedbackStatus>("new");
  const [note, setNote] = useState("");
  const [editing, setEditing] = useState<{ kind: FeedbackKind; message: string } | null>(null);

  useEffect(() => {
    if (!id) return;
    let live = true;
    getFeedback(id).then((x) => {
      if (!live) return;
      setF(x); setStatus(x.status); setNote(x.status_note ?? ""); setEditing(null); setComment("");
    }).catch((e) => { if (live) { toast.error(friendlyError(e, "Couldn't open that feedback")); onClose(); } });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const run = (fn: () => Promise<FeedbackItem>, ok?: string) => start(async () => {
    try { const x = await fn(); setF(x); onChange(x); if (ok) toast.success(ok); }
    catch (e) { toast.error(friendlyError(e, "Couldn't save that")); }
  });

  const shown = f && f.id === id ? f : null;

  return (
    <Sheet open={!!id} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-2xl">
        <SheetHeader className="border-b border-border/70">
          <SheetTitle>{shown ? `Feedback #${shown.number}` : "Feedback"}</SheetTitle>
          <SheetDescription>{shown ? `${shown.kind_label} · from ${shown.user_name} · ${fmtWhen(shown.created_at)}` : "Opening…"}</SheetDescription>
        </SheetHeader>
        {!shown ? (
          <div className="flex justify-center p-10"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>
        ) : (
          <div className="flex flex-col gap-5 p-4">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className={`rounded-full px-2.5 py-0.5 font-medium ${statusTone(shown.status)}`}>{shown.status_label}</span>
              {shown.status_by && <span className="text-muted-foreground">by {shown.status_by} {fmtWhen(shown.status_at)}</span>}
              <a href={shown.page_path} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 font-medium text-primary hover:underline">
                Open the page <ExternalLink className="size-3" aria-hidden="true" />
              </a>
              {shown.elements.some((e) => e.selector) && (
                <a href={`${shown.page_path}?feedback_pin=${shown.id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">
                  Show me on the page <MapPin className="size-3" aria-hidden="true" />
                </a>
              )}
              {shown.github_url && (
                <a href={shown.github_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">
                  GitHub issue <ExternalLink className="size-3" aria-hidden="true" />
                </a>
              )}
            </div>
            {shown.status_note && <p className="rounded-lg bg-muted/50 p-2.5 text-sm"><span className="font-semibold">Note: </span>{shown.status_note}</p>}

            <section>
              {editing ? (
                <div className="flex flex-col gap-2">
                  <select className={selectCls} value={editing.kind} onChange={(e) => setEditing({ ...editing, kind: e.target.value as FeedbackKind })} aria-label="Kind">
                    {FEEDBACK_KINDS.map((k) => <option key={k.kind} value={k.kind}>{k.label}</option>)}
                  </select>
                  <Textarea rows={4} value={editing.message} onChange={(e) => setEditing({ ...editing, message: e.target.value })} aria-label="Feedback" />
                  <div className="flex gap-2">
                    <Button size="sm" disabled={pending} onClick={() => { run(() => editFeedback(shown.id, editing), "Saved"); setEditing(null); }}>Save</Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-2">
                  <p className="flex-1 whitespace-pre-wrap text-sm">{shown.message || <span className="text-muted-foreground">No words, see what they pointed at.</span>}</p>
                  {shown.can_edit && <Button size="icon-sm" variant="ghost" aria-label="Change it" onClick={() => setEditing({ kind: shown.kind, message: shown.message })}><Pencil className="size-3.5" /></Button>}
                </div>
              )}
              <p className="mt-1.5 text-xs text-muted-foreground">On <a href={shown.page_path} target="_blank" rel="noreferrer" className="hover:underline">{shown.page_title || shown.page_path}</a></p>
            </section>

            {shown.elements.length > 0 && (
              <section className="flex flex-col gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">What they pointed at</h3>
                {shown.elements.map((e, i) => (
                  <div key={i} className="rounded-lg border border-border/70 p-2.5 text-sm">
                    <p className="flex items-center gap-1.5 font-medium"><MapPin className="size-3.5 text-primary" aria-hidden="true" />{e.label}</p>
                    {e.heading && <p className="text-xs text-muted-foreground">under “{e.heading}”</p>}
                    {e.source && e.source.length > 0 && (
                      <p className="mt-1 flex items-start gap-1 font-mono text-[11px] text-muted-foreground"><Code2 className="mt-0.5 size-3 shrink-0" aria-label="Where it is in the code" />{e.source.join("  ›  ")}</p>
                    )}
                  </div>
                ))}
              </section>
            )}

            {shown.images.length > 0 && (
              <section className="flex flex-col gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Screenshots</h3>
                {shown.images.map((img) => (
                  <a key={img.id} href={feedbackImageUrl(img.id)} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-border/70 bg-muted">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={feedbackImageUrl(img.id)} alt={img.label ?? "Screenshot"} className="w-full" />
                    {img.label && <p className="border-t border-border/70 bg-card px-2 py-1 text-xs text-muted-foreground">{img.label}</p>}
                  </a>
                ))}
              </section>
            )}

            <section className="flex flex-wrap items-center gap-2">
              {!shown.mine && (
                <Button size="sm" variant={shown.me_too_mine ? "default" : "outline"} className="gap-1.5" disabled={pending} onClick={() => run(() => toggleMeToo(shown.id))}>
                  <ThumbsUp className="size-3.5" /> {shown.me_too_mine ? "You said me too" : "Me too"}
                </Button>
              )}
              <span className="text-xs text-muted-foreground">
                {shown.me_too.length ? `Also: ${shown.me_too.join(", ")}` : "Nobody else has added their vote yet."}
              </span>
            </section>

            {shown.can_set_status && (
              <section className="flex flex-col gap-2 rounded-lg border border-border/70 bg-muted/20 p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Where it&apos;s up to</h3>
                <div className="flex flex-wrap gap-1">
                  {FEEDBACK_STATUSES.map((s) => (
                    <button key={s.status} type="button" onClick={() => setStatus(s.status)}
                      className={`rounded-full px-3 py-1 text-xs font-medium ${status === s.status ? "bg-foreground text-background" : "bg-muted text-muted-foreground hover:text-foreground"}`}>{s.label}</button>
                  ))}
                </div>
                <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} className="text-sm" placeholder="A note for them (optional), e.g. what was changed" aria-label="Note" />
                <Button size="sm" className="self-start" disabled={pending || (status === shown.status && note === (shown.status_note ?? ""))}
                  onClick={() => run(() => setFeedbackStatus(shown.id, status, note || null), "Saved. They'll get a notification.")}>Save</Button>
                {shown.github_error && (
                  <p className="flex items-center gap-2 text-xs text-[var(--warn)]">{shown.github_error}
                    <Button size="sm" variant="outline" className="h-7 gap-1 px-2 text-xs" disabled={pending} onClick={() => run(() => retryFeedbackGithub(shown.id), "Sent to GitHub")}><RefreshCw className="size-3" /> Try again</Button>
                  </p>
                )}
              </section>
            )}

            {shown.context && Object.keys(shown.context).length > 0 && (
              <details className="rounded-lg border border-border/70 p-3 text-xs">
                <summary className="cursor-pointer font-semibold text-muted-foreground">Browser and recent errors</summary>
                <dl className="mt-2 grid grid-cols-[8rem_1fr] gap-x-2 gap-y-1">
                  {(["browser", "viewport", "screen", "zoom", "theme", "time_zone"] as const).map((k) => shown.context?.[k] ? (
                    <div key={k} className="contents"><dt className="text-muted-foreground">{k.replace("_", " ")}</dt><dd>{shown.context[k]}</dd></div>
                  ) : null)}
                </dl>
                {(shown.context.errors?.length ?? 0) > 0 ? (
                  <ul className="mt-2 flex flex-col gap-1 font-mono text-[11px]">
                    {shown.context.errors!.map((e, i) => <li key={i} className="break-words"><span className="text-muted-foreground">{e.at} {e.kind}:</span> {e.message}</li>)}
                  </ul>
                ) : <p className="mt-2 text-muted-foreground">No errors in the few minutes before.</p>}
              </details>
            )}

            <section className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Comments</h3>
              {(shown.comments ?? []).length === 0 && <p className="text-xs text-muted-foreground">No comments yet.</p>}
              {(shown.comments ?? []).map((c) => (
                <div key={c.id} className="rounded-lg bg-muted/40 p-2.5 text-sm">
                  <p className="text-xs font-semibold">{c.name} <span className="font-normal text-muted-foreground">· {fmtWhen(c.at)}</span></p>
                  <p className="mt-0.5 whitespace-pre-wrap">{c.text}</p>
                </div>
              ))}
              <Textarea rows={2} value={comment} onChange={(e) => setComment(e.target.value)} className="text-sm" placeholder="Add a comment or more detail" aria-label="Comment" />
              <Button size="sm" className="self-start" disabled={pending || !comment.trim()} onClick={() => { const t = comment; setComment(""); run(() => commentOnFeedback(shown.id, t)); }}>Add comment</Button>
            </section>

            {shown.can_delete && (
              <Button size="sm" variant="ghost" className="gap-1.5 self-start text-destructive" disabled={pending} onClick={() => {
                if (!confirm(`Delete feedback #${shown.number}? This can't be undone.`)) return;
                start(async () => {
                  try { await deleteFeedback(shown.id); toast.success("Deleted"); onDeleted(shown.id); }
                  catch (e) { toast.error(friendlyError(e, "Couldn't delete it")); }
                });
              }}><Trash2 className="size-3.5" /> Delete</Button>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
