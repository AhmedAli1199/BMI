"use client";
/* eslint-disable react-hooks/set-state-in-effect -- clearing the results
   list synchronously when the query is emptied is the correct, immediate
   behavior here, not accidental prop-mirroring. */

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { ExternalLink, X } from "lucide-react";
import { Input } from "@/components/ui/input";

type Option = { id: string; label: string; sublabel?: string | null };

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
}) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<Option[]>([]);
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState<{ top: number; left: number; width: number } | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const inputWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query.trim()) {
      setOptions([]);
      return;
    }
    const id = setTimeout(() => {
      search(query).then(setOptions);
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

  const showDropdown = open && options.length > 0 && rect;

  return (
    <div ref={inputWrapRef}>
      <Input
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
      />
      {showDropdown &&
        createPortal(
          <div
            ref={boxRef}
            style={{ position: "absolute", top: rect.top, left: rect.left, width: rect.width }}
            className="z-50 max-h-64 overflow-y-auto rounded-md border bg-popover text-popover-foreground shadow-md"
          >
            {options.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className="block w-full truncate px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                onClick={() => {
                  onChange(opt);
                  setQuery("");
                  setOptions([]);
                  setOpen(false);
                }}
              >
                {opt.label}
                {opt.sublabel && <span className="text-muted-foreground"> · {opt.sublabel}</span>}
              </button>
            ))}
          </div>,
          document.body
        )}
    </div>
  );
}
