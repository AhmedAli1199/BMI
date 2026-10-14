"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { Bold, Columns3, Eraser, Heading2, Highlighter, ImagePlus, Italic, Link2, List, ListOrdered, Rows3, Table, Underline } from "lucide-react";
import { normaliseEditorHtml, sanitizeHtml, textToHtml } from "@/lib/rich-text";

export type RichEmailEditorHandle = { insertText: (text: string) => void; focus: () => void };

// Email colours: these are written into the email itself, so they're fixed values, not theme tokens.
const HIGHLIGHTS = [
  { label: "Yellow highlight", value: "#fff59d" },
  { label: "Green highlight", value: "#c8f7c5" },
  { label: "Blue highlight", value: "#cfe8ff" },
];
const TEXT_COLOURS = [
  { label: "Red text", value: "#c62828" },
  { label: "Blue text", value: "#1565c0" },
  { label: "Green text", value: "#2e7d32" },
];

/**
 * A simple formatting editor for email bodies: bold, italic, underline, highlight, text colour,
 * lists and links. Its value is HTML; older plain-text bodies (with **bold** marks) are turned
 * into HTML when loaded.
 */
export const RichEmailEditor = forwardRef<RichEmailEditorHandle, {
  value: string;
  onChange: (html: string) => void;
  onFocus?: () => void;
  minHeight?: string;
  id?: string;
  ariaLabel?: string;
  /** Table and picture buttons (proposals). Pictures are kept in the text, shrunk to at most 1200px wide. */
  rich?: boolean;
  disabled?: boolean;
}>(function RichEmailEditor({ value, onChange, onFocus, minHeight = "16rem", id, ariaLabel = "Email", rich = false, disabled = false }, ref) {
  const el = useRef<HTMLDivElement>(null);
  const lastHtml = useRef<string | null>(null);
  const saved = useRef<Range | null>(null);

  // Load the value whenever it changes from outside (a template is picked, a draft arrives).
  useEffect(() => {
    if (!el.current || value === lastHtml.current) return;
    const html = sanitizeHtml(textToHtml(value), { dataImages: rich });
    el.current.innerHTML = html;
    lastHtml.current = value;
  }, [value, rich]);

  function emit() {
    if (!el.current) return;
    const html = normaliseEditorHtml(el.current.innerHTML);
    lastHtml.current = html;
    onChange(html);
  }

  function saveSelection() {
    const sel = window.getSelection();
    if (sel && sel.rangeCount && el.current?.contains(sel.anchorNode)) saved.current = sel.getRangeAt(0).cloneRange();
  }

  useImperativeHandle(ref, () => ({
    insertText(text: string) {
      el.current?.focus();
      const sel = window.getSelection();
      if (saved.current && sel) { sel.removeAllRanges(); sel.addRange(saved.current); }
      if (!saved.current && el.current) {
        // No cursor yet: put it at the end.
        const r = document.createRange();
        r.selectNodeContents(el.current);
        r.collapse(false);
        sel?.removeAllRanges(); sel?.addRange(r);
      }
      document.execCommand("insertText", false, text);
      saveSelection();
      emit();
    },
    focus: () => el.current?.focus(),
  }));

  return (
    <div className="overflow-hidden rounded-lg border border-input font-normal text-foreground focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 dark:bg-input/30">
      {!disabled && <RichToolbar targetRef={el} savedRef={saved} onChange={emit} rich={rich} />}
      <div
        ref={el}
        id={id}
        role="textbox"
        aria-multiline="true"
        aria-label={ariaLabel}
        contentEditable={!disabled}
        suppressContentEditableWarning
        onInput={emit}
        onKeyUp={saveSelection}
        onMouseUp={saveSelection}
        onBlur={saveSelection}
        onFocus={onFocus}
        onPaste={(e) => {
          const html = e.clipboardData.getData("text/html");
          if (!html) return;
          e.preventDefault();
          document.execCommand("insertHTML", false, sanitizeHtml(html, { dataImages: rich }));
          emit();
        }}
        className="rich-email max-w-none overflow-y-auto bg-background px-3 py-2.5 text-sm leading-relaxed outline-none"
        style={{ minHeight }}
      />
    </div>
  );
});

