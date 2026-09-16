import { NextResponse } from "next/server";
import { SESSION_COOKIE, createSessionToken } from "@/lib/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

export async function POST(request: Request) {
  const { email, password } = await request.json();

  if (!email || !password) {
    return NextResponse.json({ error: "Missing credentials" }, { status: 400 });
  }

  const backendResponse = await fetch(`${BACKEND_API_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": BACKEND_API_KEY,
    },
    body: JSON.stringify({ email, password }),
  });

  if (!backendResponse.ok) {
    // Pass the backend's own reason through (e.g. "This account has been
    // disabled") rather than a blanket message - only real risk of
    // leaking anything is confirming an email exists, which login forms
    // already do via "wrong password" vs "no such account" timing/shape
    // in practice, so this isn't a meaningfully worse disclosure.
    const detail = await backendResponse.json().catch(() => null);
    return NextResponse.json({ error: detail?.detail ?? "Invalid email or password" }, { status: 401 });
  }

  const user = await backendResponse.json();
  const token = await createSessionToken({
    sub: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    access: user.access ?? [],
  });

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return response;
}
