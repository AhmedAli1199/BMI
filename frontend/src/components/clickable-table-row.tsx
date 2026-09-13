"use client";

import { useRouter } from "next/navigation";
import { TableRow } from "@/components/ui/table";
import type { ComponentProps } from "react";

/**
 * A TableRow that navigates on click anywhere in the row, not just the name
 * link inside it - fixes the "I can't select a contact" complaint, since a
 * single small underlined name was the only clickable target before.
 *
 * Nested links (e.g. a company link in another cell) still work normally:
 * rather than attaching a stopPropagation handler to each of those links -
 * which can't be done from a Server Component page, since passing an inline
 * event handler into next/link's Client Component props throws at render -
 * this checks whether the click actually landed on an <a> and, if so, lets
 * that link's own navigation happen instead of also pushing this row's href.
 */
export function ClickableTableRow({
  href,
  className,
  ...props
}: ComponentProps<typeof TableRow> & { href: string }) {
  const router = useRouter();
  return (
    <TableRow
      onClick={(e) => {
        if ((e.target as HTMLElement).closest("a")) return;
        router.push(href);
      }}
      className={`cursor-pointer ${className ?? ""}`}
      {...props}
    />
  );
}
