"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Crosshair, Loader2, Maximize, X } from "lucide-react";
import { describe, meaningful } from "@/lib/feedback-capture";
import type { FeedbackElement } from "@/lib/feedback-types";
import { Button } from "@/components/ui/button";

const Z = "z-[2147483000]";

/** Point at something: everything under the mouse gets an outline and a name; a click picks it. */
export function PickOverlay({ onPick, onCancel }: { onPick: (el: Element, d: FeedbackElement) => void; onCancel: () => void }) {
  const [hover, setHover] = useState<{ rect: DOMRect; label: string } | null>(null);
  const current = useRef<Element | null>(null);

  useEffect(() => {
    const under = (x: number, y: number) =>
      document.elementsFromPoint(x, y).find((e) => !e.closest("[data-feedback-ui]") && e !== document.documentElement && e !== document.body) ?? null;
    const move = (e: PointerEvent) => {
      const hit = under(e.clientX, e.clientY);
      const el = hit ? meaningful(hit) : null;
      current.current = el;
      setHover(el ? { rect: el.getBoundingClientRect(), label: describe(el).label } : null);
    };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    window.addEventListener("pointermove", move, true);
    window.addEventListener("keydown", key, true);
    return () => { window.removeEventListener("pointermove", move, true); window.removeEventListener("keydown", key, true); };
  }, [onCancel]);

  return (
    <div data-feedback-ui="" className={`fixed inset-0 ${Z} cursor-crosshair`}
      onPointerDown={(e) => { e.preventDefault(); e.stopPropagation(); }}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (current.current) onPick(current.current, describe(current.current));
      }}>
      <div className="pointer-events-none absolute inset-0 bg-foreground/10" />
      {hover && (
        <>
          <div className="pointer-events-none absolute rounded-md border-2 border-primary bg-primary/10 shadow-[0_0_0_9999px_color-mix(in_oklab,var(--foreground)_18%,transparent)] transition-all duration-75"
            style={{ left: hover.rect.left - 3, top: hover.rect.top - 3, width: hover.rect.width + 6, height: hover.rect.height + 6 }} />
          <div className="pointer-events-none absolute max-w-xs truncate rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground shadow"
            style={{ left: Math.max(8, Math.min(hover.rect.left, innerWidth - 320)), top: hover.rect.top > 34 ? hover.rect.top - 30 : hover.rect.bottom + 6 }}>
            {hover.label}
          </div>
        </>
      )}
      <Banner icon={<Crosshair className="size-4" />} text="Click the thing you mean." onCancel={onCancel} />
    </div>
  );
}

/** Snap an area: the screen is frozen as a picture and they drag a box over the part they mean. */
export function AreaOverlay({ screen, onDone, onCancel }: {
  screen: HTMLCanvasElement | null; onDone: (box: { x: number; y: number; w: number; h: number } | null) => void; onCancel: () => void;
}) {
  const [start, setStart] = useState<{ x: number; y: number } | null>(null);
  const [end, setEnd] = useState<{ x: number; y: number } | null>(null);
  const url = useMemo(() => screen?.toDataURL("image/png") ?? "", [screen]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    window.addEventListener("keydown", key, true);
    return () => window.removeEventListener("keydown", key, true);
  }, [onCancel]);

  if (!screen) {
    return (
      <div data-feedback-ui="" className={`fixed inset-0 ${Z} flex items-start justify-center bg-foreground/10 pt-6`}>
        <div className="flex items-center gap-2 rounded-full bg-popover px-4 py-2 text-sm shadow-lg ring-1 ring-border"><Loader2 className="size-4 animate-spin" /> Taking a picture of the page…</div>
      </div>
    );
  }
  const box = start && end ? { x: Math.min(start.x, end.x), y: Math.min(start.y, end.y), w: Math.abs(end.x - start.x), h: Math.abs(end.y - start.y) } : null;

  return (
    <div data-feedback-ui="" className={`fixed inset-0 ${Z} cursor-crosshair select-none touch-none`}
      onPointerDown={(e) => { (e.target as Element).setPointerCapture?.(e.pointerId); setStart({ x: e.clientX, y: e.clientY }); setEnd({ x: e.clientX, y: e.clientY }); }}
      onPointerMove={(e) => start && setEnd({ x: e.clientX, y: e.clientY })}
      onPointerUp={() => {
        if (box && box.w > 8 && box.h > 8) onDone(box);
        setStart(null); setEnd(null);
      }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt="" className="pointer-events-none absolute inset-0 h-full w-full" draggable={false} />
      {box ? (
        <div className="pointer-events-none absolute border-2 border-primary shadow-[0_0_0_9999px_color-mix(in_oklab,var(--foreground)_40%,transparent)]"
          style={{ left: box.x, top: box.y, width: box.w, height: box.h }} />
      ) : <div className="pointer-events-none absolute inset-0 bg-foreground/30" />}
      <Banner icon={<Crosshair className="size-4" />} text="Drag a box over the part you mean."
        extra={<Button size="sm" variant="outline" className="gap-1.5" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onDone(null); }}><Maximize className="size-3.5" /> Whole screen</Button>}
        onCancel={onCancel} />
    </div>
  );
}

function Banner({ icon, text, extra, onCancel }: { icon: React.ReactNode; text: string; extra?: React.ReactNode; onCancel: () => void }) {
  return (
    <div className="absolute left-1/2 top-4 flex -translate-x-1/2 items-center gap-2 rounded-full bg-popover py-1.5 pl-4 pr-1.5 text-sm text-popover-foreground shadow-lg ring-1 ring-border"
      onPointerDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
      {icon}<span className="font-medium">{text}</span><span className="hidden text-xs text-muted-foreground sm:inline">Esc to stop</span>
      {extra}
      <Button size="icon-sm" variant="ghost" aria-label="Stop" onClick={onCancel}><X className="size-4" /></Button>
    </div>
  );
}
