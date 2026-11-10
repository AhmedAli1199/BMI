"use client";
/* eslint-disable react-hooks/set-state-in-effect -- clearing the results
   list synchronously when the query is emptied is the correct, immediate
   behavior here, not accidental prop-mirroring. */

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { ExternalLink, Loader2, Plus, X } from "lucide-react";
import { Input } from "@/components/ui/input";

type Option = { id: string; label: string; sublabel?: string | null; /** sub-group depth, for indenting */ indent?: number; /** shown but can't be picked (e.g. already a member) */ disabled?: boolean };

/** Type-to-search picker for a single company/group/contact, backed by a
 * server action (see lib/actions.ts). Not a full combobox library - these
 * lists run into the tens of thousands of rows, so a plain <select> was
 * never an option; this is the minimum that actually works at that scale.
 *
 * The results dropdown is portaled to document.body and positioned by
 * the input's own bounding rect, rather than an absolutely-positioned
 * child of this component - every shadcn Card (and several other
 * containers in this app) ships with `overflow-hidden` on its base
 * class, so a plain in-flow absolute dropdown gets silently clipped to
 * a sliver the moment it's used inside one (e.g. the contact page's
 * "Add to group" picker, inside a Card). Portaling escapes that
 * entirely, for every use of this component at once.
 */
export function EntityPicker({
  label,
  placeholder,
  search,
  value,
  onChange,
  viewHref,
  browse,
  onCreate,
}: {
  label: string;
  placeholder: string;
  search: (q: string) => Promise<Option[]>;
  value: Option | null;
  onChange: (value: Option | null) => void;
  /** When set, a selected value gets a "View" link (opens in a new tab) to
   * this record's own page - e.g. `(id) => `/contacts/${id}``. Optional
   * since this picker is also used for things with no detail page of
   * their own (groups). */
  viewHref?: (id: string) => string;
  /** Clicking into the empty box shows this list straight away (e.g. every group), so people
   * don't need to remember a name. Typing still searches. */
  browse?: () => Promise<{ options: Option[]; note?: string }>;
  /** Offers "+ Create … '<typed text>'" at the end of the list, so a name that isn't there yet
   * isn't lost. Returns the new record, which is then picked. */
  onCreate?: (text: string) => Promise<Option>;
}) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<Option[]>([]);
  const [searchedFor, setSearchedFor] = useState("");   // the text the current results are for
  const [open, setOpen] = useState(false);
  const [browsed, setBrowsed] = useState<{ options: Option[]; note?: string } | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [rect, setRect] = useState<{ top: number; left: number; width: number } | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const inputWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query.trim()) {
      setOptions([]);
      return;
    }
    const id = setTimeout(() => {
      search(query).then((found) => {
        setOptions(found);
        setSearchedFor(query);
      });
    }, 220);
    return () => clearTimeout(id);
  }, [query, search]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      if (boxRef.current?.contains(target)) return;
      if (inputWrapRef.current?.contains(target)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  // Recomputes the dropdown's floating position from the input's real
  // on-screen location whenever it opens, and keeps it glued there
  // through scroll/resize while open - a portal has no natural
  // relationship to the input's position otherwise.
  useLayoutEffect(() => {
    if (!open) return;
    function updateRect() {
      const el = inputWrapRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      setRect({ top: r.bottom + window.scrollY + 4, left: r.left + window.scrollX, width: r.width });
    }
    updateRect();
    window.addEventListener("scroll", updateRect, true);
    window.addEventListener("resize", updateRect);
    return () => {
      window.removeEventListener("scroll", updateRect, true);
      window.removeEventListener("resize", updateRect);
    };
  }, [open]);

  function pick(opt: Option) {
    if (opt.disabled) return;
    onChange(opt);
    setQuery("");
    setOptions([]);
    setOpen(false);
  }

  async function create() {
    if (!onCreate || !query.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      pick(await onCreate(query.trim()));
    } catch {
      setCreateError(`Couldn't create that ${label}. Please try again.`);
    } finally {
      setCreating(false);
    }
  }

  function openList() {
    setOpen(true);
    if (browse && !browsed) browse().then(setBrowsed).catch(() => setBrowsed({ options: [] }));
  }

  if (value) {
    return (
      <div className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
        <span className="flex-1 truncate">
          {value.label}
          {value.sublabel && <span className="text-muted-foreground"> · {value.sublabel}</span>}
        </span>
        {viewHref && (
          <Link
            href={viewHref(value.id)}
            target="_blank"
            rel="noopener noreferrer"
            title={`Open this ${label}'s full details in a new tab`}
            className="flex shrink-0 items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="size-3.5" />
            View
          </Link>
        )}
        <button
          type="button"
          onClick={() => onChange(null)}
          className="text-muted-foreground hover:text-foreground"
          aria-label={`Clear ${label}`}
        >
          <X className="size-4" />
        </button>
      </div>
    );
  }

  const typed = query.trim();
  const list = typed ? options : browsed?.options ?? [];
  const exact = typed && options.some((o) => o.label.trim().toLowerCase() === typed.toLowerCase());
  // Only once the search for exactly this text has come back, so "Create" never races an existing match.
  const offerCreate = !!onCreate && !!typed && searchedFor === query && !exact;
  const searching = !!typed && searchedFor !== query;
  const showDropdown = open && rect && (list.length > 0 || offerCreate || (!typed && browse) || (searching && onCreate));

  return (
    <div ref={inputWrapRef}>
      <Input
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={openList}
        onClick={openList}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "Enter" && offerCreate && options.length === 0 && !creating) {
            e.preventDefault();
            void create();
          }
        }}
      />
      {createError && <p className="mt-1 text-[11px] text-destructive">{createError}</p>}
      {typed && !open && !createError && (
        <p className="mt-1 text-[11px] text-[var(--warn)]">
          Not saved yet - pick a {label} from the list{onCreate ? ` or choose “Create ${label}”` : ""}.
        </p>
      )}
      {showDropdown &&
        createPortal(
          <div
            ref={boxRef}
            style={{ position: "absolute", top: rect.top, left: rect.left, width: rect.width }}
            className="z-50 max-h-72 overflow-y-auto rounded-md border bg-popover text-popover-foreground shadow-md"
          >
            {!typed && browse && !browsed && (
              <p className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" /> Loading…
              </p>
            )}
            {searching && onCreate && list.length === 0 && (
              <p className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" /> Searching…
              </p>
            )}
            {list.map((opt) => (
              <button
                key={opt.id}
                type="button"
                disabled={opt.disabled}
                style={opt.indent ? { paddingLeft: `${0.75 + opt.indent * 0.9}rem` } : undefined}
                className="block w-full truncate px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground disabled:cursor-default disabled:opacity-50 disabled:hover:bg-transparent"
                onClick={() => pick(opt)}
              >
                {opt.label}
                {opt.sublabel && <span className="text-muted-foreground"> · {opt.sublabel}</span>}
              </button>
            ))}
            {!typed && browsed && browsed.options.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">Nothing to choose from yet.</p>
            )}
            {!typed && browsed?.note && <p className="border-t border-border px-3 py-1.5 text-[11px] text-muted-foreground">{browsed.note}</p>}
            {offerCreate && (
              <button
                type="button"
                disabled={creating}
                className="flex w-full items-center gap-2 border-t border-border px-3 py-2 text-left text-sm font-medium text-primary hover:bg-accent disabled:opacity-60"
                onClick={() => void create()}
              >
                {creating ? <Loader2 className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />}
                Create {label} “{typed}”
              </button>
            )}
          </div>,
          document.body
        )}
    </div>
  );
}
