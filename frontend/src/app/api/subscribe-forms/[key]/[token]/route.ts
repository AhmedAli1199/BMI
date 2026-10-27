import { NextResponse } from "next/server";

/** The titles' subscribe forms (Wufoo, Elementor on WordPress, Stova) post each sign-up here. The address is
 * public; the token in it is that form's secret. The body is passed on untouched, so the backend can read Wufoo's
 * and Elementor's form posts or plain JSON. */
export async function POST(request: Request, { params }: { params: Promise<{ key: string; token: string }> }) {
  const { key, token } = await params;
  if (!/^[a-z-]{2,30}$/.test(key) || !/^[\w-]{10,80}$/.test(token)) return NextResponse.json({ ok: false }, { status: 404 });
  const body = await request.arrayBuffer();
  try {
    const res = await fetch(`${process.env.BACKEND_API_URL ?? "http://localhost:8000"}/api/subscription-forms/receive/${key}/${token}`, {
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
