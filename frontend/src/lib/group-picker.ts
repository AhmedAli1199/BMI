import { browseGroups, searchGroups } from "@/lib/actions";
import type { GroupListItem } from "@/lib/types";

/** What every "pick a group" box shares (Craig, feedback #3): clicking into it lists the groups straight away -
 * sub-groups indented under their parent, with member counts - and typing narrows it down. Pass to EntityPicker. */
export function groupPicker({
  sourceDb,
  exclude,
  alreadyIn,
}: {
  /** List this database's groups (e.g. the contact's own). */
  sourceDb?: string | null;
  /** Leave these out entirely (e.g. the group you're copying from). */
  exclude?: string | null;
  /** Show these greyed out as "already in this group". */
  alreadyIn?: Set<string>;
} = {}) {
  const asOption = (g: GroupListItem) => ({
    id: g.id,
    label: g.name,
    sublabel: alreadyIn?.has(g.id) ? "already in this group" : `${g.member_count.toLocaleString()} member${g.member_count === 1 ? "" : "s"}`,
    indent: Math.max(0, (g.hier_level ?? 1) - 1),
    disabled: alreadyIn?.has(g.id) ?? false,
  });
  return {
    placeholder: "Pick a group, or type to search…",
    search: async (q: string) => (await searchGroups(q)).filter((g) => g.id !== exclude).map(asOption),
    browse: async () => {
      const { items, total } = await browseGroups(sourceDb);
      const shown = items.filter((g) => g.id !== exclude);
      return {
        options: shown.map(asOption),
        note: total > items.length ? `Showing ${items.length} of ${total.toLocaleString()} groups - type to find the rest.` : undefined,
      };
    },
  };
}
