"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  LayoutGrid,
  List,
  Mail,
  PhoneCall,
  Plus,
  User,
  Users,
  Building2,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function ActSubbar({
  module = "contacts",
  currentRecordIndex,
  totalRecords,
  onPrevious,
  onNext,
  onFirst,
  onLast,
  onQuickAction,
}: {
  module?: "contacts" | "companies" | "groups";
  currentRecordIndex?: number;
  totalRecords?: number;
  onPrevious?: () => void;
  onNext?: () => void;
  onFirst?: () => void;
  onLast?: () => void;
  onQuickAction?: (action: "call" | "meeting" | "note" | "email") => void;
}) {
  const pathname = usePathname();
  const router = useRouter();

  const isDetailView =
    pathname.includes("/contacts/") ||
    pathname.includes("/companies/") ||
    pathname.includes("/groups/");

  const handleQuickAction = (action: "call" | "meeting" | "note" | "email") => {
    if (onQuickAction) {
      onQuickAction(action);
    } else if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("act-quick-action", { detail: { action } })
      );
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 bg-card/60 backdrop-blur-xs px-4 py-2 text-xs">
      {/* 1. Module Sub-Tabs (Contacts | Companies | Groups) */}
      <div className="flex items-center gap-1">
        <Link
          href="/contacts"
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition-colors ${
            pathname.startsWith("/contacts")
              ? "bg-primary/10 text-primary border border-primary/20"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          }`}
        >
          <Users className="size-3.5" />
          <span>Contacts</span>
        </Link>
        <Link
          href="/companies"
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition-colors ${
            pathname.startsWith("/companies")
              ? "bg-primary/10 text-primary border border-primary/20"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          }`}
        >
          <Building2 className="size-3.5" />
          <span>Companies</span>
        </Link>
        <Link
          href="/groups"
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition-colors ${
            pathname.startsWith("/groups")
              ? "bg-primary/10 text-primary border border-primary/20"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          }`}
        >
          <UsersRound className="size-3.5" />
          <span>Groups</span>
        </Link>
      </div>

      {/* 2. ACT! Quick Action Cluster (Call, Meeting, Note, Email) */}
      <div className="hidden sm:flex items-center gap-1 border-x px-3 border-border/60">
        <Button
          size="xs"
          variant="ghost"
          onClick={() => handleQuickAction("call")}
          className="gap-1.5 font-medium hover:bg-amber-500/10 hover:text-amber-600 cursor-pointer"
          title="Log Call"
        >
          <PhoneCall className="size-3 text-amber-600" />
          <span>Call</span>
        </Button>
        <Button
          size="xs"
          variant="ghost"
          onClick={() => handleQuickAction("meeting")}
          className="gap-1.5 font-medium hover:bg-blue-500/10 hover:text-blue-600 cursor-pointer"
          title="Schedule Meeting"
        >
          <Calendar className="size-3 text-blue-600" />
          <span>Meeting</span>
        </Button>
        <Button
          size="xs"
          variant="ghost"
          onClick={() => handleQuickAction("note")}
          className="gap-1.5 font-medium hover:bg-emerald-500/10 hover:text-emerald-600 cursor-pointer"
          title="Create Note"
        >
          <FileText className="size-3 text-emerald-600" />
          <span>Note</span>
        </Button>
        <Button
          size="xs"
          variant="ghost"
          onClick={() => handleQuickAction("email")}
          className="gap-1.5 font-medium hover:bg-purple-500/10 hover:text-purple-600 cursor-pointer"
          title="Send E-mail"
        >
          <Mail className="size-3 text-purple-600" />
          <span>E-mail</span>
        </Button>
      </div>

      {/* 3. View Switcher Pills & VCR Stepper */}
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
