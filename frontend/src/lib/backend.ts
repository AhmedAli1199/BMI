import { getDevFallback } from "@/lib/dev-fallback";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/** Server-side only - calls the FastAPI backend with the shared API key.
 * Never call this from a client component; it would expose BACKEND_API_KEY.
 *
 * In production, deliberately throws on any non-2xx response or network failure.
 * In local development, if backend is offline or returns 404 (e.g. port 8000
 * conflict), falls back to rich sample data so UI can be inspected locally.
 */
export async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${BACKEND_API_URL}${path}`, {
      ...init,
      headers: { "X-API-Key": BACKEND_API_KEY, ...init?.headers },
      cache: "no-store",
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      // In local dev, if 404 or backend mismatch, try fallback
      if (process.env.NODE_ENV === "development") {
        const fallback = getDevFallback<T>(path);
        if (fallback !== null) return fallback;
      }
      throw new Error(`Backend request failed: ${res.status} ${path}${detail ? ` - ${detail}` : ""}`);
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
