"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Users } from "lucide-react";
import { toast } from "sonner";
import type { DealSettings, HandoffRoutes } from "@/lib/deals-types";
import { saveDealSettings } from "@/lib/deals-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";

const labelCls = "flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground";

/** The routing table: who gets each magazine's hand-offs. Blank until someone fills it in. */
export function HandoffRoutesButton({ settings, titles }: { settings: DealSettings; titles: { id: string; name: string }[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [r, setR] = useState<HandoffRoutes>(settings.handoff_routes ?? {});
  const [pending, start] = useTransition();
  const setRow = (id: string | null, team: "editorial" | "production", v: string) => setR((x) => id === null
    ? { ...x, default: { ...(x.default ?? {}), [team]: v } }
    : { ...x, titles: { ...(x.titles ?? {}), [id]: { ...(x.titles?.[id] ?? {}), [team]: v } } });
  const row = (id: string | null, label: string, hint?: string) => {
    const v = id === null ? r.default ?? {} : r.titles?.[id] ?? {};
    return (
      <div key={id ?? "default"} className="grid gap-2 rounded-lg border border-border/70 p-2.5 sm:grid-cols-2">
        <p className="text-sm font-semibold sm:col-span-2">{label}{hint && <span className="ml-1.5 text-xs font-normal text-muted-foreground">{hint}</span>}</p>
        <label className={labelCls}>Editorial<Input value={v.editorial ?? ""} disabled={!settings.can_edit} onChange={(e) => setRow(id, "editorial", e.target.value)} placeholder="editor@bmipublishing.co.uk" className="h-8 text-sm" /></label>
        <label className={labelCls}>Production<Input value={v.production ?? ""} disabled={!settings.can_edit} onChange={(e) => setRow(id, "production", e.target.value)} placeholder={id === null ? settings.production_emails || "production@bmipublishing.co.uk" : "same as every magazine"} className="h-8 text-sm" /></label>
      </div>
    );
  };
  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setR(settings.handoff_routes ?? {}); setOpen(true); }}><Users className="size-3.5" /> Hand-offs</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-xl">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>Who gets the hand-offs</SheetTitle>
            <SheetDescription>When accounts have checked a booking, each item goes to editorial (sponsored content, social media) or production (adverts, banners, HTML emails) as an email. These are the addresses the booking form suggests; the salesperson can change them on any item. Separate several addresses with commas.</SheetDescription>
          </SheetHeader>
          <div className="flex flex-col gap-3 p-4">
            {row(null, "Every magazine", "used when a magazine has no row of its own")}
            {titles.map((t) => row(t.id, t.name))}
          </div>
          {settings.can_edit && (
            <SheetFooter className="flex-row border-t border-border/70">
              <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
              <Button disabled={pending} onClick={() => start(async () => {
                try { const { can_edit: _c, ...rest } = settings; void _c; await saveDealSettings({ ...rest, handoff_routes: r }); toast.success("Saved"); setOpen(false); router.refresh(); }
                catch (e) { toast.error(friendlyError(e, "Couldn't save the addresses")); }
              })}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
            </SheetFooter>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
