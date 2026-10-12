"use client";

import { useMemo, useState, useTransition } from "react";
import { toast } from "sonner";
import { Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { friendlyError } from "@/lib/errors";
import { saveHiddenSections } from "@/lib/sections-actions";
import type { SectionKey, SectionsInfo } from "@/lib/sections";

const ROLE_LABELS: Record<string, string> = { sales: "Sales", data_manager: "Data Manager" };
// The Hub and Data Health are never open to Sales, so there's nothing to hide for them.
const NOT_FOR_SALES: SectionKey[] = ["automations_hub", "data_health"];
const selectCls = "h-8 rounded-md border border-input bg-background px-2 text-xs";

type Col = { id: string; label: string; role: string; person: boolean };

/** Ticked = shown. A grid of sections x roles, plus a column for anyone who needs their own choice. */
export function SectionsEditor({ info }: { info: SectionsInfo }) {
  const roles = ["sales", "data_manager"].filter((r) => info.roles.includes(r));
  const start = () => ({
    roles: Object.fromEntries(roles.map((r) => [r, info.hidden[r] ?? []])) as Record<string, SectionKey[]>,
    users: { ...info.users } as Record<string, SectionKey[]>,
  });
  const [state, setState] = useState(start);
  const [saved, setSaved] = useState(state);
  const [pending, run] = useTransition();
  const dirty = JSON.stringify(state) !== JSON.stringify(saved);
  const people = new Map(info.people.map((p) => [p.id, p]));

  const cols: Col[] = [
    ...roles.map((r) => ({ id: r, label: ROLE_LABELS[r], role: r, person: false })),
    ...Object.keys(state.users)
      .filter((id) => people.has(id))
      .map((id) => ({ id, label: people.get(id)!.name, role: people.get(id)!.role, person: true })),
  ];
  const addable = info.people.filter((p) => !(p.id in state.users));

  const groups = useMemo(() => {
    const m = new Map<string, typeof info.sections>();
    for (const s of info.sections) m.set(s.group, [...(m.get(s.group) ?? []), s]);
    return [...m.entries()];
  }, [info]);

  const hiddenFor = (c: Col) => (c.person ? state.users[c.id] : state.roles[c.id]) ?? [];

  function toggle(c: Col, key: SectionKey, show: boolean) {
    setState((st) => {
      const cur = new Set(c.person ? st.users[c.id] ?? [] : st.roles[c.id] ?? []);
      if (show) cur.delete(key);
      else cur.add(key);
      const next = [...cur].sort();
      return c.person ? { ...st, users: { ...st.users, [c.id]: next } } : { ...st, roles: { ...st.roles, [c.id]: next } };
    });
  }

  function addPerson(id: string) {
    const p = people.get(id);
    if (!p) return;
    // starts from their role's choice, then changes only for them
    setState((st) => ({ ...st, users: { ...st.users, [id]: [...(st.roles[p.role] ?? [])] } }));
  }

  function removePerson(id: string) {
    setState((st) => {
      const users = { ...st.users };
      delete users[id];
      return { ...st, users };
    });
  }

  function save() {
    run(async () => {
      try {
        const out = await saveHiddenSections(state.roles, state.users);
        const next = { roles: Object.fromEntries(roles.map((r) => [r, out.hidden[r] ?? []])), users: { ...out.users } };
        setState(next);
        setSaved(next);
        toast.success("Saved. People see the change next time a page loads.");
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save the sections"));
      }
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>Someone needs something different from the rest of their role?</span>
        <select
          aria-label="Give one person their own choice"
          className={selectCls}
          value=""
          disabled={!addable.length}
          onChange={(e) => e.target.value && addPerson(e.target.value)}
        >
          <option value="">{addable.length ? "Choose a person…" : "Everyone already has a column"}</option>
          {addable.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({ROLE_LABELS[p.role] ?? p.role})
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[32rem] text-sm">
          <caption className="sr-only">Which sections each role, and anyone with their own choice, sees</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
              <th scope="col" className="px-4 py-2.5 font-semibold">Section</th>
              {cols.map((c) => (
                <th key={c.id} scope="col" className="w-32 px-3 py-2.5 text-center font-semibold">
                  <span className="inline-flex items-center gap-1">
                    {c.label}
                    {c.person && (
                      <button
                        type="button"
                        onClick={() => removePerson(c.id)}
                        className="rounded p-0.5 hover:bg-muted"
                        aria-label={`${c.label}: use their role's choice again`}
                        title="Use their role's choice again"
                      >
                        <X className="size-3" />
                      </button>
                    )}
                  </span>
                  {c.person && <span className="block text-[10px] font-normal">just them</span>}
                </th>
              ))}
            </tr>
          </thead>
          {groups.map(([group, items]) => (
            <tbody key={group}>
              <tr className="border-b border-border/60 bg-muted/40">
                <th scope="colgroup" colSpan={cols.length + 1} className="px-4 py-1.5 text-left text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  {group}
                </th>
              </tr>
              {items.map((s) => (
                <tr key={s.key} className="border-b border-border/60 last:border-0">
                  <td className="px-4 py-2.5">
                    <div className="font-semibold text-foreground">{s.label}</div>
                    <div className="text-[11px] text-muted-foreground">{s.description}</div>
                  </td>
                  {cols.map((c) => {
                    const na = c.role === "sales" && NOT_FOR_SALES.includes(s.key);
                    const shown = !hiddenFor(c).includes(s.key);
                    return (
                      <td key={c.id} className="px-3 py-2.5 text-center">
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
                              onChange={(e) => toggle(c, s.key, e.target.checked)}
                              aria-label={`Show ${s.label} to ${c.label}`}
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
