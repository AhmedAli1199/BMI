import { publicBase } from "@/lib/public-url";
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { friendlyError } from "@/lib/errors";

/** Google sends people back here after "Connect Google Calendar". */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const base = publicBase(request);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (url.searchParams.get("error") || !code || !state) {
    return NextResponse.redirect(new URL(`/calls/meetings?calendar_error=${encodeURIComponent("Google sign-in was cancelled")}`, base));
  }
  try {
    const res = await backendFetch<{ email: string; return_to: string }>("/api/calendar/google/callback", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code, state }),
    });
    const back = new URL(res.return_to || "/calls/meetings", base);
    back.searchParams.set("calendar_connected", res.email);
    return NextResponse.redirect(back);
  } catch (e) {
    return NextResponse.redirect(new URL(`/calls/meetings?calendar_error=${encodeURIComponent(friendlyError(e, "Couldn't connect Google Calendar"))}`, base));
  }
}
