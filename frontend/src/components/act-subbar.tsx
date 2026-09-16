"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  List,
  User,
  Users,
  Building2,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export function ActSubbar({
  module = "contacts",
  currentRecordIndex,
  totalRecords,
  onPrevious,
  onNext,
  onFirst,
  onLast,
}: {
  module?: "contacts" | "companies" | "groups";
  currentRecordIndex?: number;
  totalRecords?: number;
  onPrevious?: () => void;
  onNext?: () => void;
  onFirst?: () => void;
  onLast?: () => void;
}) {
  const pathname = usePathname();

  const isDetailView =
    pathname.includes("/contacts/") ||
    pathname.includes("/companies/") ||
    pathname.includes("/groups/");

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 bg-card px-4 py-2 text-xs shadow-2xs">
      {/* 1. Module Sub-Tabs (Contacts | Companies | Groups) */}
      <div className="flex items-center gap-1.5" role="tablist" aria-label="CRM Modules">
        <Link
          href="/contacts"
          role="tab"
          aria-selected={pathname.startsWith("/contacts")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition-all ${
            pathname.startsWith("/contacts")
              ? "bg-primary/15 text-primary border border-primary/30 shadow-2xs font-bold"
              : "text-muted-foreground hover:bg-muted/80 hover:text-foreground border border-transparent"
          }`}
        >
          <Users className="size-3.5" />
          <span>Contacts</span>
        </Link>
        <Link
          href="/companies"
          role="tab"
          aria-selected={pathname.startsWith("/companies")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition-all ${
            pathname.startsWith("/companies")
              ? "bg-primary/15 text-primary border border-primary/30 shadow-2xs font-bold"
              : "text-muted-foreground hover:bg-muted/80 hover:text-foreground border border-transparent"
          }`}
        >
          <Building2 className="size-3.5" />
          <span>Companies</span>
        </Link>
        <Link
          href="/groups"
          role="tab"
          aria-selected={pathname.startsWith("/groups")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition-all ${
            pathname.startsWith("/groups")
              ? "bg-primary/15 text-primary border border-primary/30 shadow-2xs font-bold"
              : "text-muted-foreground hover:bg-muted/80 hover:text-foreground border border-transparent"
          }`}
        >
          <UsersRound className="size-3.5" />
          <span>Groups</span>
        </Link>
      </div>

      {/* 2. View Switcher Pills & VCR Stepper */}
      <div className="flex items-center gap-3">
        {/* View Toggle (List View vs Detail View) */}
        <div className="flex items-center rounded-lg border border-border bg-muted/40 p-0.5">
          <Link
            href={`/${module}`}
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-semibold transition-all ${
              !isDetailView
                ? "bg-card text-foreground shadow-2xs"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <List className="size-3" />
            <span>List</span>
          </Link>
          <span
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-semibold transition-all ${
              isDetailView
                ? "bg-card text-foreground shadow-2xs"
                : "text-muted-foreground"
            }`}
          >
            <User className="size-3" />
            <span>Detail</span>
          </span>
        </div>

        {/* VCR Record Stepper (Act! classic record navigator) */}
        {isDetailView && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <Button
              size="icon-xs"
              variant="ghost"
              onClick={onFirst}
              disabled={!onFirst}
              title="First Record"
              className="size-6 cursor-pointer"
            >
              <ChevronsLeft className="size-3.5" />
            </Button>
            <Button
              size="icon-xs"
              variant="ghost"
              onClick={onPrevious}
              disabled={!onPrevious}
              title="Previous Record"
              className="size-6 cursor-pointer"
            >
              <ChevronLeft className="size-3.5" />
            </Button>

            <span className="text-[11px] font-mono px-1">
              {currentRecordIndex
                ? `${currentRecordIndex} of ${totalRecords?.toLocaleString() ?? "118k"}`
                : "Record"}
            </span>

            <Button
              size="icon-xs"
              variant="ghost"
              onClick={onNext}
              disabled={!onNext}
              title="Next Record"
              className="size-6 cursor-pointer"
            >
              <ChevronRight className="size-3.5" />
            </Button>
            <Button
              size="icon-xs"
              variant="ghost"
              onClick={onLast}
              disabled={!onLast}
              title="Last Record"
              className="size-6 cursor-pointer"
            >
              <ChevronsRight className="size-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
