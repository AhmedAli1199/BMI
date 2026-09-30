import type { ReactNode } from "react";

/** Wraps every case-insensitive occurrence of `term` in `text` with <mark>,
 * so a search result also shows exactly why it matched - "surfaces that
 * instance" - instead of just being present in an otherwise-identical list.
 * Returns `text` unchanged when there's no term or no match. */
export function highlightMatch(text: string, term: string): ReactNode {
  const needle = term.trim();
  if (!needle) return text;

  const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  if (parts.length === 1) return text;

  return parts.map((part, i) =>
    part.toLowerCase() === needle.toLowerCase() ? (
      <mark key={i} className="rounded-sm bg-primary/25 px-0.5 text-foreground">
        {part}
      </mark>
    ) : (
      part
    )
  );
}
