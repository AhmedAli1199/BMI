"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, EyeOff, Pencil, Square, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type Tool = "pen" | "arrow" | "box" | "hide";
type Shape = { tool: Tool; points: { x: number; y: number }[] };

// Drawn into the picture itself, so it's a fixed colour (not a theme colour) that shows on any screen.
const INK = "#e11d48";

function draw(ctx: CanvasRenderingContext2D, s: Shape, k: number) {
  const p = s.points;
  if (!p.length) return;
  ctx.save();
  ctx.lineWidth = 4 * k;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = INK;
  const a = p[0], b = p[p.length - 1];
  if (s.tool === "pen") {
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    p.forEach((q) => ctx.lineTo(q.x, q.y));
    ctx.stroke();
  } else if (s.tool === "box") {
    ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
  } else if (s.tool === "hide") {
    ctx.fillStyle = "#111827";
    ctx.fillRect(a.x, a.y, b.x - a.x, b.y - a.y);
  } else {
    const ang = Math.atan2(b.y - a.y, b.x - a.x), head = 16 * k;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.lineTo(b.x - head * Math.cos(ang - 0.45), b.y - head * Math.sin(ang - 0.45));
    ctx.moveTo(b.x, b.y);
    ctx.lineTo(b.x - head * Math.cos(ang + 0.45), b.y - head * Math.sin(ang + 0.45));
    ctx.stroke();
  }
  ctx.restore();
}

/** Mark up a screenshot: draw, arrows, boxes, and black out anything private. Give it a new key for each picture. */
export function AnnotateDialog({ image, open, onDone, onCancel }: {
  image: HTMLCanvasElement | null; open: boolean; onDone: (c: HTMLCanvasElement) => void; onCancel: () => void;
}) {
  const view = useRef<HTMLCanvasElement>(null);
  const [tool, setTool] = useState<Tool>("arrow");
  const [shapes, setShapes] = useState<Shape[]>([]);
  const live = useRef<Shape | null>(null);

  const k = image ? Math.max(1, image.width / 900) : 1;

  function paint(extra?: Shape | null) {
    const c = view.current;
    if (!c || !image) return;
    c.width = image.width;
    c.height = image.height;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(image, 0, 0);
    [...shapes, ...(extra ? [extra] : [])].forEach((s) => draw(ctx, s, k));
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { paint(); }, [shapes, image, open]);

  const at = (e: React.PointerEvent) => {
    const c = view.current!;
    const r = c.getBoundingClientRect();
    return { x: ((e.clientX - r.left) / r.width) * c.width, y: ((e.clientY - r.top) / r.height) * c.height };
  };

  const tools: { t: Tool; label: string; icon: React.ReactNode }[] = [
    { t: "arrow", label: "Arrow", icon: <ArrowUpRight className="size-3.5" /> },
    { t: "box", label: "Box", icon: <Square className="size-3.5" /> },
    { t: "pen", label: "Draw", icon: <Pencil className="size-3.5" /> },
    { t: "hide", label: "Hide", icon: <EyeOff className="size-3.5" /> },
  ];

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent data-feedback-ui="" className="max-h-[94vh] gap-3 overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>Mark up the screenshot</DialogTitle>
          <DialogDescription>Point things out with an arrow or box. Use Hide to black out anything private before it&apos;s sent.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-wrap items-center gap-1">
          {tools.map((x) => (
            <Button key={x.t} size="sm" variant={tool === x.t ? "default" : "outline"} className="gap-1.5" onClick={() => setTool(x.t)}>{x.icon} {x.label}</Button>
          ))}
          <Button size="sm" variant="ghost" className="ml-auto gap-1.5" disabled={!shapes.length} onClick={() => setShapes(shapes.slice(0, -1))}><Undo2 className="size-3.5" /> Undo</Button>
        </div>
        <div className="flex justify-center rounded-lg border border-border bg-muted/40 p-2">
          <canvas
            ref={(c) => {
              view.current = c;
              // The dialog's content appears a moment after it opens: draw as soon as the canvas is there.
              if (c && !c.dataset.painted) { c.dataset.painted = "1"; paint(); }
            }}
            className="max-h-[62vh] max-w-full cursor-crosshair touch-none rounded"
            style={{ width: image ? Math.min(image.width / (window.devicePixelRatio || 1), 1000) : undefined }}
            onPointerDown={(e) => { (e.target as Element).setPointerCapture(e.pointerId); live.current = { tool, points: [at(e)] }; }}
            onPointerMove={(e) => {
              if (!live.current) return;
              const p = at(e);
              live.current = { ...live.current, points: tool === "pen" ? [...live.current.points, p] : [live.current.points[0], p] };
              paint(live.current);
            }}
            onPointerUp={() => {
              const s = live.current;
              live.current = null;
              if (s && s.points.length > 1) setShapes([...shapes, s]);
            }}
          />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onCancel}>Cancel</Button>
          <Button onClick={() => { paint(); if (view.current) onDone(view.current); }}>Add this screenshot</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
