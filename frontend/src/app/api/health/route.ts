import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_API_URL}/api/health`, {
      headers: { "X-API-Key": BACKEND_API_KEY },
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ status: "offline" }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ status: "offline" }, { status: 502 });
  }
}
