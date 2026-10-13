import { publicBase } from "@/lib/public-url";
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { friendlyError } from "@/lib/errors";

/** "Connect Google / Outlook Calendar" - gets the provider's sign-in URL (with a signed state naming
 * this user) and sends the browser there. Outlook comes back through /api/outlook/callback, Google
 * through /api/google/callback. */
export async function GET(request: Request) {
  const session = await getSession();
  const url = new URL(request.url);
  const base = publicBase(request);
  if (!session) return NextResponse.redirect(new URL("/login", base));
  const provider = url.searchParams.get("provider") === "google" ? "google" : "microsoft";
  const returnTo = url.searchParams.get("return_to") || "/calls/meetings";
  try {
    const { url: authorize } = await backendFetch<{ url: string }>(`/api/calendar/${provider}/start?return_to=${encodeURIComponent(returnTo)}`);
    return NextResponse.redirect(authorize);
  } catch (e) {
    const msg = friendlyError(e, "Couldn't start the calendar sign-in");
    return NextResponse.redirect(new URL(`${returnTo}?calendar_error=${encodeURIComponent(msg)}`, base));
  }
}
