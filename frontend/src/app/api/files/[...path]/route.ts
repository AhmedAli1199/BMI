import { NextResponse } from "next/server";
import { getIdentityHeaders } from "@/lib/backend";
import { getSession } from "@/lib/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/** Browser <-> backend bridge for file traffic that server actions can't
 * carry well: Excel/Word downloads (contacts & group export, mail-merge
 * letters, labels, merge data) and attachment uploads. Only the paths
 * below are reachable, and the API key never leaves the server. */
const ALLOWED: RegExp[] = [
  /^contacts\/export$/,
  /^sales\/orders\/export$/,
  /^groups\/[0-9a-f-]{36}\/export$/,
  /^contact-imports$/,
  /^contact-imports\/template\.xlsx$/,
  /^contact-imports\/[0-9a-f-]{36}\/report\.xlsx$/,
  /^mail-merge$/,
  /^mail-merge\/attachments$/,
  /^mail-merge\/[0-9a-f-]{36}\/letters$/,
];

async function forward(request: Request, params: Promise<{ path: string[] }>) {
  const session = await getSession();
  if (!session) return NextResponse.json({ detail: "Not signed in" }, { status: 401 });
  const path = (await params).path.join("/");
  if (!ALLOWED.some((re) => re.test(path))) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }
  const url = new URL(request.url);
  const headers: Record<string, string> = { "X-API-Key": BACKEND_API_KEY, ...(await getIdentityHeaders()) };
  const contentType = request.headers.get("Content-Type");
  if (contentType) headers["Content-Type"] = contentType;
  const res = await fetch(`${BACKEND_API_URL}/api/${path}${url.search}`, {
    method: request.method,
    headers,
    body: request.method === "GET" ? undefined : await request.arrayBuffer(),
    cache: "no-store",
  });
  const outHeaders: Record<string, string> = {
    "Content-Type": res.headers.get("Content-Type") ?? "application/octet-stream",
  };
  const disposition = res.headers.get("Content-Disposition");
  if (disposition) outHeaders["Content-Disposition"] = disposition;
  return new Response(res.body, { status: res.status, headers: outHeaders });
}

export async function GET(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, params);
}

export async function POST(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, params);
}
