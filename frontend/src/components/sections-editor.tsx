"use client";

import { useMemo, useState, useTransition } from "react";
import { toast } from "sonner";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { friendlyError } from "@/lib/errors";
import { saveHiddenSections } from "@/lib/sections-actions";
import type { SectionKey, SectionsInfo } from "@/lib/sections";

const ROLE_LABELS: Record<string, string> = { sales: "Sales", data_manager: "Data Manager" };
// The Hub and Data Health are never open to Sales, so there's nothing to hide for them.
const NOT_FOR_SALES: SectionKey[] = ["automations_hub", "data_health"];

/** Ticked = shown. A grid of sections × roles, saved in one go. */
export function SectionsEditor({ info }: { info: SectionsInfo }) {
  const roles = ["sales", "data_manager"].filter((r) => info.roles.includes(r));
  const [hidden, setHidden] = useState<Record<string, SectionKey[]>>(() =>
    Object.fromEntries(roles.map((r) => [r, info.hidden[r] ?? []])),
  );
  const [saved, setSaved] = useState(hidden);
  const [pending, start] = useTransition();
  const dirty = JSON.stringify(hidden) !== JSON.stringify(saved);

  const groups = useMemo(() => {
    const m = new Map<string, typeof info.sections>();
    for (const s of info.sections) m.set(s.group, [...(m.get(s.group) ?? []), s]);
    return [...m.entries()];
  }, [info]);

  function toggle(role: string, key: SectionKey, show: boolean) {
    setHidden((h) => {
      const cur = new Set(h[role] ?? []);
      if (show) cur.delete(key);
      else cur.add(key);
      return { ...h, [role]: [...cur].sort() };
    });
  }

  function save() {
    start(async () => {
      try {
        const out = await saveHiddenSections(hidden);
        const next = Object.fromEntries(roles.map((r) => [r, out.hidden[r] ?? []]));
        setHidden(next);
        setSaved(next);
        toast.success("Saved. People see the change next time a page loads.");
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save the sections"));
      }
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[32rem] text-sm">
          <caption className="sr-only">Which sections each role sees</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
              <th scope="col" className="px-4 py-2.5 font-semibold">Section</th>
              {roles.map((r) => (
                <th key={r} scope="col" className="w-32 px-3 py-2.5 text-center font-semibold">
                  {ROLE_LABELS[r]}
                </th>
              ))}
            </tr>
          </thead>
          {groups.map(([group, items]) => (
            <tbody key={group}>
              <tr className="border-b border-border/60 bg-muted/40">
                <th scope="colgroup" colSpan={roles.length + 1} className="px-4 py-1.5 text-left text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  {group}
                </th>
              </tr>
              {items.map((s) => (
                <tr key={s.key} className="border-b border-border/60 last:border-0">
                  <td className="px-4 py-2.5">
                    <div className="font-semibold text-foreground">{s.label}</div>
                    <div className="text-[11px] text-muted-foreground">{s.description}</div>
                  </td>
                  {roles.map((r) => {
                    const na = r === "sales" && NOT_FOR_SALES.includes(s.key);
                    const shown = !(hidden[r] ?? []).includes(s.key);
                    return (
                      <td key={r} className="px-3 py-2.5 text-center">
                        {na ? (
                          <span className="text-[11px] text-muted-foreground" title="Sales users can't open this section anyway">
                            Not available
                          </span>
                        ) : (
                          <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs font-medium text-foreground">
                            <input
                              type="checkbox"
                              className="size-4"
                              checked={shown}
                              disabled={pending}
                              onChange={(e) => toggle(r, s.key, e.target.checked)}
                              aria-label={`Show ${s.label} to ${ROLE_LABELS[r]} users`}
                            />
                            {shown ? "Shown" : "Hidden"}
                          </label>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <div className="flex items-center justify-end gap-3">
        {dirty && <span className="text-xs text-muted-foreground">You have unsaved changes</span>}
        <Button size="sm" className="gap-1.5" disabled={!dirty || pending} onClick={save}>
          <Save className="size-3.5" aria-hidden="true" />
          Save
        </Button>
      </div>
    </div>
  );
}
