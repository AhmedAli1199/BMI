import Link from "next/link";
import { Building2 } from "lucide-react";
import type { ContactListItem } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClickableTableRow } from "@/components/clickable-table-row";
import { EntityAvatar } from "@/components/entity-avatar";
import { Badge } from "@/components/ui/badge";
import { sourceLabel } from "@/lib/sources";

const publicationBadgeStyle = (source: string) => {
  switch (source) {
    case "onboard":
      return "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400";
    case "sellingtravel":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
    case "prospects":
      return "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400";
    default:
      return "border-border bg-muted text-muted-foreground";
  }
};

/** Clicking a row (or the name inside it) opens the full record directly -
 * no in-between preview step. The columns here already carry everything a
 * preview panel used to show (title, company, email, publication), so
 * there's nothing extra to surface before the click. */
export function InteractiveContactTable({ items }: { items: ContactListItem[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card shadow-2xs">
      <Table>
        <TableHeader className="bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[34%] py-3">Contact &amp; Title</TableHead>
            <TableHead className="w-[28%]">Company</TableHead>
            <TableHead className="w-[22%]">Direct Email</TableHead>
            <TableHead className="w-[16%]">Publication</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((c) => {
            const name =
              c.full_name ||
              [c.first_name, c.last_name].filter(Boolean).join(" ") ||
              "(no name)";

            return (
              <ClickableTableRow
                key={c.id}
                href={`/contacts/${c.id}`}
                className="group hover:bg-accent/40"
              >
                <TableCell className="py-3">
                  <Link href={`/contacts/${c.id}`} className="flex items-center gap-3">
                    <EntityAvatar
                      name={name}
                      className="size-8.5 text-xs font-medium border border-border shrink-0"
                    />
                    <div className="min-w-0">
                      <div className="font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                        {name}
                      </div>
                      {c.job_title && (
                        <div className="truncate text-xs text-muted-foreground">
                          {c.job_title}
                        </div>
                      )}
                    </div>
                  </Link>
                </TableCell>

                <TableCell>
                  {c.company_name ? (
                    <span className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                      <Building2 className="size-3 text-muted-foreground shrink-0" />
                      <span className="truncate">{c.company_name}</span>
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-xs">—</span>
                  )}
                </TableCell>

                <TableCell>
                  {c.primary_email ? (
                    <span className="text-xs font-mono text-muted-foreground truncate block max-w-[220px]">
                      {c.primary_email}
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-xs">—</span>
                  )}
                </TableCell>

                <TableCell>
                  <Badge
                    variant="outline"
                    className={`text-[11px] font-medium ${publicationBadgeStyle(c.source_db)}`}
                  >
                    {sourceLabel(c.source_db)}
                  </Badge>
                </TableCell>
              </ClickableTableRow>
            );
          })}

          {items.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={4}
                className="py-12 text-center text-sm text-muted-foreground"
              >
                No contacts match this view or publication filter.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
