const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/** Server-side only - calls the FastAPI backend with the shared API key.
 * Never call this from a client component; it would expose BACKEND_API_KEY.
 */
export async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_API_URL}${path}`, {
    ...init,
    headers: { "X-API-Key": BACKEND_API_KEY, ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend request failed: ${res.status} ${path}`);
  }
  return res.json() as Promise<T>;
}
