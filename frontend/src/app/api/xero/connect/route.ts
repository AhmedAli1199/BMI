import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";

/** "Connect Xero" - asks the backend for Xero's sign-in URL
 * (carrying a signed state naming this user) and sends the browser there. */
export async function GET(request: Request) {
  const session = await getSession();
  const url = new URL(request.url);
  if (!session) return NextResponse.redirect(new URL("/login", url));
  const returnTo = url.searchParams.get("return_to") || "/settings";
  try {
    const { url: authorize } = await backendFetch<{ url: string }>(
      `/api/integrations/xero/start?return_to=${encodeURIComponent(returnTo)}`
    );
    return NextResponse.redirect(authorize);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Couldn't start Xero sign-in";
    return NextResponse.redirect(new URL(`${returnTo}?xero_error=${encodeURIComponent(msg)}`, url));
  }
}
