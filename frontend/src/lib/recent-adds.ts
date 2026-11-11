/** Companies and contacts you've just added, pinned at the top of their list until you sign out (Craig, feedback #18).
 * Kept in this browser only; cleared on sign-out and after a day. */
export type RecentKind = "company" | "contact";
export type RecentAdd = { id: string; name: string; at: number };

const KEY = (k: RecentKind) => `bmi.recent-adds.${k}`;
const DAY = 24 * 60 * 60 * 1000;
export const RECENT_CHANGED = "bmi-recent-adds-changed";

export function listRecent(kind: RecentKind): RecentAdd[] {
  try {
    const items = JSON.parse(window.localStorage.getItem(KEY(kind)) || "[]") as RecentAdd[];
    return items.filter((i) => i && i.id && Date.now() - i.at < DAY);
  } catch {
    return [];
  }
}

function save(kind: RecentKind, items: RecentAdd[]) {
  try {
    window.localStorage.setItem(KEY(kind), JSON.stringify(items.slice(0, 20)));
    window.dispatchEvent(new Event(RECENT_CHANGED));
  } catch {
    /* private window */
  }
}

export function addRecent(kind: RecentKind, id: string, name: string) {
  save(kind, [{ id, name: name || "(no name)", at: Date.now() }, ...listRecent(kind).filter((i) => i.id !== id)]);
}

export function removeRecent(kind: RecentKind, id: string) {
  save(kind, listRecent(kind).filter((i) => i.id !== id));
}

export function clearRecent() {
  try {
    for (const k of ["company", "contact"] as RecentKind[]) window.localStorage.removeItem(KEY(k));
  } catch {
    /* private window */
  }
}
