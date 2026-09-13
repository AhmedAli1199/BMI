"use client";

import { useRouter } from "next/navigation";
import { TableRow } from "@/components/ui/table";
import type { ComponentProps } from "react";

/**
 * A TableRow that navigates on click anywhere in the row, not just the name
 * link inside it - fixes the "I can't select a contact" complaint, since a
 * single small underlined name was the only clickable target before. Nested
 * links/buttons (e.g. a company link in another cell) still work normally;
 * clicking them stops the row-level navigation via stopPropagation.
 */
export function ClickableTableRow({
  href,
  className,
  ...props
}: ComponentProps<typeof TableRow> & { href: string }) {
  const router = useRouter();
  return (
    <TableRow
      onClick={() => router.push(href)}
      className={`cursor-pointer ${className ?? ""}`}
      {...props}
    />
  );
}
