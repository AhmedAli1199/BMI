"use client";

import { useEffect, useState } from "react";
import { MessageSquarePlus } from "lucide-react";
import { toast } from "sonner";
import type { BrainConversationSummary } from "@/lib/brain-types";
import { brainConversations } from "@/lib/brain-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { BrainChat } from "@/components/brain/brain-chat";
import { HistoryList } from "@/components/brain/brain-provider";

export function BrainPage({ initial, userName }: { initial: string | null; userName?: string }) {
  const [active, setActive] = useState<string | null>(initial);
  const [chatKey, setChatKey] = useState(0);
  const [list, setList] = useState<BrainConversationSummary[]>([]);
  const refresh = () => brainConversations().then(setList).catch((e) => toast.error(friendlyError(e, "Couldn't load your conversations")));
  useEffect(() => { void refresh(); }, []);
  const open = (id: string | null, fresh = true) => {
    setActive(id);
    if (fresh) setChatKey((k) => k + 1);
    window.history.replaceState(null, "", id ? `/brain?c=${id}` : "/brain");
  };
  return (
    <div className="grid min-h-[32rem] flex-1 overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs md:grid-cols-[16rem_1fr]">
      <div className="hidden flex-col border-r border-border/70 md:flex">
        <div className="border-b border-border/70 p-2">
          <Button size="sm" variant="outline" className="w-full gap-1.5" onClick={() => open(null)}><MessageSquarePlus className="size-3.5" /> New conversation</Button>
        </div>
        <HistoryList items={list} active={active} onOpen={open} onDelete={(id) => { setList(list.filter((c) => c.id !== id)); if (id === active) open(null); }}
          onRename={(id, title) => setList(list.map((c) => (c.id === id ? { ...c, title } : c)))} />
      </div>
      <div className="flex min-h-0 flex-col">
        <BrainChat key={chatKey} variant="page" conversationId={active} userName={userName}
          onConversation={(id) => { open(id, false); void refresh(); }} />
      </div>
    </div>
  );
}
