/** Client-side file downloads through /api/files (see that route). */

function filenameFrom(res: Response, fallback: string): string {
  const cd = res.headers.get("Content-Disposition") ?? "";
  const m = /filename="?([^";]+)"?/i.exec(cd);
  return m ? decodeURIComponent(m[1]) : fallback;
}

async function errorText(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // not JSON
  }
  return `Download failed (${res.status})`;
}

export async function downloadFile(url: string, fallbackName: string, init?: RequestInit): Promise<void> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(await errorText(res));
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filenameFrom(res, fallbackName);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 2000);
}

export function postJson(body: unknown): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

/** Hands a set of contacts to the mail-merge page (too many for a URL). */
export const MERGE_SELECTION_KEY = "bmi-mail-merge-selection";

export function stashMergeSelection(ids: string[], label: string) {
  try {
    sessionStorage.setItem(MERGE_SELECTION_KEY, JSON.stringify({ ids, label }));
  } catch {
    // storage blocked - the merge page falls back to "choose contacts"
  }
}
