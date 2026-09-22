import type { NoteOut } from "@/lib/types";

/** What the Notes table's "Source" column shows for one note - real
 * origin, not the "Act! Manual" literal every note used to show
 * regardless of where it actually came from. A note migrated from Act!
 * shows that; a note typed by a real person in this CRM shows their
 * name (every UI-driven note-add sets created_by_user_id from the
 * logged-in session); a note with source_db "manual" and no
 * created_by is always automation-authored - no automation in this
 * codebase ever sets created_by_user_id on a Note it writes. */
export function noteSourceLabel(note: NoteOut): string {
  if (note.source_db !== "manual") return "Act! Import";
  return note.created_by?.name || "AI / Automation";
}

const HTML_ENTITIES: Record<string, string> = {
  "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
  "&quot;": '"', "&#39;": "'", "&apos;": "'",
};

/** Strip an HTML fragment down to plain text. Act! (and Outlook, when a
 * note was pasted from an email) can store note bodies as raw HTML - e.g.
 * `<span style="font-family: 'Microsoft Sans Serif';...">text</span>` -
 * migrated verbatim, same problem as the RTF case below, different markup. */
function stripHtml(text: string): string {
  return text
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|li)>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&[a-zA-Z]+;/g, (m) => HTML_ENTITIES[m] ?? m)
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/**
 * Act! stored note bodies as RTF (Windows Rich Text Format) or raw HTML in
 * some cases, and that markup was migrated verbatim into `notes.body`. This
 * strips it down to plain, readable text for display. Not a full RTF parser
 * - just enough to turn `{\rtf1\ansi...{\fonttbl{...}}\pard\f0\fs17 Some
 * text\par}` into "Some text", which covers everything Act! actually
 * produces.
 */
export function cleanNoteBody(raw: string | null | undefined): string {
  if (!raw) return "";
  const text = raw.trim();
  if (!text.startsWith("{\\rtf")) {
    return /<[a-z][\s\S]*>/i.test(text) ? stripHtml(text) : text;
  }

  const out = text
    // Drop font table, color table, and other control groups entirely.
    .replace(/\{\\fonttbl[\s\S]*?\}\}/g, "")
    .replace(/\{\\colortbl[\s\S]*?\}/g, "")
    .replace(/\{\\\*[^{}]*\}/g, "")
    // Paragraph/line breaks become newlines.
    .replace(/\\par[d]?/g, "\n")
    .replace(/\\line/g, "\n")
    // Escaped literal characters.
    .replace(/\\'([0-9a-fA-F]{2})/g, (_, hex) => {
      try {
        return Buffer.from([parseInt(hex, 16)]).toString("latin1");
      } catch {
        return "";
      }
    })
    .replace(/\\{/g, "{")
    .replace(/\\}/g, "}")
    .replace(/\\\\/g, "\\")
    // Any remaining control words (\ansi, \deff0, \f0, \fs17, ...).
    .replace(/\\[a-zA-Z]+-?\d* ?/g, "")
    // Remaining braces used purely for grouping.
    .replace(/[{}]/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return out || text;
}
