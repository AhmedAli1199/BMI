"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Building2,
  ExternalLink,
  Eye,
  Mail,
  MoreHorizontal,
  Phone,
} from "lucide-react";
import type { ContactListItem } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EntityAvatar } from "@/components/entity-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { sourceLabel } from "@/lib/sources";
import { ContactPreviewDrawer } from "@/components/contact-preview-drawer";

export function InteractiveContactTable({ items }: { items: ContactListItem[] }) {
  const [selectedContact, setSelectedContact] = useState<ContactListItem | null>(
    null
  );
  const [drawerOpen, setDrawerOpen] = useState(false);

  function handleRowClick(c: ContactListItem) {
    setSelectedContact(c);
    setDrawerOpen(true);
  }

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

  return (
    <>
      <div className="overflow-hidden rounded-lg border border-border bg-card shadow-2xs">
        <Table>
          <TableHeader className="bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[32%] py-3">Contact &amp; Title</TableHead>
              <TableHead className="w-[26%]">Account / Publisher</TableHead>
              <TableHead className="w-[20%]">Direct Email</TableHead>
              <TableHead className="w-[14%]">Publication</TableHead>
              <TableHead className="w-[8%] text-right pr-4">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((c) => {
              const name =
                c.full_name ||
                [c.first_name, c.last_name].filter(Boolean).join(" ") ||
                "(no name)";

              return (
                <TableRow
                  key={c.id}
                  onClick={() => handleRowClick(c)}
                  className="group cursor-pointer transition-colors hover:bg-accent/40"
                >
                  <TableCell className="py-3">
                    <div className="flex items-center gap-3">
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
                    </div>
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
                      className={`text-[11px] font-medium ${publicationBadgeStyle(
                        c.source_db
                      )}`}
                    >
                      {sourceLabel(c.source_db)}
                    </Badge>
                  </TableCell>

                  <TableCell className="text-right pr-4" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        size="icon-xs"
                        variant="ghost"
                        onClick={() => handleRowClick(c)}
                        title="Quick Inspect"
                        className="opacity-70 group-hover:opacity-100 hover:bg-muted cursor-pointer"
                      >
                        <Eye className="size-3.5 text-muted-foreground" />
                      </Button>
                      <Link
                        href={`/contacts/${c.id}`}
                        title="Open Full Dossier"
                        className="flex size-6 items-center justify-center rounded-md opacity-70 group-hover:opacity-100 hover:bg-muted cursor-pointer transition-colors"
                      >
                        <ExternalLink className="size-3.5 text-muted-foreground" />
                      </Link>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}

            {items.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="py-12 text-center text-sm text-muted-foreground"
                >
                  No contacts match this view or publication filter.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <ContactPreviewDrawer
        contact={selectedContact}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </>
  );
}
