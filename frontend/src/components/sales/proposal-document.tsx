"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Blocks, Plus, RefreshCw, Trash2 } from "lucide-react";
import { BLOCK_OPTIONS, type BlockKind, type ProposalBlock, type ProposalSection } from "@/lib/proposals-types";
import type { SalesRate, SalesTitle } from "@/lib/sales-types";
import { previewBlock } from "@/lib/proposals-actions";
import { normaliseEditorHtml, sanitizeHtml, textToHtml } from "@/lib/rich-text";
import { RichToolbar } from "@/components/mail-merge/rich-email-editor";
import { BlockCard } from "@/components/sales/proposal-sections";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";

/*
 * The whole proposal as one page. It's still saved as sections (the Word file, the email and the AI all use them):
 * each heading (h2) starts a section, and each ready-made block is a box in the page that can't be typed into -
 * click it to choose what it shows.
 */

const blockLabel = (k: BlockKind) => BLOCK_OPTIONS.find((b) => b.kind === k)?.label ?? k;
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const newId = () => crypto.randomUUID();

function blockHtml(sid: string, block: ProposalBlock): string {
  return `<div class="pblock" contenteditable="false" data-sid="${esc(sid)}" data-block="${esc(block.kind)}" data-config="${esc(JSON.stringify(block.config ?? {}))}">`
    + `<div class="pblock-tag">${esc(blockLabel(block.kind))} · filled in for you · click to change</div><div class="pblock-body"></div></div>`;
}

/** Sections -> the page. */
function toHtml(sections: ProposalSection[]): string {
  return sections.map((s) => {
    const head = s.heading.trim() ? `<h2 data-sid="${esc(s.id)}" data-kind="${esc(s.kind)}">${esc(s.heading)}</h2>` : "";
    if (s.block) return head + blockHtml(s.id, s.block);
    const auto = s.kind === "investment"
      ? `<div class="pblock pblock-auto" contenteditable="false" data-auto="package"><div class="pblock-tag">The package and prices from the table above go here</div><div class="pblock-body"></div></div>`
      : "";
    const text = sanitizeHtml(textToHtml(s.html ?? s.body ?? ""), { dataImages: true });
    return head + auto + (text || (head ? "<p><br></p>" : ""));
  }).join("") || "<p><br></p>";
}

/** The page -> sections, keeping each section's id and kind where it can. */
function fromPage(root: HTMLElement, before: ProposalSection[]): ProposalSection[] {
  const known = new Map(before.map((s) => [s.id, s]));
  const seen = new Set<string>();
  const out: (ProposalSection & { parts: string[] })[] = [];
  const takeId = (sid: string | null) => {
    // Pressing Enter in a heading copies it, id and all: the copy becomes a new section.
    const id = sid && !seen.has(sid) ? sid : newId();
    seen.add(id);
    return id;
  };
  let cur: (ProposalSection & { parts: string[] }) | null = null;

  for (const node of Array.from(root.childNodes)) {
    const elNode = node.nodeType === 1 ? (node as HTMLElement) : null;
    if (elNode?.dataset.auto) continue;
    if (elNode?.tagName === "H2") {
      const wanted = elNode.dataset.sid ?? null;
      const id = takeId(wanted);
      const was = id === wanted ? known.get(id) : undefined;
      cur = { id, kind: was && !was.block ? was.kind : "custom", heading: (elNode.textContent ?? "").trim(), body: was?.body ?? "", html: "", block: null, parts: [] };
      out.push(cur);
      continue;
    }
    if (elNode?.dataset.block) {
      let config = {};
      try { config = JSON.parse(elNode.dataset.config || "{}"); } catch { /* keep it empty */ }
      const block = { kind: elNode.dataset.block as BlockKind, config } as ProposalBlock;
      if (cur && !cur.block && !cur.parts.join("").replace(/<br\s*\/?>|<\/?(div|p)>|&nbsp;|\s/gi, "")) {
        // A heading straight above the block is the block's heading.
        cur.block = block;
        cur.kind = `block_${block.kind}`;
      } else {
        cur = { id: takeId(elNode.dataset.sid ?? null), kind: `block_${block.kind}`, heading: "", body: "", html: "", block, parts: [] };
        out.push(cur);
      }
      continue;
    }
    const piece = elNode ? elNode.outerHTML : esc(node.textContent ?? "");
    if (!cur || cur.block) {
      if (!piece.replace(/<br\s*\/?>|<\/?(div|p)>|&nbsp;|\s/gi, "")) continue;
      cur = { id: takeId(null), kind: "custom", heading: "", body: "", html: "", block: null, parts: [] };
      out.push(cur);
    }
    cur.parts.push(piece);
  }
  return out.map(({ parts, ...s }) => (s.block ? { ...s, html: null, body: "" } : { ...s, html: normaliseEditorHtml(sanitizeHtml(parts.join(""), { dataImages: true })) }));
}

