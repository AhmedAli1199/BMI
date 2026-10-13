import { NextResponse } from "next/server";

/** Online booking forms (Jotform, Stova) post each entry here (this address is public; the token in it is the
 * form's secret). The body is passed on untouched, so the backend can read Jotform's form post or plain JSON. */
export async function POST(request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!/^[\w-]{10,80}$/.test(token)) return NextResponse.json({ ok: false }, { status: 404 });
  const body = await request.arrayBuffer();
  try {
    const res = await fetch(`${process.env.BACKEND_API_URL ?? "http://localhost:8000"}/api/sales/booking-forms/receive/${token}`, {
      method: "POST",
      headers: { "Content-Type": request.headers.get("content-type") ?? "application/json", "X-API-Key": process.env.BACKEND_API_KEY ?? "" },
      body,
      cache: "no-store",
    });
    return NextResponse.json({ ok: res.ok }, { status: res.ok ? 200 : res.status === 404 ? 404 : res.status === 422 ? 422 : 502 });
  } catch {
    return NextResponse.json({ ok: false }, { status: 502 });
  }
}
