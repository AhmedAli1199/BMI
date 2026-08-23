"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";

type ApiState = "checking" | "online" | "offline";

export function ApiStatus() {
  const [state, setState] = useState<ApiState>("checking");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    let cancelled = false;

    fetch(`${apiUrl}/api/health`)
      .then((res) => {
        if (!cancelled) setState(res.ok ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setState("offline");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const variant =
    state === "online" ? "default" : state === "offline" ? "destructive" : "secondary";
  const label =
    state === "online" ? "API online" : state === "offline" ? "API offline" : "Checking API…";

  return <Badge variant={variant}>{label}</Badge>;
}
