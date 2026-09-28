"use client";

import { useEffect, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, CheckCircle2, Mail, Unplug } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { disconnectOutlook } from "@/lib/messaging-actions";
import type { MailStatus } from "@/lib/messaging-types";

/** Settings > Email: "Connect Outlook" (so mail merge sends from your own
 * mailbox) and where notification emails come from. */
export function OutlookConnectionCard({ status }: { status: MailStatus | null }) {
  const router = useRouter();
  const params = useSearchParams();
  const [pending, start] = useTransition();

  useEffect(() => {
    const ok = params.get("outlook_connected");
    const err = params.get("outlook_error");
    if (ok) toast.success(`Outlook connected - mail merges will send from ${ok}`);
    if (err) toast.error(err);
    if (ok || err) router.replace("/settings#email", { scroll: false });
  }, [params, router]);

  if (!status) {
    return (
      <Card className="editorial-card">
        <CardContent className="p-4 text-sm text-muted-foreground">Sign in to connect your mailbox.</CardContent>
      </Card>
    );
  }

  return (
    <Card className="editorial-card">
      <CardContent className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 gap-3">
            <span className="brand-icon size-9 shrink-0 text-primary">
              <Mail className="size-4" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-bold text-foreground">Your Outlook mailbox</p>
              {status.connected ? (
                <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  {status.needs_reconnect ? (
                    <AlertTriangle className="size-3.5 text-amber-600" />
                  ) : (
                    <CheckCircle2 className="size-3.5 text-emerald-600" />
                  )}
                  <span className="truncate">
                    {status.display_name ? `${status.display_name} · ` : ""}
                    {status.email}
                  </span>
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Connect once and mail merges send straight from your own Outlook: they appear in your Sent
                  Items and replies come back to you.
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            {status.configured && (!status.connected || status.needs_reconnect) && (
              <Button
                size="sm"
                nativeButton={false}
                render={<a href="/api/outlook/connect?return_to=/settings" />}
              >
                {status.connected ? "Reconnect" : "Connect Outlook"}
              </Button>
            )}
            {status.connected && (
              <Button
                size="sm"
                variant="outline"
                disabled={pending}
                onClick={() =>
                  start(async () => {
                    await disconnectOutlook();
                    toast.success("Outlook disconnected");
                    router.refresh();
                  })
                }
              >
                <Unplug className="size-3.5" />
                Disconnect
              </Button>
            )}
          </div>
        </div>
        {status.needs_reconnect && status.last_error && (
          <p className="rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
            {status.last_error}
          </p>
        )}
        {!status.configured && (
          <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
            Not available yet: an administrator needs to add the Microsoft app registration (with the delegated{" "}
            <em>Mail.Send</em> permission) to the server settings.
          </p>
        )}
        <div className="border-t border-border/60 pt-3 text-xs text-muted-foreground">
          <p>
            <strong className="text-foreground">Sending limit:</strong> {status.per_minute} emails a minute, so a
            500-contact mailing takes about {Math.ceil(500 / Math.max(1, status.per_minute))} minutes. You can close
            the page - it keeps sending.
          </p>
          <p className="mt-1.5">
            <strong className="text-foreground">Notification emails</strong> (reminders and alerts) come from{" "}
            {status.automation_mailbox_ready ? (
              <span className="font-mono">{status.automation_mailbox}</span>
            ) : (
              <>the automation mailbox once it&apos;s set up - until then they appear under the bell only</>
            )}
            .
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
