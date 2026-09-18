import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

const ENDPOINTS: Record<string, string> = {
  "business-card": "/api/automations/business-cards/upload",
  "returned-copy": "/api/automations/returned-copies/upload",
};

/** Client components can't call backendFetch (it'd leak BACKEND_API_KEY to
 * the browser), so this route re-attaches the key server-side and forwards
 * the multipart body straight through to the matching backend upload
 * endpoint - see business_card.py / returned_copy.py for what happens next. */
export async function POST(request: Request) {
  const { searchParams } = new URL(request.url);
  const kind = searchParams.get("kind") ?? "";
  const path = ENDPOINTS[kind];
  if (!path) {
    return NextResponse.json({ error: "Unknown upload kind" }, { status: 400 });
  }

  const formData = await request.formData();
  const backendResponse = await fetch(`${BACKEND_API_URL}${path}`, {
    method: "POST",
    headers: { "X-API-Key": BACKEND_API_KEY },
    body: formData,
  });

  const body = await backendResponse.json().catch(() => ({ error: "Unexpected response from server" }));
  return NextResponse.json(body, { status: backendResponse.status });
}
