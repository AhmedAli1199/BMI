"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { setActivityDone } from "@/lib/actions";

export function ActivityDoneToggle({
  id,
  isCleared,
  contactId,
  companyId,
}: {
  id: string;
  isCleared: boolean;
  contactId?: string | null;
  companyId?: string | null;
}) {
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  return (
    <input
      type="checkbox"
      checked={isCleared}
      disabled={pending}
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => {
        const next = e.target.checked;
        startTransition(async () => {
          await setActivityDone(id, next, {
            contactId: contactId ?? undefined,
            companyId: companyId ?? undefined,
          });
          router.refresh();
        });
      }}
      className="size-4 shrink-0 cursor-pointer accent-primary"
      aria-label={isCleared ? "Mark as not done" : "Mark as done"}
    />
  );
}
