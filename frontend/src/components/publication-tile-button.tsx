"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { setPublicationFilter } from "@/lib/actions";

/** Wraps a dashboard "magazine title" tile so clicking it sets the global
 * publication filter (lib/publication.ts) and stays on the dashboard - it
 * used to be a <Link href="/contacts?source_db=..."> that jumped you to the
 * Contacts list, which was the reported bug ("if I select a database while
 * on the dashboard it jumps to the contacts tab"). */
export function PublicationTileButton({
  sourceDb,
  className,
  children,
}: {
  sourceDb: string;
  className?: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      disabled={pending}
      onClick={() =>
        startTransition(async () => {
          await setPublicationFilter(sourceDb);
          router.refresh();
        })
      }
      className={`block w-full text-left ${className ?? ""}`}
    >
      {children}
    </button>
  );
}
