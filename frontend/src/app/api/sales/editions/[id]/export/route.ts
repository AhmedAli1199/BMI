import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/** Streams an edition's .xlsx export (the SOR sheet layout) to the
 * browser without exposing BACKEND_API_KEY - see backend's
 * GET /api/sales/editions/{id}/export. */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const session = await getSession();
  if (!session) return NextResponse.json({ detail: "Not signed in" }, { status: 401 });
  const { id } = await params;
  const res = await fetch(`${BACKEND_API_URL}/api/sales/editions/${encodeURIComponent(id)}/export`, {
    headers: { "X-API-Key": BACKEND_API_KEY },
    cache: "no-store",
  });
  if (!res.ok || !res.body) {
    return NextResponse.json({ detail: "Couldn't export this edition" }, { status: res.status || 502 });
  }
  return new Response(res.body, {
    headers: {
      "Content-Type": res.headers.get("Content-Type") ?? "application/octet-stream",
      "Content-Disposition": res.headers.get("Content-Disposition") ?? 'attachment; filename="edition.xlsx"',
    },
  });
}
