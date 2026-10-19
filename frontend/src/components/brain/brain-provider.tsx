"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { ExternalLink, History, Loader2, MessageSquarePlus, Pencil, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { BrainConversationSummary } from "@/lib/brain-types";
import { brainConversations, deleteBrainConversation, renameBrainConversation } from "@/lib/brain-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BrainBuddy } from "@/components/brain/brain-buddy";
import { BrainCoach } from "@/components/brain/brain-coach";
import { BrainChat, type ChatHandle, type Seed } from "@/components/brain/brain-chat";

type Ask = Seed;
const Ctx = createContext<{ ask: (a?: Ask) => void; open: boolean }>({ ask: () => {}, open: false });

/** Anywhere in the app: `const { ask } = useBrain(); ask({ question: "How do I…?" })` opens the assistant. */
export const useBrain = () => useContext(Ctx);

/** The assistant beside every page: the "Ask AI" button, the side panel (the page stays usable, so
 * "Show me" can point at it), ⌘/Ctrl + J to open and close. The panel is left out of screenshots and
 * can't be pointed at itself (data-feedback-ui), like the Feedback panel. */
export function BrainProvider({ userName, role, children }: { userName?: string; role?: string; children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const [open, setOpen] = useState(false);
  const [conversation, setConversation] = useState<string | null>(null);
  const [chatKey, setChatKey] = useState(0);   // a new key = a fresh chat (new or picked conversation)
  const [seed, setSeed] = useState<Seed | null>(null);
  const chat = useRef<ChatHandle | null>(null);
  const [history, setHistory] = useState<BrainConversationSummary[] | null>(null);

  const ask = useCallback((a?: Ask) => {
    const has = !!a && !!(a.question || a.elements?.length || a.shots?.length);
    if (has && chat.current) chat.current.seed(a!);     // already open: hand it straight over
    else setSeed(has ? a! : null);
    setOpen(true);
    setHistory(null);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j" && !window.location.pathname.startsWith("/brain")) { e.preventDefault(); setOpen((o) => !o); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // On wide screens the page makes room for the panel instead of hiding under it.
  useEffect(() => {
    document.body.classList.toggle("brain-open", open);
    return () => document.body.classList.remove("brain-open");
  }, [open]);

  const showHistory = async () => {
    if (history) { setHistory(null); return; }
    try { setHistory(await brainConversations()); } catch (e) { toast.error(friendlyError(e, "Couldn't load your conversations")); }
  };

  const print = pathname.includes("/print");
  return (
    <Ctx.Provider value={{ ask, open }}>
      {children}
      {!print && <BrainCoach role={role} panelOpen={open} />}
      {!print && !open && !pathname.startsWith("/brain") && <AskButton onClick={() => ask()} />}
      {!print && open && (
        <aside data-brain-panel="" data-feedback-ui="" aria-label="Ask the Brain"
          className={`fixed inset-y-0 right-0 z-[2147481500] flex w-full flex-col border-l border-border bg-popover text-popover-foreground shadow-2xl sm:w-[26rem] print:hidden`}>
          <header className="flex items-center gap-1 border-b border-border/70 px-3 py-2.5">
            <BrainBuddy head mood="happy" size={22} still />
            <h2 className="mr-auto pl-1 text-sm font-semibold">Ask the Brain</h2>
            <Button size="icon-sm" variant="ghost" aria-label="Your conversations" aria-pressed={!!history} title="Your conversations" onClick={() => void showHistory()}><History className="size-4" /></Button>
            <Button size="icon-sm" variant="ghost" aria-label="New conversation" title="New conversation" onClick={() => { setConversation(null); setHistory(null); setSeed(null); setChatKey((k) => k + 1); }}><MessageSquarePlus className="size-4" /></Button>
            <Button size="icon-sm" variant="ghost" aria-label="Open on its own page" title="Open on its own page" nativeButton={false}
              render={<a href={conversation ? `/brain?c=${conversation}` : "/brain"} target="_blank" rel="noreferrer" />}><ExternalLink className="size-4" /></Button>
            <Button size="icon-sm" variant="ghost" aria-label="Close" title="Close (Ctrl+J)" onClick={() => setOpen(false)}><X className="size-4" /></Button>
          </header>
          {history ? (
            <HistoryList items={history} onOpen={(id) => { setConversation(id); setHistory(null); setSeed(null); setChatKey((k) => k + 1); }}
              onDelete={(id) => { setHistory(history.filter((h) => h.id !== id)); if (id === conversation) { setConversation(null); setChatKey((k) => k + 1); } }}
              onRename={(id, title) => setHistory(history.map((h) => (h.id === id ? { ...h, title } : h)))} />
          ) : (
            <BrainChat key={chatKey} handle={chat} variant="panel" conversationId={conversation} onConversation={setConversation} seed={seed} userName={userName}
              />
          )}
        </aside>
      )}
    </Ctx.Provider>
  );
}

export function HistoryList({ items, onOpen, onDelete, onRename, active }: {
  items: BrainConversationSummary[]; onOpen: (id: string) => void; onDelete: (id: string) => void; onRename: (id: string, title: string) => void; active?: string | null;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<{ id: string; title: string } | null>(null);
  if (!items.length) return <p className="px-4 py-6 text-center text-sm text-muted-foreground">No conversations yet.</p>;

  async function saveName() {
    if (!renaming) return;
    const { id, title } = renaming;
    const was = items.find((c) => c.id === id)?.title ?? "";
    setRenaming(null);
    if (!title.trim() || title.trim() === was) return;
    setBusy(id);
    try { await renameBrainConversation(id, title.trim()); onRename(id, title.trim().slice(0, 200)); }
    catch (e) { toast.error(friendlyError(e, "Couldn't rename it")); }
    finally { setBusy(null); }
  }

  return (
    <ul className="flex-1 divide-y divide-border/60 overflow-y-auto">
      {items.map((c) => (
        <li key={c.id} className={`group flex items-center gap-2 px-3 py-2 ${c.id === active ? "bg-muted/60" : ""}`}>
          {renaming?.id === c.id ? (
            <Input autoFocus value={renaming.title} aria-label="New name for the conversation" maxLength={200} className="h-7 min-w-0 flex-1 text-sm"
              onChange={(e) => setRenaming({ id: c.id, title: e.target.value })}
              onKeyDown={(e) => { if (e.key === "Enter") void saveName(); if (e.key === "Escape") setRenaming(null); }}
              onBlur={() => void saveName()} />
          ) : (
            <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onOpen(c.id)}>
              <p className="truncate text-sm font-medium">{c.title}</p>
              {c.updated_at && <p className="text-[11px] text-muted-foreground">{new Date(c.updated_at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</p>}
            </button>
          )}
          {renaming?.id !== c.id && (
            <Button size="icon-xs" variant="ghost" aria-label={`Rename ${c.title}`} title="Rename" className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" disabled={busy === c.id}
              onClick={() => setRenaming({ id: c.id, title: c.title })}>
              <Pencil className="size-3" />
            </Button>
          )}
          <Button size="icon-xs" variant="ghost" aria-label={`Delete ${c.title}`} className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" disabled={busy === c.id}
            onClick={async () => {
              setBusy(c.id);
              try { await deleteBrainConversation(c.id); onDelete(c.id); } catch (e) { toast.error(friendlyError(e, "Couldn't delete it")); } finally { setBusy(null); }
            }}>
            {busy === c.id ? <Loader2 className="size-3 animate-spin" /> : <Trash2 className="size-3" />}
          </Button>
        </li>
      ))}
    </ul>
  );
}

/** Sits just above the Feedback button; steps aside when a pop-up or the feedback panel is open. */
function AskButton({ onClick }: { onClick: () => void }) {
  const [covered, setCovered] = useState(false);
  useEffect(() => {
    const check = () => setCovered(!!document.querySelector("[data-base-ui-inert], section[data-feedback-ui], div.fixed.inset-0[data-feedback-ui]"));
    check();
    const mo = new MutationObserver(check);
    mo.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["data-base-ui-inert"] });
    return () => mo.disconnect();
  }, []);
  if (covered) return null;
  return (
    <button type="button" data-feedback-ui="" onClick={onClick} title="Ask the Brain how anything works (Ctrl+J)"
      className="fixed bottom-14 right-4 z-[2147481000] flex items-center gap-1.5 rounded-full border border-primary/30 bg-background py-1.5 pl-2 pr-3.5 text-xs font-semibold text-primary shadow-lg transition hover:translate-y-[-1px] hover:shadow-xl print:hidden">
      <BrainBuddy head mood="happy" size={22} /> Ask the Brain
    </button>
  );
}
