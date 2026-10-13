import { NextResponse } from "next/server";

/** The Notetaker service posts call results here (this address is public). The signature is
 * checked by the backend, so the raw body and its signature headers are passed on untouched. */
export async function POST(request: Request) {
  const body = await request.text();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-API-Key": process.env.BACKEND_API_KEY ?? "",
  };
  for (const h of ["x-notetaker-event", "x-notetaker-delivery", "x-notetaker-timestamp", "x-notetaker-signature"]) {
    const v = request.headers.get(h);
    if (v) headers[h] = v;
  }
  try {
    const res = await fetch(`${process.env.BACKEND_API_URL ?? "http://localhost:8000"}/api/calls/webhook`, { method: "POST", headers, body, cache: "no-store" });
    return NextResponse.json({ ok: res.ok }, { status: res.ok ? 200 : res.status === 401 ? 401 : 502 });
  } catch {
    return NextResponse.json({ ok: false }, { status: 502 });
  }
}
