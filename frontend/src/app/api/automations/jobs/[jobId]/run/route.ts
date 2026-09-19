import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/** Proxies a manual job run so the browser never needs BACKEND_API_KEY -
 * see backend's POST /api/automations/jobs/{id}/run. */
export async function POST(_request: Request, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const backendResponse = await fetch(`${BACKEND_API_URL}/api/automations/jobs/${jobId}/run`, {
    method: "POST",
    headers: { "X-API-Key": BACKEND_API_KEY },
  });
  const body = await backendResponse.json().catch(() => ({ detail: "Unexpected response from server" }));
  return NextResponse.json(body, { status: backendResponse.status });
}
