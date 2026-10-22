import { publicBase } from "@/lib/public-url";
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { friendlyError } from "@/lib/errors";

/** "Connect Zoom" - gets Zoom's sign-in address (with a signed state naming this person) and sends the browser
 * there. Zoom comes back through /api/zoom/callback. */
export async function GET(request: Request) {
  const session = await getSession();
  const url = new URL(request.url);
  const base = publicBase(request);
  if (!session) return NextResponse.redirect(new URL("/login", base));
  const returnTo = url.searchParams.get("return_to") || "/calls/meetings";
  try {
    const { url: authorize } = await backendFetch<{ url: string }>(`/api/zoom/start?return_to=${encodeURIComponent(returnTo)}`);
    return NextResponse.redirect(authorize);
  } catch (e) {
    const msg = friendlyError(e, "Couldn't start the Zoom sign-in");
    return NextResponse.redirect(new URL(`${returnTo}?zoom_error=${encodeURIComponent(msg)}`, base));
  }
}
