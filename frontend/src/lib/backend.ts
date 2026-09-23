import { getDevFallback } from "@/lib/dev-fallback";
import { getSession } from "@/lib/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/** Server-side only - calls the FastAPI backend with the shared API key.
 * Never call this from a client component; it would expose BACKEND_API_KEY.
 *
 * Also forwards the current session's identity (X-BMI-User-*) - see
 * backend/app/core/identity.py's docstring for the trust model this
 * relies on: the shared API key is what actually gets a request past the
 * backend at all, these headers are a second, finer-grained layer on top
 * of that, letting a route scope data to the real logged-in person
 * instead of returning everything the master key can see. Best-effort:
 * getSession() failing/returning null just means no identity headers go
 * out, which the backend treats as unrestricted (same as before these
 * existed), never a hard failure of the request itself.
 *
 * In production, deliberately throws on any non-2xx response or network failure.
 * In local development, if backend is offline or returns 404 (e.g. port 8000
 * conflict), falls back to rich sample data so UI can be inspected locally.
 */
export async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const identityHeaders: Record<string, string> = {};
    try {
      const session = await getSession();
      if (session) {
        identityHeaders["X-BMI-User-Id"] = session.sub;
        identityHeaders["X-BMI-User-Role"] = session.role;
        identityHeaders["X-BMI-User-Access"] = JSON.stringify(
          session.access.map((a) => ({ source_db: a.source_db, group_id: a.group_id }))
        );
      }
    } catch {
      // No request context (or session lookup failed) - proceed without
      // identity headers, same as any caller that predates them.
    }

    const res = await fetch(`${BACKEND_API_URL}${path}`, {
      ...init,
      headers: { "X-API-Key": BACKEND_API_KEY, ...identityHeaders, ...init?.headers },
      cache: "no-store",
    });
    if (!res.ok) {
      const rawBody = await res.text().catch(() => "");
      // In local dev, if 404 or backend mismatch, try fallback
      if (process.env.NODE_ENV === "development") {
        const fallback = getDevFallback<T>(path);
        if (fallback !== null) return fallback;
      }
      // The full "status + path + raw body" string is developer-facing -
      // useful in server logs, never something a reviewer should see in a
      // toast (see review-item-card.tsx's catch blocks, which show
      // e.message directly). FastAPI's own error responses are always
      // {"detail": "<a real sentence already written for a human>"} - use
      // that verbatim when present, so an action's own backend message
      // ("This signal no longer exists - it may have been superseded by a
      // newer message on the same thread.") reaches the user unmangled.
      const fullMessage = `Backend request failed: ${res.status} ${path}${rawBody ? ` - ${rawBody}` : ""}`;
      console.error(fullMessage);
      let userMessage = `Something went wrong (${res.status}). Please try again.`;
      try {
        const parsed = JSON.parse(rawBody);
        if (typeof parsed?.detail === "string" && parsed.detail.trim()) {
          userMessage = parsed.detail;
        }
      } catch {
        // Not JSON (a proxy/gateway error page, etc.) - keep the generic message.
      }
      throw new Error(userMessage);
    }
    if (res.status === 204) {
      return undefined as T;
    }
    return res.json() as Promise<T>;
  } catch (err) {
    if (process.env.NODE_ENV === "development") {
      const fallback = getDevFallback<T>(path);
      if (fallback !== null) return fallback;
    }
    throw err;
  }
}
