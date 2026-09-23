"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/** Catches any error thrown while rendering a page inside the app shell
 * (a backend request failing, a bad response shape, etc.) - without this,
 * Next falls back to its own generic error screen with no in-app way to
 * recover short of a hard browser reload, which doesn't even help when
 * the underlying request is failing again on every attempt. `reset()` re-
 * renders this route segment in place; "Back to dashboard" is the escape
 * hatch when the broken page is the one you're already on. */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-4 p-4 pt-24 text-center sm:p-6">
      <Card className="editorial-card w-full">
        <CardContent className="flex flex-col items-center gap-3 py-10">
          <span className="brand-icon size-12 rounded-full! border-destructive text-destructive">
            <AlertTriangle className="size-5" />
          </span>
          <p className="text-base font-bold text-foreground">This page hit a snag.</p>
          <p className="max-w-xs text-sm text-muted-foreground">
            Something went wrong loading this page. Try again, or head back to the dashboard.
          </p>
          <div className="mt-2 flex gap-2">
            <Button variant="outline" onClick={() => (window.location.href = "/")}>
              Back to dashboard
            </Button>
            <Button onClick={() => reset()}>Try again</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
