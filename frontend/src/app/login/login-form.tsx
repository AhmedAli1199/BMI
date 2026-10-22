"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { BrainBuddy } from "@/components/brain/brain-buddy";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      setLoading(false);
      setError("That email and password don't match. Check them and try again.");
      return;
    }

    const next = searchParams.get("next") || "/";
    // only our own pages; a sign-in link (e.g. Connect Zoom, /api/zoom/connect) needs a full page load
    const safe = next.startsWith("/") && !next.startsWith("//") ? next : "/";
    if (safe.startsWith("/api/")) {
      window.location.assign(safe);
      return;
    }
    router.push(safe);
    router.refresh();
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="items-center text-center">
        <BrainBuddy mood="waving" size={92} className="mx-auto mb-1" />
        <CardTitle className="text-xl">BMI Brain</CardTitle>
        <CardDescription>Sign in to carry on where you left off</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
