"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarClock, ChevronRight, ClipboardCheck, HeartPulse, Settings, Sparkles } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import { LogoutButton } from "@/components/logout-button";
import { ThemeMotif } from "@/components/theme-motif";
import { canUseAutomations, canViewAutomationsQueue } from "@/lib/access";
import type { SessionPayload } from "@/lib/session";
import type { WorkstreamSummary } from "@/lib/types";

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  data_manager: "Data Manager",
  sales: "Sales",
};

// Nav items get a deliberately bigger, bolder treatment than shadcn's
// default text-sm - the client asked for this explicitly ("bigger bolder
// for easy viewing"), applied here rather than in the shared ui/sidebar.tsx
// primitive so it's specific to this app's nav, not every future sidebar use.
const NAV_ITEM = "text-[15.5px] font-semibold h-10 [&_svg]:size-[19px]";

/** Hub sub-pages live under /automations but Today and Review Queue do
 * too - they're separate sidebar items, so they don't count as "inside"
 * the Hub section. */
function isHubPath(pathname: string): boolean {
  return (
    pathname.startsWith("/automations") &&
    !pathname.startsWith("/automations/today") &&
    !pathname.startsWith("/automations/review")
  );
}

export function AppSidebar({
  session,
  workstreams = [],
  scanners,
}: {
  session: SessionPayload | null;
  workstreams?: WorkstreamSummary[];
  scanners?: { active: number; total: number };
}) {
  const pathname = usePathname();
  const inHub = isHubPath(pathname);
  const [hubOpen, setHubOpen] = useState(inHub);
  // Navigating into a Hub page from anywhere else (a link, the back
  // button) opens the section so the current page is always visible in
  // the nav - but leaving it never force-closes something the user opened.
  const [wasInHub, setWasInHub] = useState(inHub);
  if (inHub !== wasInHub) {
    setWasInHub(inHub);
    if (inHub) setHubOpen(true);
  }
  const hubPending = workstreams.reduce((sum, w) => sum + w.pending, 0);

  return (
    <Sidebar>
      <SidebarHeader className="border-b border-sidebar-border/60 px-4 py-3.5">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link href="/" />}
              isActive={pathname === "/"}
              className="h-auto flex-col items-start gap-0.5 py-2 hover:bg-sidebar-accent/80 transition-colors"
            >
              <span className="bmi-wordmark">BMI</span>
              <span className="text-[10.5px] font-medium tracking-wide text-sidebar-foreground/55">
                Publishing &middot; Sales &amp; Editorial CRM
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-[11px] font-bold tracking-wider">Platform</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1.5">
              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/" />}
                  isActive={pathname === "/"}
                  className={NAV_ITEM}
                >
                  Dashboard
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/contacts" />}
                  isActive={pathname.startsWith("/contacts")}
                  className={NAV_ITEM}
                >
                  Contacts
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/companies" />}
                  isActive={pathname.startsWith("/companies")}
                  className={NAV_ITEM}
                >
                  Companies
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/groups" />}
                  isActive={pathname.startsWith("/groups")}
                  className={NAV_ITEM}
                >
                  Groups
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/activities" />}
                  isActive={pathname.startsWith("/activities")}
                  className={NAV_ITEM}
                >
                  Calendar &amp; Tasks
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {canViewAutomationsQueue(session) && (
          <SidebarGroup>
            <SidebarGroupLabel className="text-[11px] font-bold tracking-wider">BMI Brain</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu className="gap-1.5">
                {/* Every icon in this group shares one rule - bright/
                    primary when its own page is active, a readable (not
                    washed-out) neutral otherwise - so "Today" isn't the
                    only one that ever looks switched on. Previously
                    "Today" was hardcoded text-primary always and the
                    other two were always text-muted-foreground, which
                    read as broken/inconsistent rather than as a
                    deliberate active-state design. */}
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={<Link href="/automations/today" />}
                    isActive={pathname.startsWith("/automations/today")}
                    className={NAV_ITEM}
                  >
                    <CalendarClock
                      className={`mr-1.5 size-4 ${pathname.startsWith("/automations/today") ? "text-primary" : "text-sidebar-foreground/70"}`}
                    />
                    <span>Today</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={<Link href="/automations/review" />}
                    isActive={pathname.startsWith("/automations/review")}
                    className={NAV_ITEM}
                  >
                    <ClipboardCheck
                      className={`mr-1.5 size-4 ${pathname.startsWith("/automations/review") ? "text-primary" : "text-sidebar-foreground/70"}`}
                    />
                    <span>Review Queue</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                {/* The job/settings/cost control panel - stays
                    admin/data_manager only even though Today/Review Queue
                    above are now open to sales too (scoped to their own
                    data server-side - see lib/access.ts). */}
                {canUseAutomations(session) && (
                  <Collapsible open={hubOpen} onOpenChange={setHubOpen} render={<SidebarMenuItem />}>
                    <CollapsibleTrigger
                      render={<SidebarMenuButton isActive={inHub && !hubOpen} className={NAV_ITEM} />}
                    >
                      <Sparkles className={`mr-1.5 size-4 ${inHub ? "text-primary" : "text-sidebar-foreground/70"}`} />
                      <span>Automations Hub</span>
                      {!hubOpen && hubPending > 0 && (
                        <span className="ml-auto rounded-full bg-amber-600 px-1.5 py-px text-[10.5px] font-bold text-white tabular-nums">
                          {hubPending.toLocaleString("en-GB")}
                        </span>
                      )}
                      <ChevronRight
                        aria-hidden="true"
                        className={`${!hubOpen && hubPending > 0 ? "" : "ml-auto"} size-4! shrink-0 text-sidebar-foreground/60 transition-transform duration-200 ${hubOpen ? "rotate-90" : ""}`}
                      />
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <SidebarMenuSub className="mt-1">
                        <HubSubItem href="/automations" label="Overview" active={pathname === "/automations"} />
                        {workstreams.map((w) => (
                          <HubSubItem
                            key={w.id}
                            href={`/automations/${w.id}`}
                            label={w.label}
                            active={pathname === `/automations/${w.id}`}
                            badge={w.pending > 0 ? w.pending.toLocaleString("en-GB") : undefined}
                          />
                        ))}
                        <HubSubItem
                          href="/automations/engine"
                          label="Scanners & Settings"
                          active={pathname === "/automations/engine" || pathname === "/automations/settings"}
                          badge={scanners && scanners.total > 0 ? `${scanners.active}/${scanners.total}` : undefined}
                          badgeTone="neutral"
                        />
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </Collapsible>
                )}
                {canUseAutomations(session) && (
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      render={<Link href="/data-health" />}
                      isActive={pathname === "/data-health"}
                      className={NAV_ITEM}
                    >
                      <HeartPulse
                        className={`mr-1.5 size-4 ${pathname === "/data-health" ? "text-primary" : "text-sidebar-foreground/70"}`}
                      />
                      <span>Data Health</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

      </SidebarContent>
      <SidebarFooter>
        {session && (
          <div className="flex items-center justify-between gap-2 px-2 py-1.5">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{session.name}</p>
              <p className="truncate text-xs text-sidebar-foreground/60">
                {ROLE_LABELS[session.role] ?? session.role}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <Button
                nativeButton={false}
                size="icon-sm"
                variant="outline"
                title="Settings"
                render={<Link href="/settings" />}
                className={`border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground ${
                  pathname === "/settings" ? "bg-sidebar-accent text-sidebar-accent-foreground" : ""
                }`}
              >
                <Settings className="size-4" />
              </Button>
              <LogoutButton className="border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
            </div>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}

function HubSubItem({
  href,
  label,
  active,
  badge,
  badgeTone = "pending",
}: {
  href: string;
  label: string;
  active: boolean;
  badge?: string;
  badgeTone?: "pending" | "neutral";
}) {
  return (
    <SidebarMenuSubItem>
      <SidebarMenuSubButton
        render={<Link href={href} />}
        isActive={active}
        aria-current={active ? "page" : undefined}
        className="h-8 text-[13.5px] font-medium"
      >
        <span className="truncate">{label}</span>
        {badge && (
          <span
            className={`ml-auto shrink-0 rounded-full px-1.5 py-px text-[10.5px] font-bold tabular-nums ${
              badgeTone === "pending"
                ? "bg-amber-600 text-white"
                : "border border-sidebar-border text-sidebar-foreground/70"
            }`}
          >
            {badge}
          </span>
        )}
      </SidebarMenuSubButton>
    </SidebarMenuSubItem>
  );
}
