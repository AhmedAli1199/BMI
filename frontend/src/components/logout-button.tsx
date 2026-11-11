"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { clearRecent } from "@/lib/recent-adds";

export function LogoutButton({ className }: { className?: string }) {
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/logout", { method: "POST" });
    clearRecent(); // "You added today" lasts until you sign out
    router.push("/login");
    router.refresh();
  }

  return (
    <Button variant="outline" size="sm" onClick={handleLogout} className={className}>
      Sign out
    </Button>
  );
}
