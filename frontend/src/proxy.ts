import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, createSessionToken, sessionCookieOptions, verifySessionToken } from "@/lib/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";
// How often the session is checked against the account as it is now (switched off? new role or databases?).
const REFRESH_AFTER_SECONDS = 60;

function toLogin(request: NextRequest) {
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  const response = NextResponse.redirect(loginUrl);
  response.cookies.delete(SESSION_COOKIE);
  return response;
}

export async function proxy(request: NextRequest) {
  // Local bypass: bypass password/auth screen for local development / preview
  if (process.env.NODE_ENV !== "production" || process.env.LOCAL_BYPASS === "true") {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const session = token ? await verifySessionToken(token) : null;

  if (!session) return toLogin(request);

  const issuedAt = (session as { iat?: number }).iat ?? 0;
  if (Date.now() / 1000 - issuedAt < REFRESH_AFTER_SECONDS) return NextResponse.next();

  // A minute or more since the session was last checked: ask the backend who this is now. A switched-off
  // account is signed out; otherwise the session is re-issued with the current role and databases. If the
  // backend can't be reached, carry on with the session as it is (the backend checks the account on every call).
  try {
    const res = await fetch(`${BACKEND_API_URL}/api/auth/me`, {
      headers: {
        "X-API-Key": BACKEND_API_KEY,
        "X-BMI-User-Id": session.sub,
        "X-BMI-User-Role": session.role,
        "X-BMI-User-Access": JSON.stringify(session.access.map((a) => ({ source_db: a.source_db, group_id: a.group_id }))),
      },
      cache: "no-store",
    });
    if (res.status === 401 && res.headers.get("X-BMI-Signed-Out")) return toLogin(request);
    if (!res.ok) return NextResponse.next();
    const me = await res.json();
    const fresh = await createSessionToken({ sub: me.id, email: me.email, name: me.name, role: me.role, access: me.access ?? [] });
    // Hand the fresh session to this request too, so the page being opened already shows the change.
    request.cookies.set(SESSION_COOKIE, fresh);
    const response = NextResponse.next({ request: { headers: request.headers } });
    response.cookies.set(SESSION_COOKIE, fresh, sessionCookieOptions);
    return response;
  } catch {
    return NextResponse.next();
  }
}

export const config = {
  matcher: [
    "/((?!login|privacy|terms|support|zoom|api/login|api/notetaker|api/booking-forms|api/subscribe-forms|_next/static|_next/image|favicon.ico).*)",
  ],
};
