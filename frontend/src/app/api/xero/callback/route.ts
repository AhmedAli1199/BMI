import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { friendlyError } from "@/lib/errors";

/** Xero redirects here after the admin picks BMI's organisation. The code is
 * exchanged by the backend, which stores the tokens encrypted and runs a
 * first invoice sync. */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error_description") || url.searchParams.get("error");
  if (error || !code || !state) {
    return NextResponse.redirect(new URL(`/settings?xero_error=${encodeURIComponent(error || "Xero sign-in was cancelled")}`, url));
  }
  try {
    const res = await backendFetch<{ organisation: string; return_to: string }>("/api/integrations/xero/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, state }),
    });
    const back = new URL(res.return_to || "/settings", url);
    back.searchParams.set("xero_connected", res.organisation || "Xero");
    return NextResponse.redirect(back);
  } catch (e) {
    const msg = friendlyError(e, "Couldn't connect Xero");
    return NextResponse.redirect(new URL(`/settings?xero_error=${encodeURIComponent(msg)}`, url));
  }
}
