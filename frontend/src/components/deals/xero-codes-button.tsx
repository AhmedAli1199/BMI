"use client";

import { useState, useTransition } from "react";
import { Loader2, RefreshCw, Settings2 } from "lucide-react";
import { toast } from "sonner";
import { getXeroCodes, getXeroReference, saveXeroCodes, type XeroCodes, type XeroReference, type XeroTracking } from "@/lib/xero-invoicing";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";

const selectCls = "h-8 w-full min-w-0 rounded-md border border-input bg-transparent px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
type Codes = { account_code?: string; item_code?: string; tracking?: XeroTracking[] };

function CodeRow({ label, value, onChange, xero }: { label: string; value: Codes; onChange: (c: Codes) => void; xero: XeroReference }) {
  const tr = value.tracking ?? [];
  return (
    <div className="grid gap-2 rounded-lg border border-border/70 p-2.5 sm:grid-cols-2">
      <p className="text-sm font-semibold sm:col-span-2">{label}</p>
      <label className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground">Account
        <select className={selectCls} value={value.account_code ?? ""} onChange={(e) => onChange({ ...value, account_code: e.target.value || undefined })}>
          <option value="">{label === "Every publication" ? "None" : "Same as every publication"}</option>
          {xero.accounts.map((a) => <option key={a.code} value={a.code}>{a.code} · {a.name}</option>)}
        </select></label>
      <label className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground">Item
        <select className={selectCls} value={value.item_code ?? ""} onChange={(e) => onChange({ ...value, item_code: e.target.value || undefined })}>
          <option value="">None</option>
          {xero.items.map((i) => <option key={i.code} value={i.code}>{i.code} · {i.name}</option>)}
        </select></label>
      {xero.tracking.map((t) => (
        <label key={t.name} className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground">{t.name}
          <select className={selectCls} value={tr.find((x) => x.name === t.name)?.option ?? ""} onChange={(e) => {
            const others = tr.filter((x) => x.name !== t.name);
            onChange({ ...value, tracking: e.target.value ? [...others, { name: t.name, option: e.target.value }] : others });
          }}>
            <option value="">None</option>
            {t.options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select></label>
      ))}
    </div>
  );
}

/** Accounts: the Xero account, item and tracking codes each publication's invoice lines use. */
export function XeroCodesButton({ titles }: { titles: { id: string; name: string }[] }) {
  const [open, setOpen] = useState(false);
  const [codes, setCodes] = useState<XeroCodes | null>(null);
  const [ref, setRef] = useState<XeroReference | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const load = (fresh = false) => start(async () => {
    setError(null);
    try {
      const [c, r] = await Promise.all([getXeroCodes(), getXeroReference(fresh)]);
      setCodes(c); setRef(r);
    } catch (e) { setError(friendlyError(e, "Couldn't load the codes from Xero. Check Xero is connected (Settings, Integrations).")); }
  });

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setOpen(true); load(); }}><Settings2 className="size-3.5" /> Xero codes</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-xl">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>Xero codes for invoices</SheetTitle>
            <SheetDescription>The account, item and tracking each publication&apos;s invoice lines use when an invoice is made from a booking. Set them once; anything chosen while making an invoice is remembered here too.</SheetDescription>
          </SheetHeader>
          <div className="flex flex-col gap-3 p-4">
            {error && <p className="rounded-md bg-muted/50 p-2.5 text-sm">{error}</p>}
            {pending && !ref && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
            {codes && ref && (
              <>
                <CodeRow label="Every publication" value={codes.default ?? {}} xero={ref} onChange={(c) => setCodes({ ...codes, default: c })} />
                {titles.map((t) => (
                  <CodeRow key={t.id} label={t.name} value={codes.titles?.[t.id] ?? {}} xero={ref}
                    onChange={(c) => setCodes({ ...codes, titles: { ...(codes.titles ?? {}), [t.id]: c } })} />
                ))}
                <button type="button" className="inline-flex items-center gap-1 self-start text-xs font-medium text-primary hover:underline" onClick={() => load(true)}>
                  <RefreshCw className="size-3" aria-hidden="true" /> Reload the codes from Xero
                </button>
              </>
            )}
          </div>
          {codes && ref && (
            <SheetFooter className="flex-row border-t border-border/70">
              <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
              <Button disabled={pending} onClick={() => start(async () => {
                try { setCodes(await saveXeroCodes(codes)); toast.success("Saved"); setOpen(false); }
                catch (e) { toast.error(friendlyError(e, "Couldn't save the codes")); }
              })}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
            </SheetFooter>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
