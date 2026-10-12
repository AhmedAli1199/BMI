import { publicBase } from "@/lib/public-url";
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { friendlyError } from "@/lib/errors";

/** "Connect Xero" - asks the backend for Xero's sign-in URL
 * (carrying a signed state naming this user) and sends the browser there. */
export async function GET(request: Request) {
  const session = await getSession();
  const url = new URL(request.url);
  const base = publicBase(request);
  if (!session) return NextResponse.redirect(new URL("/login", base));
  const returnTo = url.searchParams.get("return_to") || "/settings";
  try {
    const { url: authorize } = await backendFetch<{ url: string }>(
      `/api/integrations/xero/start?return_to=${encodeURIComponent(returnTo)}`
    );
    return NextResponse.redirect(authorize);
  } catch (e) {
    const msg = friendlyError(e, "Couldn't start Xero sign-in");
    return NextResponse.redirect(new URL(`${returnTo}?xero_error=${encodeURIComponent(msg)}`, base));
  }
}
