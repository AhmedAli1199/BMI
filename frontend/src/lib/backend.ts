const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/** Server-side only - calls the FastAPI backend with the shared API key.
 * Never call this from a client component; it would expose BACKEND_API_KEY.
 *
 * Deliberately throws (never silently substitutes placeholder data) on any
 * non-2xx response or network failure - callers rely on that to show a
 * proper 404/error state (see contacts/[id]/page.tsx's try/catch ->
 * notFound()). A real CRM must never render fabricated content in place of
 * a failed request with no indication it isn't real: a visitor could act on
 * (or a rep could quote to a client) invented data believing it came from
 * the actual database, and a temporary backend hiccup or a genuinely
 * deleted record would look identical to a normal page load instead of
 * surfacing the failure.
 */
export async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_API_URL}${path}`, {
    ...init,
    headers: { "X-API-Key": BACKEND_API_KEY, ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Backend request failed: ${res.status} ${path}${detail ? ` - ${detail}` : ""}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}
