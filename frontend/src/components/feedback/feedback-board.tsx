"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { Download, ExternalLink, Image as ImageIcon, Loader2, MapPin, MessageSquare, Search, ThumbsUp } from "lucide-react";
import { toast } from "sonner";
import { FEEDBACK_KINDS, FEEDBACK_STATUSES, feedbackImageUrl, type FeedbackBoard, type FeedbackItem } from "@/lib/feedback-types";
import { listFeedback, type BoardQuery } from "@/lib/feedback-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FeedbackDetail } from "@/components/feedback/feedback-detail";
import { fmtWhen, statusTone } from "@/components/feedback/feedback-ui";

const STATUS_TABS = [
  { key: "open", label: "Open" },
  ...FEEDBACK_STATUSES.map((s) => ({ key: s.status, label: s.label })),
  { key: "", label: "All" },
];
const selectCls = "h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

/** Everyone's feedback in one place, with filters, the download and the detail panel. */
export function FeedbackBoardView({ initial, openId }: { initial: FeedbackBoard | null; openId: string | null }) {
  const [board, setBoard] = useState<FeedbackBoard | null>(initial);
  const [q, setQ] = useState<BoardQuery>({ status: "open", sort: "new" });
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<string | null>(openId);
  const [pending, start] = useTransition();
  const first = useRef(true);

  const load = (next: BoardQuery) => start(async () => {
    try { setBoard(await listFeedback(next)); }
    catch (e) { toast.error(friendlyError(e, "Couldn't load the feedback")); }
  });

  useEffect(() => {
    if (first.current) { first.current = false; return; }
    load(q);
  }, [q]);

  // Search as they type, a moment after they stop.
  useEffect(() => {
    const t = setTimeout(() => setQ((x) => (x.q === (search || undefined) ? x : { ...x, q: search || undefined, offset: 0 })), 350);
    return () => clearTimeout(t);
  }, [search]);

  const set = (patch: Partial<BoardQuery>) => setQ({ ...q, ...patch, offset: 0 });
  const replace = (f: FeedbackItem) => setBoard((b) => (b ? { ...b, items: b.items.map((x) => (x.id === f.id ? { ...x, ...f } : x)) } : b));
  const remove = (id: string) => setBoard((b) => (b ? { ...b, items: b.items.filter((x) => x.id !== id), total: b.total - 1 } : b));

  const exportHref = () => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(q)) if (v !== undefined && v !== "" && v !== false && k !== "sort" && k !== "offset") p.set(k, String(v));
    return `/api/files/feedback/export?${p}`;
  };

  if (!board) return <p className="text-sm text-muted-foreground">The feedback couldn&apos;t be loaded just now. Try again in a moment.</p>;
  const openCount = (board.counts.new ?? 0) + (board.counts.looking ?? 0);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {[
          { label: "Open", n: openCount, key: "open" },
          { label: "New", n: board.counts.new, key: "new" },
          { label: "Looking at it", n: board.counts.looking, key: "looking" },
          { label: "Fixed", n: board.counts.fixed, key: "fixed" },
          { label: "Won't do", n: board.counts.wont_do, key: "wont_do" },
        ].map((t) => (
          <button key={t.key} type="button" onClick={() => set({ status: t.key })}
            className={`rounded-xl border p-3 text-left shadow-2xs transition ${q.status === t.key ? "border-primary bg-primary/5" : "border-border/80 bg-card hover:border-primary/50"}`}>
            <p className="text-xs font-semibold text-muted-foreground">{t.label}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{t.n ?? 0}</p>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Status">
          {STATUS_TABS.map((t) => (
            <button key={t.key || "all"} type="button" role="tab" aria-selected={(q.status ?? "") === t.key} onClick={() => set({ status: t.key || undefined })}
              className={`rounded-full px-3 py-1 text-xs font-medium ${(q.status ?? "") === t.key ? "bg-foreground text-background" : "bg-muted text-muted-foreground hover:text-foreground"}`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative ml-auto w-full sm:w-64">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search words, a page, a person or #12" className="h-8 pl-8 text-sm" aria-label="Search feedback" />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select className={selectCls} value={q.kind ?? ""} onChange={(e) => set({ kind: e.target.value || undefined })} aria-label="Kind">
          <option value="">Every kind</option>
          {FEEDBACK_KINDS.map((k) => <option key={k.kind} value={k.kind}>{k.label}</option>)}
        </select>
        <select className={`${selectCls} max-w-64`} value={q.path ?? ""} onChange={(e) => set({ path: e.target.value || undefined })} aria-label="Page">
          <option value="">Every page</option>
          {board.pages.map((p) => <option key={p.path} value={p.path}>{p.title || p.path} ({p.count})</option>)}
        </select>
        <select className={selectCls} value={q.sort ?? "new"} onChange={(e) => set({ sort: e.target.value })} aria-label="Sort">
          <option value="new">Newest first</option>
          <option value="votes">Most votes first</option>
          <option value="updated">Recently changed</option>
          <option value="old">Oldest first</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <input type="checkbox" checked={!!q.mine} onChange={(e) => set({ mine: e.target.checked || undefined })} /> Only mine
        </label>
        {pending && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
        <a href={exportHref()} className="ml-auto" download>
          <Button size="sm" variant="outline" className="gap-1.5"><Download className="size-3.5" /> Download feedback</Button>
        </a>
      </div>
      <p className="-mt-2 text-[11px] text-muted-foreground">
        {board.total} {board.total === 1 ? "piece" : "pieces"} of feedback. The download has the ones shown here (with their screenshots) as a document you can read and a file for the developers.
        {board.github && " Each one is also a GitHub issue."}
      </p>

      {board.items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          Nothing here. Use the <strong className="font-semibold text-foreground">Feedback</strong> button at the bottom right of any page to add some.
        </div>
      ) : (
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {board.items.map((f) => (
            <li key={f.id}>
              <button type="button" onClick={() => setOpen(f.id)}
                className="flex h-full w-full flex-col overflow-hidden rounded-xl border border-border/80 bg-card text-left shadow-2xs transition hover:border-primary/60 hover:shadow-sm">
                {f.images[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={feedbackImageUrl(f.images[0].id)} alt={f.images[0].label ?? "Screenshot"} loading="lazy" className="h-36 w-full border-b border-border/70 bg-muted object-cover object-top" />
                ) : null}
                <div className="flex flex-1 flex-col gap-1.5 p-3">
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="font-semibold text-muted-foreground">#{f.number}</span>
                    <span className={`rounded-full px-2 py-0.5 font-medium ${statusTone(f.status)}`}>{f.status_label}</span>
                    <span className="rounded-full bg-muted px-2 py-0.5 font-medium text-muted-foreground">{f.kind_label}</span>
                  </div>
                  <p className="line-clamp-3 text-sm font-medium">{f.message || f.elements[0]?.label || "No words, see the screenshot."}</p>
                  {f.elements[0] && <p className="flex items-center gap-1 truncate text-xs text-muted-foreground"><MapPin className="size-3 shrink-0" aria-hidden="true" />{f.elements[0].path || f.elements[0].label}</p>}
                  <p className="truncate text-xs text-muted-foreground">{f.page_title || f.page_path}</p>
                  <div className="mt-auto flex items-center gap-3 pt-1.5 text-[11px] text-muted-foreground">
                    <span>{f.user_name} · {fmtWhen(f.created_at)}</span>
                    <span className="ml-auto flex items-center gap-2">
                      {f.images.length > 1 && <span className="flex items-center gap-0.5"><ImageIcon className="size-3" />{f.images.length}</span>}
                      {f.comment_count > 0 && <span className="flex items-center gap-0.5"><MessageSquare className="size-3" />{f.comment_count}</span>}
                      <span className={`flex items-center gap-0.5 ${f.me_too_mine ? "font-semibold text-primary" : ""}`}><ThumbsUp className="size-3" />{f.me_too.length + 1}</span>
                      {f.github_url && <ExternalLink className="size-3" aria-label="Also on GitHub" />}
                    </span>
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
      {board.total > board.items.length + (q.offset ?? 0) && (
        <Button variant="outline" size="sm" className="self-center" disabled={pending} onClick={() => start(async () => {
          try {
            const more = await listFeedback({ ...q, offset: board.items.length });
            setBoard({ ...more, items: [...board.items, ...more.items] });
          } catch (e) { toast.error(friendlyError(e, "Couldn't load more")); }
        })}>Show more</Button>
      )}

      <FeedbackDetail id={open} onClose={() => setOpen(null)} onChange={replace} onDeleted={(id) => { remove(id); setOpen(null); }} />
    </div>
  );
}
