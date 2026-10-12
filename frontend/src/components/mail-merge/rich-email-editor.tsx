"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { Bold, Eraser, Highlighter, Italic, Link2, List, ListOrdered, Underline } from "lucide-react";
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
}>(function RichEmailEditor({ value, onChange, onFocus, minHeight = "16rem", id, ariaLabel = "Email" }, ref) {
  const el = useRef<HTMLDivElement>(null);
  const lastHtml = useRef<string | null>(null);
  const saved = useRef<Range | null>(null);

  // Load the value whenever it changes from outside (a template is picked, a draft arrives).
  useEffect(() => {
    if (!el.current || value === lastHtml.current) return;
    const html = sanitizeHtml(textToHtml(value));
    el.current.innerHTML = html;
    lastHtml.current = value;
  }, [value]);

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

  function restoreSelection() {
    el.current?.focus();
    const sel = window.getSelection();
    if (saved.current && sel) { sel.removeAllRanges(); sel.addRange(saved.current); }
  }

  function exec(cmd: string, arg?: string) {
    restoreSelection();
    document.execCommand("styleWithCSS", false, "true");
    document.execCommand(cmd, false, arg);
    saveSelection();
    emit();
  }

  useImperativeHandle(ref, () => ({
    insertText(text: string) {
      restoreSelection();
      if (!saved.current && el.current) {
        // No cursor yet: put it at the end.
        const r = document.createRange();
        r.selectNodeContents(el.current);
        r.collapse(false);
        const sel = window.getSelection();
        sel?.removeAllRanges(); sel?.addRange(r);
      }
      document.execCommand("insertText", false, text);
      saveSelection();
      emit();
    },
    focus: () => el.current?.focus(),
  }));

  const btn = "inline-flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground";
  const keep = (e: React.MouseEvent) => e.preventDefault();   // keep the text selected while clicking the toolbar

  return (
    <div className="overflow-hidden rounded-lg border border-input font-normal text-foreground focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 dark:bg-input/30">
      <div role="toolbar" aria-label="Formatting" className="flex flex-wrap items-center gap-0.5 border-b border-border/70 bg-muted/30 px-1.5 py-1">
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
      </div>
      <div
        ref={el}
        id={id}
        role="textbox"
        aria-multiline="true"
        aria-label={ariaLabel}
        contentEditable
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
          document.execCommand("insertHTML", false, sanitizeHtml(html));
          emit();
        }}
        className="rich-email max-w-none overflow-y-auto bg-background px-3 py-2.5 text-sm leading-relaxed outline-none"
        style={{ minHeight }}
      />
    </div>
  );
});

/** Shows an email body (HTML or plain text) the way it will look. Filled in the browser, where it can be cleaned safely. */
export function EmailBodyView({ body, className = "" }: { body: string; className?: string }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { if (box.current) box.current.innerHTML = sanitizeHtml(textToHtml(body)); }, [body]);
  return <div ref={box} className={`rich-email ${className}`} />;
}
