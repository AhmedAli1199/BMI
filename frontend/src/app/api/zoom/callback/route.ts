import { publicBase } from "@/lib/public-url";
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";
import { friendlyError } from "@/lib/errors";

/** Zoom sends people back here after "Connect Zoom" (this address is the Zoom app's Redirect URL). */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const base = publicBase(request);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (url.searchParams.get("error") || !code) {
    return NextResponse.redirect(new URL(`/calls/meetings?zoom_error=${encodeURIComponent("The Zoom sign-in was cancelled")}`, base));
  }
  // No state: Zoom's own "Add App Now" (or installing from Zoom's side) - it's finished for whoever is signed in here.
  try {
    const res = await backendFetch<{ return_to: string }>("/api/zoom/callback", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code, state: state || null }),
    });
    const back = new URL(res.return_to || "/calls/meetings", base);
    back.searchParams.set("zoom_connected", "1");
    return NextResponse.redirect(back);
  } catch (e) {
    return NextResponse.redirect(new URL(`/calls/meetings?zoom_error=${encodeURIComponent(friendlyError(e, "Couldn't connect Zoom"))}`, base));
  }
}
