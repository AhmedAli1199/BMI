"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarClock, ClipboardCheck, HeartPulse, Settings, Sparkles } from "lucide-react";
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
} from "@/components/ui/sidebar";
import { LogoutButton } from "@/components/logout-button";
import { ThemeMotif } from "@/components/theme-motif";
import { canUseAutomations, canViewAutomationsQueue } from "@/lib/access";
import type { SessionPayload } from "@/lib/session";

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

export function AppSidebar({ session }: { session: SessionPayload | null }) {
  const pathname = usePathname();

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
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      render={<Link href="/automations" />}
                      isActive={pathname === "/automations"}
                      className={NAV_ITEM}
                    >
                      <Sparkles
                        className={`mr-1.5 size-4 ${pathname === "/automations" ? "text-primary" : "text-sidebar-foreground/70"}`}
                      />
                      <span>Automations Hub</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
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