/**
 * The formatting buttons: bold, italic, underline, highlight, text colour, lists, links, and (rich) tables and
 * pictures. Works on whichever editable box it's given, so one toolbar can serve a whole page.
 */
export function RichToolbar({ targetRef, savedRef, onChange, rich = false, headings = false, extra, className = "" }: {
  targetRef: React.RefObject<HTMLDivElement | null>;
  savedRef: React.RefObject<Range | null>;
  onChange: () => void;
  rich?: boolean;
  /** A "Heading" button (proposals: each heading starts a section). */
  headings?: boolean;
  extra?: React.ReactNode;
  className?: string;
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  function saveSelection() {
    const sel = window.getSelection();
    if (sel && sel.rangeCount && targetRef.current?.contains(sel.anchorNode)) savedRef.current = sel.getRangeAt(0).cloneRange();
  }

  function restoreSelection() {
    targetRef.current?.focus();
    const sel = window.getSelection();
    if (savedRef.current && sel) { sel.removeAllRanges(); sel.addRange(savedRef.current); }
  }

  function exec(cmd: string, arg?: string) {
    restoreSelection();
    document.execCommand("styleWithCSS", false, "true");
    document.execCommand(cmd, false, arg);
    saveSelection();
    onChange();
  }

  function toggleHeading() {
    const node = savedRef.current?.startContainer ?? null;
    const at = node && (node.nodeType === 1 ? (node as Element) : node.parentElement);
    exec("formatBlock", at?.closest("h2") ? "p" : "h2");
  }

  function insertTable() {
    const ask = window.prompt("How many rows and columns? For example 3 x 3", "3 x 3");
    const m = ask?.match(/(\d+)\s*[x×,]\s*(\d+)/i);
    if (!m) return;
    const rows = Math.min(30, Math.max(1, Number(m[1]))), cols = Math.min(8, Math.max(1, Number(m[2])));
    const cell = (tag: string) => `<${tag}>&nbsp;</${tag}>`;
    const head = `<tr>${Array.from({ length: cols }, () => cell("th")).join("")}</tr>`;
    const body = Array.from({ length: rows - 1 }, () => `<tr>${Array.from({ length: cols }, () => cell("td")).join("")}</tr>`).join("");
    exec("insertHTML", `<table><tbody>${head}${body}</tbody></table><p><br></p>`);
  }

  /** The table cell the cursor is in. */
  function currentCell(): HTMLTableCellElement | null {
    const node = savedRef.current?.startContainer ?? null;
    const elNode = node && (node.nodeType === 1 ? (node as Element) : node.parentElement);
    const c = elNode?.closest("td, th") as HTMLTableCellElement | null;
    return c && targetRef.current?.contains(c) ? c : null;
  }

  function addRow() {
    const c = currentCell();
    if (!c) return;
    const row = c.parentElement as HTMLTableRowElement;
    const copy = row.cloneNode(true) as HTMLTableRowElement;
    copy.querySelectorAll("td, th").forEach((x) => { const td = document.createElement("td"); td.innerHTML = "&nbsp;"; x.replaceWith(td); });
    row.after(copy);
    onChange();
  }

  function addColumn() {
    const c = currentCell();
    if (!c) return;
    const index = c.cellIndex;
    c.closest("table")?.querySelectorAll("tr").forEach((tr) => {
      const ref = tr.children[index];
      const add = document.createElement(ref?.tagName.toLowerCase() === "th" ? "th" : "td");
      add.innerHTML = "&nbsp;";
      if (ref) ref.after(add); else tr.append(add);
    });
    onChange();
  }

  function insertPicture(file: File) {
    if (!/^image\/(png|jpe?g|gif)$/.test(file.type)) { window.alert("Choose a PNG, JPG or GIF picture."); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, 1200 / img.width);
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext("2d")?.drawImage(img, 0, 0, canvas.width, canvas.height);
        const data = file.type === "image/png" && file.size < 400_000 ? String(reader.result) : canvas.toDataURL("image/jpeg", 0.85);
        exec("insertHTML", `<img src="${data}" width="${Math.min(600, canvas.width)}" alt="${file.name.replace(/"/g, "")}">`);
      };
      img.src = String(reader.result);
    };
    reader.readAsDataURL(file);
  }

  const btn = "inline-flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground";
  const keep = (e: React.MouseEvent) => e.preventDefault();   // keep the text selected while clicking the toolbar


  return (
    <div role="toolbar" aria-label="Formatting" className={`flex flex-wrap items-center gap-0.5 border-b border-border/70 bg-muted/30 px-1.5 py-1 ${className}`}>
      {headings && <>
        <button type="button" className={`${btn} w-auto px-1.5 text-xs font-bold`} onMouseDown={keep} onClick={toggleHeading} title="Make this line a heading (or back to text)" aria-label="Heading"><Heading2 className="size-3.5" /></button>
        <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
      </>}
      <button type="button" className={btn} onMouseDown={keep} onClick={() => exec("bold")} title="Bold (Ctrl+B)" aria-label="Bold"><Bold className="size-3.5" /></button>
      <button type="button" className={btn} onMouseDown={keep} onClick={() => exec("italic")} title="Italic (Ctrl+I)" aria-label="Italic"><Italic className="size-3.5" /></button>
      <button type="button" className={btn} onMouseDown={keep} onClick={() => exec("underline")} title="Underline (Ctrl+U)" aria-label="Underline"><Underline className="size-3.5" /></button>
      <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
      <Highlighter className="ml-1 size-3.5 text-muted-foreground" aria-hidden="true" />
      {HIGHLIGHTS.map((h) => (
        <button key={h.value} type="button" className={btn} onMouseDown={keep} onClick={() => exec("hiliteColor", h.value)} title={h.label} aria-label={h.label}>
          <span className="size-4 rounded-sm border border-border" style={{ background: h.value }} />
        </button>
      ))}
      <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
      {TEXT_COLOURS.map((c) => (
        <button key={c.value} type="button" className={btn} onMouseDown={keep} onClick={() => exec("foreColor", c.value)} title={c.label} aria-label={c.label}>
          <span className="text-sm font-bold" style={{ color: c.value }}>A</span>
        </button>
      ))}
      <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
      <button type="button" className={btn} onMouseDown={keep} onClick={() => exec("insertUnorderedList")} title="Bullet list" aria-label="Bullet list"><List className="size-3.5" /></button>
      <button type="button" className={btn} onMouseDown={keep} onClick={() => exec("insertOrderedList")} title="Numbered list" aria-label="Numbered list"><ListOrdered className="size-3.5" /></button>
      <button type="button" className={btn} onMouseDown={keep} onClick={() => {
        saveSelection();
        const url = window.prompt("Link to (web address)", "https://");
        if (url && url !== "https://") exec("createLink", /^(https?:|mailto:|\{\{)/i.test(url) ? url : `https://${url}`);
      }} title="Add a link" aria-label="Add a link"><Link2 className="size-3.5" /></button>
      <button type="button" className={btn} onMouseDown={keep} onClick={() => { exec("removeFormat"); exec("unlink"); }} title="Clear formatting" aria-label="Clear formatting"><Eraser className="size-3.5" /></button>
      {rich && <>
        <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
        <button type="button" className={btn} onMouseDown={keep} onClick={insertTable} title="Insert a table" aria-label="Insert a table"><Table className="size-3.5" /></button>
        <button type="button" className={btn} onMouseDown={keep} onClick={addRow} title="Add a row below (click in the table first)" aria-label="Add a row"><Rows3 className="size-3.5" /></button>
        <button type="button" className={btn} onMouseDown={keep} onClick={addColumn} title="Add a column to the right (click in the table first)" aria-label="Add a column"><Columns3 className="size-3.5" /></button>
        <button type="button" className={btn} onMouseDown={(e) => { keep(e); saveSelection(); }} onClick={() => fileRef.current?.click()} title="Insert a picture" aria-label="Insert a picture"><ImagePlus className="size-3.5" /></button>
        <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/gif" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) insertPicture(f); e.target.value = ""; }} />
      </>}
      {extra}
    </div>
  );
}

/** Shows an email body (HTML or plain text) the way it will look. Filled in the browser, where it can be cleaned safely. */
export function EmailBodyView({ body, className = "", dataImages = false }: { body: string; className?: string; dataImages?: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { if (box.current) box.current.innerHTML = sanitizeHtml(textToHtml(body), { dataImages }); }, [body, dataImages]);
  return <div ref={box} className={`rich-email ${className}`} />;
}
