"use client";

import { useEffect, useState } from "react";
import { ExternalLink, ThumbsUp, X } from "lucide-react";
import { toast } from "sonner";
import type { FeedbackPin } from "@/lib/feedback-types";
import { toggleMeToo } from "@/lib/feedback-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";

type Placed = { pin: FeedbackPin; x: number; y: number };

/** Open feedback about this page as numbered dots on the things people pointed at. */
export function FeedbackPins({ pins, focusId, onClose }: { pins: FeedbackPin[]; focusId?: string | null; onClose: () => void }) {
  const [placed, setPlaced] = useState<Placed[]>([]);
  const [openId, setOpenId] = useState<string | null>(focusId ?? null);

  // Things move (scrolling, opening panels), so keep finding them.
  useEffect(() => {
    let alive = true;
    const place = () => {
      if (!alive) return;
      const out: Placed[] = [];
      for (const pin of pins) {
        for (const e of pin.elements) {
          let el: Element | null = null;
          try { el = e.selector ? document.querySelector(e.selector) : null; } catch { el = null; }
          if (!el) continue;
          const r = el.getBoundingClientRect();
          if (r.width === 0 && r.height === 0) continue;
          let x = Math.min(innerWidth - 14, r.right - 4);
          const y = Math.max(14, r.top + 4);
          // Several about the same thing sit side by side, not on top of each other.
          while (out.some((o) => Math.abs(o.x - x) < 12 && Math.abs(o.y - y) < 12)) x -= 26;
          out.push({ pin, x, y });
          break;
        }
      }
      setPlaced(out);
    };
    place();
    const t = setInterval(place, 400);
    return () => { alive = false; clearInterval(t); };
  }, [pins]);

  useEffect(() => {
    if (!focusId) return;
    const p = placed.find((x) => x.pin.id === focusId);
    if (!p) return;
    const pin = p.pin.elements.find((e) => e.selector);
    try { if (pin?.selector) document.querySelector(pin.selector)?.scrollIntoView({ block: "center", behavior: "smooth" }); } catch { /* not there */ }
    // only once, when it's first found
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusId, placed.length > 0]);

  const notShown = pins.filter((p) => !placed.some((x) => x.pin.id === p.id));
  const current = pins.find((p) => p.id === openId);

  return (
    <div data-feedback-ui="" className="pointer-events-none fixed inset-0 z-[2147482000]">
      {placed.map(({ pin, x, y }) => (
        <button key={pin.id} type="button" onClick={() => setOpenId(openId === pin.id ? null : pin.id)}
          className={`pointer-events-auto absolute flex size-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full text-[11px] font-bold shadow-md ring-2 ring-background transition-transform hover:scale-110 ${pin.id === openId ? "bg-foreground text-background" : "bg-primary text-primary-foreground"}`}
          style={{ left: x, top: y }} aria-label={`Feedback ${pin.number}: ${pin.message || pin.kind_label}`}>
          {pin.number}
        </button>
      ))}
      <div className="pointer-events-auto absolute bottom-20 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-full bg-popover py-1 pl-3 pr-1 text-xs text-popover-foreground shadow-lg ring-1 ring-border">
        <span><strong>{pins.length}</strong> open on this page{notShown.length ? ` · ${notShown.length} not on screen right now` : ""}</span>
        <Button size="icon-sm" variant="ghost" aria-label="Hide the dots" onClick={onClose}><X className="size-3.5" /></Button>
      </div>
      {current && <PinCard pin={current} onClose={() => setOpenId(null)} />}
    </div>
  );
}

function PinCard({ pin, onClose }: { pin: FeedbackPin; onClose: () => void }) {
  const [count, setCount] = useState(pin.me_too);
  const [voted, setVoted] = useState(pin.me_too_mine);
  return (
    <div className="pointer-events-auto absolute bottom-32 left-1/2 w-[min(24rem,calc(100vw-2rem))] -translate-x-1/2 rounded-xl bg-popover p-3 text-sm text-popover-foreground shadow-xl ring-1 ring-border">
      <div className="flex items-start gap-2">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">{pin.number}</span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-muted-foreground">{pin.kind_label} · {pin.user_name}</p>
          <p className="mt-0.5 line-clamp-4">{pin.message || pin.elements[0]?.label || "No words, just pointed at this."}</p>
        </div>
        <Button size="icon-sm" variant="ghost" aria-label="Close" onClick={onClose}><X className="size-3.5" /></Button>
      </div>
      <div className="mt-2 flex items-center gap-2">
        {pin.mine ? (
          <span className="text-xs text-muted-foreground">You sent this{count ? ` · ${count} said me too` : ""}</span>
        ) : (
          <Button size="sm" variant={voted ? "default" : "outline"} className="gap-1.5" onClick={async () => {
            try { const r = await toggleMeToo(pin.id); setCount(r.me_too.length); setVoted(r.me_too_mine); toast.success(r.me_too_mine ? "Added your vote" : "Took your vote off"); }
            catch (e) { toast.error(friendlyError(e, "Couldn't add your vote")); }
          }}><ThumbsUp className="size-3.5" /> {voted ? "You said me too" : "Me too"}{count ? ` (${count})` : ""}</Button>
        )}
        <a href={`/feedback?open=${pin.id}`} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
          Open it <ExternalLink className="size-3" aria-hidden="true" />
        </a>
      </div>
    </div>
  );
}
