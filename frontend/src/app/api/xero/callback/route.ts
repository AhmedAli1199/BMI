import { publicBase } from "@/lib/public-url";
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { friendlyError } from "@/lib/errors";

/** Xero redirects here after the admin picks BMI's organisation. The code is
 * exchanged by the backend, which stores the tokens encrypted and runs a
 * first invoice sync. */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const base = publicBase(request);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  // Xero's own error text never reaches the screen - just a plain sentence.
  const error = url.searchParams.get("error_description") || url.searchParams.get("error");
  if (error || !code || !state) {
    const msg = "Xero sign-in was cancelled or didn't finish - please try connecting again.";
    return NextResponse.redirect(new URL(`/settings?xero_error=${encodeURIComponent(msg)}`, base));
  }
  try {
    const res = await backendFetch<{ organisation: string; return_to: string }>("/api/integrations/xero/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, state }),
    });
    const back = new URL(res.return_to || "/settings", base);
    back.searchParams.set("xero_connected", res.organisation || "Xero");
    return NextResponse.redirect(back);
  } catch (e) {
    const msg = friendlyError(e, "Couldn't connect Xero");
    return NextResponse.redirect(new URL(`/settings?xero_error=${encodeURIComponent(msg)}`, base));
  }
}
