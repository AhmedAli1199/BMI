"use client";

import { Fragment, type ReactNode } from "react";
import { ExternalLink, Info, Lightbulb, MousePointerClick, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { showMe } from "@/components/brain/show-me";

/** The assistant's answers: a small, safe Markdown subset (no HTML) plus [[show:Label]] "Show me" buttons.
 * Every link opens in a new tab so nobody loses their place. */
export function BrainMarkdown({ text, streaming = false }: { text: string; streaming?: boolean }) {
  // half-typed [[show:…]] / [[ask:…]] while it's still streaming
  const clean = (streaming ? text.replace(/\[\[[^\]]*\]?$/, "") : text).replace(/\[\[ask:[^\]]*\]\]/g, "");
  const blocks = toBlocks(clean);
  return <div className="flex flex-col gap-2 text-sm leading-relaxed">{blocks.map((b, i) => <Block key={i} b={b} />)}</div>;
}

type B = { kind: "p" | "h" | "ul" | "ol" | "tip" | "note"; lines: string[] };

function toBlocks(text: string): B[] {
  const out: B[] = [];
  let cur: B | null = null;
  const push = (b: B) => { out.push(b); cur = b; };
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) { cur = null; continue; }
    let m: RegExpMatchArray | null;
    if ((m = line.match(/^#{1,4}\s+(.*)$/))) { push({ kind: "h", lines: [m[1]] }); cur = null; continue; }
    if ((m = line.match(/^>\s*(?:\*\*)?(Tip|Note|Warning)(?:\*\*)?:?\s*(?:\*\*)?\s*(.*)$/i))) {
      push({ kind: m[1].toLowerCase() === "tip" ? "tip" : "note", lines: [m[2]] }); continue;
    }
    if ((m = line.match(/^>\s?(.*)$/))) {
      const c = cur as B | null;
      if (c && (c.kind === "tip" || c.kind === "note")) c.lines.push(m[1]); else push({ kind: "note", lines: [m[1]] });
      continue;
    }
    if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) {
      const c = cur as B | null;
      if (c?.kind === "ul") c.lines.push(m[1]); else push({ kind: "ul", lines: [m[1]] });
      continue;
    }
    if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
      const c = cur as B | null;
      if (c?.kind === "ol") c.lines.push(m[1]); else push({ kind: "ol", lines: [m[1]] });
      continue;
    }
    const c = cur as B | null;
    if (c && (c.kind === "ul" || c.kind === "ol") && /^\s{2,}/.test(raw)) { c.lines[c.lines.length - 1] += ` ${line.trim()}`; continue; }
    if (c?.kind === "p") c.lines.push(line); else push({ kind: "p", lines: [line] });
  }
  return out;
}

function Block({ b }: { b: B }) {
  if (b.kind === "h") return <h4 className="mt-1 text-sm font-bold">{inline(b.lines[0])}</h4>;
  if (b.kind === "ul") return <ul className="ml-4 list-disc space-y-1 marker:text-muted-foreground">{b.lines.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>;
  if (b.kind === "ol") {
    return (
      <ol className="space-y-1.5">
        {b.lines.map((l, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/12 text-[11px] font-bold text-primary">{i + 1}</span>
            <span className="min-w-0 flex-1">{inline(l)}</span>
          </li>
        ))}
      </ol>
    );
  }
  if (b.kind === "tip" || b.kind === "note") {
    const tip = b.kind === "tip";
    const Icon = tip ? Lightbulb : /warn|careful/i.test(b.lines.join(" ")) ? TriangleAlert : Info;
    return (
      <div className="flex gap-2 rounded-lg border px-3 py-2 text-[13px]"
        style={{ borderColor: `color-mix(in oklab, var(${tip ? "--ok" : "--warn"}) 35%, transparent)`, background: `color-mix(in oklab, var(${tip ? "--ok" : "--warn"}) 8%, transparent)` }}>
        <Icon className="mt-0.5 size-3.5 shrink-0" style={{ color: `var(${tip ? "--ok" : "--warn"})` }} aria-hidden="true" />
        <span className="min-w-0">{inline(b.lines.join(" "))}</span>
      </div>
    );
  }
  return <p>{inline(b.lines.join(" "))}</p>;
}

const TOKEN = /(\[\[show:[^\]]+\]\]|\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g;

function inline(text: string): ReactNode {
  const parts = text.split(TOKEN).filter((p) => p !== "");
  return parts.map((p, i) => {
    let m: RegExpMatchArray | null;
    if ((m = p.match(/^\[\[show:([^\]]+)\]\]$/))) return <ShowMeButton key={i} label={m[1].trim()} />;
    if ((m = p.match(/^\*\*([^*]+)\*\*$/))) return <strong key={i} className="font-semibold text-foreground">{m[1]}</strong>;
    if ((m = p.match(/^`([^`]+)`$/))) return <code key={i} className="rounded bg-muted px-1 py-0.5 text-[12px]">{m[1]}</code>;
    if ((m = p.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/))) {
      const href = m[2];
      if (!href.startsWith("/") && !href.startsWith("https://")) return <Fragment key={i}>{m[1]}</Fragment>;
      return (
        <a key={i} href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 font-medium text-primary hover:underline">
          {m[1]}<ExternalLink className="size-3" aria-hidden="true" />
        </a>
      );
    }
    return <Fragment key={i}>{p}</Fragment>;
  });
}

function ShowMeButton({ label }: { label: string }) {
  return (
    <button type="button" onClick={() => { if (!showMe(label)) toast.info(`“${label}” isn't on the screen right now - it may be inside a menu, a closed panel or another tab.`); }}
      className="mx-0.5 inline-flex items-center gap-1 rounded-full border border-primary/40 bg-primary/8 px-1.5 py-px align-baseline text-[11px] font-semibold text-primary hover:bg-primary/15"
      aria-label={`Show me ${label} on the page`}>
      <MousePointerClick className="size-3" aria-hidden="true" /> Show me
    </button>
  );
}
