import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { friendlyError } from "@/lib/errors";

/** Microsoft redirects here after "Sign in with Microsoft". The code is
 * exchanged for tokens by the backend, which stores them encrypted. */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error_description") || url.searchParams.get("error");
  if (error || !code || !state) {
    return NextResponse.redirect(new URL(`/settings?outlook_error=${encodeURIComponent(error || "Sign-in was cancelled")}`, url));
  }
  try {
    const res = await backendFetch<{ email: string; return_to: string }>("/api/mail/outlook/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, state }),
    });
    const back = new URL(res.return_to || "/settings", url);
    back.searchParams.set("outlook_connected", res.email);
    return NextResponse.redirect(back);
  } catch (e) {
    const msg = friendlyError(e, "Couldn't connect Outlook");
    return NextResponse.redirect(new URL(`/settings?outlook_error=${encodeURIComponent(msg)}`, url));
  }
}
