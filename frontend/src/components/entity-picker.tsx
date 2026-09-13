"use client";
/* eslint-disable react-hooks/set-state-in-effect -- clearing the results
   list synchronously when the query is emptied is the correct, immediate
   behavior here, not accidental prop-mirroring. */

import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { X } from "lucide-react";

type Option = { id: string; label: string; sublabel?: string | null };

/** Type-to-search picker for a single company/group/contact, backed by a
 * server action (see lib/actions.ts). Not a full combobox library - these
 * lists run into the tens of thousands of rows, so a plain <select> was
 * never an option; this is the minimum that actually works at that scale.
 */
export function EntityPicker({
  label,
  placeholder,
  search,
  value,
  onChange,
}: {
  label: string;
  placeholder: string;
  search: (q: string) => Promise<Option[]>;
  value: Option | null;
  onChange: (value: Option | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<Option[]>([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

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
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  if (value) {
    return (
      <div className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
        <span className="flex-1 truncate">
          {value.label}
          {value.sublabel && <span className="text-muted-foreground"> · {value.sublabel}</span>}
        </span>
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

  return (
    <div className="relative" ref={boxRef}>
      <Input
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
      />
      {open && options.length > 0 && (
        <div className="absolute z-10 mt-1 w-full rounded-md border bg-popover text-popover-foreground shadow-md">
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
        </div>
      )}
    </div>
  );
}
