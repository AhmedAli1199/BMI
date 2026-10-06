"use client";

import { useEffect, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, CheckCircle2, Landmark, RefreshCw, Unplug } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { disconnectXero, syncXero, type XeroStatus } from "@/lib/xero-actions";

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "never");

/** Settings › Integrations: the read-only Xero link. Sales invoices sync
 * every hour and show as paid / unpaid / overdue next to each booking. */
export function XeroConnectionCard({ status }: { status: XeroStatus | null }) {
  const router = useRouter();
  const params = useSearchParams();
  const [pending, start] = useTransition();

  useEffect(() => {
    const ok = params.get("xero_connected");
    const err = params.get("xero_error");
    if (ok) toast.success(`Xero connected to ${ok} - invoices are syncing`);
    if (err) toast.error(err);
    if (ok || err) router.replace("/settings#integrations", { scroll: false });
  }, [params, router]);

  if (!status) return null;
  const broken = status.connected && !!status.last_error;
  const viaN8n = status.mode === "webhook";

  return (
    <Card className="editorial-card">
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 gap-3">
            <span className="brand-icon size-9 shrink-0 text-primary">
              <Landmark className="size-4" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-bold text-foreground">Xero</p>
              {status.connected ? (
                <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  {broken ? (
                    <AlertTriangle className="size-3.5" style={{ color: "var(--warn)" }} aria-hidden="true" />
                  ) : (
                    <CheckCircle2 className="size-3.5" style={{ color: "var(--ok)" }} aria-hidden="true" />
                  )}
                  <span>
                    {status.organisation} · {status.invoices.toLocaleString()} invoices · {status.bookings_matched.toLocaleString()} bookings
                    matched · last sync {when(status.last_sync_at)}
                    {viaN8n && " · signed in through BMI's n8n workflow"}
                  </span>
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Read-only link to BMI&apos;s Xero. Sales invoices sync every hour and each booking shows whether its invoice is paid,
                  unpaid or overdue. Nothing is ever written to Xero.
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            {status.configured && !viaN8n && (!status.connected || broken) && (
              <Button size="sm" nativeButton={false} render={<a href="/api/xero/connect?return_to=/settings" />}>
                {status.connected ? "Reconnect" : "Connect Xero"}
              </Button>
            )}
            {status.connected && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={pending}
                  onClick={() =>
                    start(async () => {
                      try {
                        const r = await syncXero();
                        toast.success(r.skipped ?? `Synced - ${r.invoices ?? 0} invoices changed`);
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Sync failed");
                      }
                      router.refresh();
                    })
                  }
                >
                  <RefreshCw className="size-3.5" /> Sync now
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={pending}
                  title="Reads every invoice again from the start. Needed once so the invoice matcher can see what each invoice is for; takes a minute or two."
                  onClick={() =>
                    start(async () => {
                      try {
                        const r = await syncXero(true);
                        toast.success(r.skipped ?? `Re-read ${r.invoices ?? 0} invoices`);
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Sync failed");
                      }
                      router.refresh();
                    })
                  }
                >
                  <RefreshCw className="size-3.5" /> Re-read all invoices
                </Button>
                {!viaN8n && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={pending}
                    onClick={() =>
                      start(async () => {
                        await disconnectXero();
                        toast.success("Xero disconnected");
                        router.refresh();
                      })
                    }
                  >
                    <Unplug className="size-3.5" /> Disconnect
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
        {broken && (
          <p
            role="status"
            className="rounded-md bg-[color-mix(in_oklab,var(--warn)_12%,transparent)] px-3 py-2 text-xs font-medium"
            style={{ color: "var(--warn)" }}
          >
            {status.last_error}
          </p>
        )}
        {!status.configured && (
          <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
            Not available yet: add XERO_CLIENT_ID and XERO_CLIENT_SECRET to the server settings. In the Xero app, the redirect URI must be{" "}
            <span className="font-mono">{status.redirect_uri}</span>.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
