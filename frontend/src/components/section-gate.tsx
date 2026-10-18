"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { sectionForPath } from "@/lib/section-routes";
import type { SectionKey } from "@/lib/sections";

/** Pages in a section an administrator has hidden for this person (Settings > Sections) don't open, even from an
 * old link or bookmark - the menu already leaves them out. Administrators get no hidden sections. */
export function SectionGate({ hidden, children }: { hidden: SectionKey[]; children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const section = sectionForPath(pathname);
  if (!section || !hidden.includes(section)) return <>{children}</>;
  return (
    <div className="mx-auto w-full max-w-xl p-6 lg:p-10">
      <EmptyState
        title="This part of the app is switched off for you"
        action={<Button size="sm" nativeButton={false} render={<Link href="/" />}>Go to Home</Button>}
      >
        An administrator has hidden it to keep your screens simple. Ask them if you need it.
      </EmptyState>
    </div>
  );
}
