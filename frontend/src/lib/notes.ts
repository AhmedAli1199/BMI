/**
 * Act! stored note bodies as RTF (Windows Rich Text Format) in some cases,
 * and that raw markup was migrated verbatim into `notes.body`. This strips
 * it down to plain, readable text for display. Not a full RTF parser - just
 * enough to turn `{\rtf1\ansi...{\fonttbl{...}}\pard\f0\fs17 Some text\par}`
 * into "Some text", which covers everything Act! actually produces.
 */
export function cleanNoteBody(raw: string | null | undefined): string {
  if (!raw) return "";
  const text = raw.trim();
  if (!text.startsWith("{\\rtf")) return text;

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
