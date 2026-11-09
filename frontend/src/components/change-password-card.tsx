"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { changeMyPassword } from "@/lib/actions";
import { friendlyError } from "@/lib/errors";

/** Settings > Password: anyone changes their own password, after typing their current one. */
export function ChangePasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [pending, start] = useTransition();
  const tooShort = next.length > 0 && next.length < 8;
  const mismatch = again.length > 0 && next !== again;
  const ready = current && next.length >= 8 && next === again;

  function save() {
    start(async () => {
      try {
        await changeMyPassword(current, next);
        setCurrent(""); setNext(""); setAgain("");
        toast.success("Password changed. Use your new one next time you sign in.");
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't change your password. Please try again."));
      }
    });
  }

  return (
    <Card className="editorial-card">
      <CardContent className="flex flex-col gap-3 p-4">
        <div>
          <p className="text-sm font-bold text-foreground">Change your password</p>
          <p className="text-xs text-muted-foreground">At least 8 characters. You stay signed in on this device.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pw-current">Current password</Label>
            <Input id="pw-current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pw-new">New password</Label>
            <Input id="pw-new" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
            {tooShort && <span className="text-xs text-destructive">At least 8 characters.</span>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pw-again">New password again</Label>
            <Input id="pw-again" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} />
            {mismatch && <span className="text-xs text-destructive">The two new passwords don&apos;t match.</span>}
          </div>
        </div>
        <Button className="w-fit" disabled={pending || !ready} onClick={save}>
          {pending ? "Saving…" : "Change password"}
        </Button>
      </CardContent>
    </Card>
  );
}