export function ProposalDocument({ proposalId, sections, onChange, titleId, titles, rates, brand, refreshKey, disabled }: {
  proposalId: string; sections: ProposalSection[]; onChange: (s: ProposalSection[]) => void; titleId: string | null; titles: SalesTitle[];
  rates: SalesRate[]; brand: string | null; refreshKey: string; disabled: boolean;
}) {
  const el = useRef<HTMLDivElement>(null);
  const saved = useRef<Range | null>(null);
  const lastSent = useRef<string | null>(null);
  const current = useRef<ProposalSection[]>(sections);
  const [editing, setEditingRaw] = useState<{ sid: string; block: ProposalBlock; index: number; count: number } | null>(null);
  // Where the block sits, worked out when it's opened (for Move up / Move down).
  const setEditing = (e: { sid: string; block: ProposalBlock } | null) =>
    setEditingRaw(e && { ...e, index: current.current.findIndex((x) => x.id === e.sid), count: current.current.length });

  /** Fill each block box with what it will say (live data from the server). */
  function fillBlocks(only?: HTMLElement) {
    const root = el.current;
    if (!root) return;
    const boxes = only ? [only] : Array.from(root.querySelectorAll<HTMLElement>(".pblock"));
    boxes.forEach((box) => {
      const body = box.querySelector<HTMLElement>(".pblock-body");
      if (!body) return;
      let block: ProposalBlock;
      if (box.dataset.auto) block = { kind: "package", config: {} };
      else { try { block = { kind: box.dataset.block as BlockKind, config: JSON.parse(box.dataset.config || "{}") }; } catch { return; } }
      body.innerHTML = '<p class="pblock-wait">Filling in...</p>';
      previewBlock(proposalId, block)
        .then((h) => { body.innerHTML = sanitizeHtml(h); })
        .catch(() => { body.innerHTML = "<p><em>Couldn't show this block just now.</em></p>"; });
    });
  }

  function load(list: ProposalSection[]) {
    if (!el.current) return;
    el.current.innerHTML = toHtml(list);
    current.current = list;
    lastSent.current = JSON.stringify(list);
    fillBlocks();
  }

  // Load the proposal, and again whenever it changes from outside (redraft, "Tell the AI what to change", undo).
  useEffect(() => {
    if (JSON.stringify(sections) === lastSent.current) return;
    load(sections);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sections]);

  // Prices, issues or the package changed: refresh what the blocks show.
  const lastKey = useRef(refreshKey);
  useEffect(() => {
    if (lastKey.current === refreshKey) return;
    lastKey.current = refreshKey;
    fillBlocks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  useEffect(() => { document.execCommand("defaultParagraphSeparator", false, "p"); }, []);

  function emit() {
    if (!el.current) return;
    const next = fromPage(el.current, current.current);
    current.current = next;
    lastSent.current = JSON.stringify(next);
    onChange(next);
  }

  function saveSelection() {
    const sel = window.getSelection();
    if (sel && sel.rangeCount && el.current?.contains(sel.anchorNode)) saved.current = sel.getRangeAt(0).cloneRange();
  }

  /** The top-level paragraph the cursor is in, so a block goes in after it. */
  function topLevelAtCursor(): ChildNode | null {
    let n: Node | null = saved.current?.startContainer ?? null;
    while (n && n.parentNode !== el.current) n = n.parentNode;
    return n as ChildNode | null;
  }

  function addBlock(kind: BlockKind) {
    const root = el.current;
    const b = BLOCK_OPTIONS.find((x) => x.kind === kind);
    if (!root || !b) return;
    const sid = newId();
    const tmp = document.createElement("div");
    tmp.innerHTML = `<h2 data-sid="${sid}" data-kind="block_${kind}">${esc(b.heading)}</h2>${blockHtml(sid, { kind, config: {} })}<p><br></p>`;
    const nodes = Array.from(tmp.childNodes);
    const after = topLevelAtCursor();
    if (after) after.after(...nodes); else root.append(...nodes);
    fillBlocks(nodes[1] as HTMLElement);
    emit();
  }

  function updateBlock(sid: string, block: ProposalBlock) {
    const box = el.current?.querySelector<HTMLElement>(`.pblock[data-sid="${CSS.escape(sid)}"]`);
    if (!box) return;
    box.dataset.config = JSON.stringify(block.config ?? {});
    setEditing({ sid, block });
    fillBlocks(box);
    emit();
  }

  /** Move or remove a block (with its heading) as a whole section. */
  function changeSections(sid: string, how: "up" | "down" | "remove") {
    const list = [...current.current];
    const i = list.findIndex((s) => s.id === sid);
    if (i < 0) return;
    if (how === "remove") list.splice(i, 1);
    else {
      const j = how === "up" ? i - 1 : i + 1;
      if (j < 0 || j >= list.length) return;
      [list[i], list[j]] = [list[j], list[i]];
    }
    load(list);
    onChange(list);
    if (how === "remove" || !editing) setEditing(null);
    else setEditing({ sid: editing.sid, block: editing.block });
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs focus-within:border-ring">
        {!disabled && (
          <div className="sticky top-0 z-10">
            <RichToolbar targetRef={el} savedRef={saved} onChange={emit} rich headings className="px-3"
              extra={<>
                <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
                <DropdownMenu>
                  <DropdownMenuTrigger render={<Button size="sm" variant="ghost" className="h-7 gap-1 px-2 text-xs" onMouseDown={(e) => { e.preventDefault(); saveSelection(); }} />}>
                    <Plus className="size-3.5" /> Add a ready-made part
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-72">
                    <DropdownMenuLabel className="text-xs">Filled in for you, goes where your cursor is</DropdownMenuLabel>
                    {BLOCK_OPTIONS.map((b) => (
                      <DropdownMenuItem key={b.kind} onClick={() => addBlock(b.kind)}>
                        <div className="flex flex-col"><span>{b.label}</span><span className="text-[11px] text-muted-foreground">{b.hint}</span></div>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </>} />
          </div>
        )}
        <div className="bg-muted/30 px-2 py-4 sm:px-6 sm:py-6">
          <div
            ref={el}
            role="textbox"
            aria-multiline="true"
            aria-label="Proposal"
            contentEditable={!disabled}
            suppressContentEditableWarning
            onInput={emit}
            onKeyUp={saveSelection}
            onMouseUp={saveSelection}
            onBlur={saveSelection}
            onClick={(e) => {
              const box = (e.target as HTMLElement).closest<HTMLElement>(".pblock[data-block]");
              if (!box || disabled || !box.dataset.sid) return;
              let config = {};
              try { config = JSON.parse(box.dataset.config || "{}"); } catch { /* empty */ }
              setEditing({ sid: box.dataset.sid, block: { kind: box.dataset.block as BlockKind, config } as ProposalBlock });
            }}
            onPaste={(e) => {
              const html = e.clipboardData.getData("text/html");
              if (!html) return;
              e.preventDefault();
              document.execCommand("insertHTML", false, sanitizeHtml(html, { dataImages: true }));
              emit();
            }}
            className="rich-email proposal-page mx-auto min-h-[28rem] max-w-3xl rounded-md border border-border/60 bg-background px-5 py-6 text-sm leading-relaxed text-foreground shadow-xs outline-none sm:px-10 sm:py-8"
          />
        </div>
      </div>
      <p className="flex items-start gap-1 text-[11px] text-muted-foreground">
        <RefreshCw className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
        <span>Type anywhere. The heading button turns a line into a heading. The shaded parts fill themselves with the latest prices, issues and numbers: click one to choose what it shows.</span>
      </p>

      <Sheet open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-xl">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle className="flex items-center gap-1.5"><Blocks className="size-4" aria-hidden="true" /> {editing ? blockLabel(editing.block.kind) : ""}</SheetTitle>
            <SheetDescription>This part fills itself from the Brain&apos;s data. Choose what it shows; the heading above it is typed on the page.</SheetDescription>
          </SheetHeader>
          {editing && (
            <div className="flex flex-col gap-3 p-4">
              <BlockCard key={editing.sid} proposalId={proposalId} block={editing.block} onChange={(b) => updateBlock(editing.sid, b)} titleId={titleId}
                rates={rates} titles={titles} brand={brand} refreshKey={refreshKey} disabled={disabled} startOpen />
            </div>
          )}
          {editing && (
            <SheetFooter className="flex-row flex-wrap border-t border-border/70">
              <Button variant="ghost" size="sm" className="gap-1" disabled={editing.index <= 0} onClick={() => changeSections(editing.sid, "up")}><ArrowUp className="size-3.5" /> Move up</Button>
              <Button variant="ghost" size="sm" className="gap-1" disabled={editing.index < 0 || editing.index >= editing.count - 1} onClick={() => changeSections(editing.sid, "down")}><ArrowDown className="size-3.5" /> Move down</Button>
              <Button variant="ghost" size="sm" className="gap-1 text-destructive" onClick={() => changeSections(editing.sid, "remove")}><Trash2 className="size-3.5" /> Remove</Button>
              <Button size="sm" className="ml-auto" onClick={() => setEditing(null)}>Done</Button>
            </SheetFooter>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
