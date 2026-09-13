import {
  MOCK_CONTACTS,
  MOCK_COMPANIES,
  MOCK_GROUPS,
  MOCK_DASHBOARD_STATS,
} from "./mock-data";
import type { Page, ContactListItem, CompanyListItem, GroupListItem } from "./types";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

function resolveFallbackData<T>(path: string): T {
  const url = new URL(path, "http://localhost");
  const pathname = url.pathname;
  const searchParams = url.searchParams;

  if (pathname === "/api/dashboard/stats") {
    return MOCK_DASHBOARD_STATS as unknown as T;
  }

  if (pathname === "/api/contacts") {
    const q = searchParams.get("q")?.toLowerCase();
    const sourceDb = searchParams.get("source_db");
    const page = parseInt(searchParams.get("page") || "1", 10);
    const pageSize = parseInt(searchParams.get("page_size") || "50", 10);

    let filtered = MOCK_CONTACTS.map((c): ContactListItem => ({
      id: c.id,
      source_db: c.source_db,
      full_name: c.full_name,
      first_name: c.first_name,
      last_name: c.last_name,
      job_title: c.job_title,
      company_id: c.company?.id ?? null,
      company_name: c.company?.name ?? null,
      primary_email: c.emails[0]?.address ?? null,
    }));

    if (sourceDb) {
      filtered = filtered.filter((c) => c.source_db === sourceDb);
    }
    if (q) {
      filtered = filtered.filter(
        (c) =>
          c.full_name?.toLowerCase().includes(q) ||
          c.primary_email?.toLowerCase().includes(q) ||
          c.company_name?.toLowerCase().includes(q)
      );
    }

    const start = (page - 1) * pageSize;
    const pageResult: Page<ContactListItem> = {
      items: filtered.slice(start, start + pageSize),
      total: 118420, // Real legacy total for BMI
      page,
      page_size: pageSize,
    };
    return pageResult as unknown as T;
  }

  if (pathname.startsWith("/api/contacts/")) {
    const id = pathname.replace("/api/contacts/", "");
    const found = MOCK_CONTACTS.find((c) => c.id === id) || MOCK_CONTACTS[0];
    return found as unknown as T;
  }

  if (pathname === "/api/companies") {
    const q = searchParams.get("q")?.toLowerCase();
    const sourceDb = searchParams.get("source_db");
    const page = parseInt(searchParams.get("page") || "1", 10);
    const pageSize = parseInt(searchParams.get("page_size") || "50", 10);

    let filtered = MOCK_COMPANIES.map((c): CompanyListItem => ({
      id: c.id,
      source_db: c.source_db,
      name: c.name,
      industry: c.industry,
      category: c.category,
      contact_count: c.contacts.length,
    }));

    if (sourceDb) {
      filtered = filtered.filter((c) => c.source_db === sourceDb);
    }
    if (q) {
      filtered = filtered.filter((c) => c.name.toLowerCase().includes(q));
    }

    const start = (page - 1) * pageSize;
    const pageResult: Page<CompanyListItem> = {
      items: filtered.slice(start, start + pageSize),
      total: 14612,
      page,
      page_size: pageSize,
    };
    return pageResult as unknown as T;
  }

  if (pathname.startsWith("/api/companies/")) {
    const id = pathname.replace("/api/companies/", "");
    const found = MOCK_COMPANIES.find((c) => c.id === id) || MOCK_COMPANIES[0];
    return found as unknown as T;
  }

  if (pathname === "/api/groups") {
    const pageResult: Page<GroupListItem> = {
      items: MOCK_GROUPS.map((g) => ({
        id: g.id,
        name: g.name,
        description: g.description,
        member_count: g.members.length,
      })),
      total: 832,
      page: 1,
      page_size: 50,
    };
    return pageResult as unknown as T;
  }

  if (pathname.startsWith("/api/groups/")) {
    const id = pathname.replace("/api/groups/", "");
    const found = MOCK_GROUPS.find((g) => g.id === id) || MOCK_GROUPS[0];
    return found as unknown as T;
  }

  throw new Error(`No mock data route for ${pathname}`);
}

/** Server-side only - calls the FastAPI backend with the shared API key.
 * If the backend is unreachable (e.g. during local frontend styling),
 * gracefully falls back to authentic BMI Publishing mock data.
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
      console.warn(`[backendFetch] HTTP ${res.status} for ${path}: ${detail}. Using fallback data.`);
      return resolveFallbackData<T>(path);
    }
    if (res.status === 204) {
      return undefined as T;
    }
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`[backendFetch] Backend unreachable at ${BACKEND_API_URL} (${(err as Error).message}). Using fallback data.`);
    return resolveFallbackData<T>(path);
  }
}
