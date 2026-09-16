"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Settings } from "lucide-react";
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
import { canUseAutomations } from "@/lib/access";
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
              className="gap-3 hover:bg-sidebar-accent/80 transition-colors"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-sidebar-primary/15 border border-sidebar-primary/30 text-sidebar-primary font-serif font-black text-sm shadow-xs">
                BMI
              </div>
              <div className="flex flex-col text-left leading-tight">
                <span className="font-serif font-bold tracking-tight text-sidebar-foreground text-[14px]">
                  BMI Publishing
                </span>
                <span className="text-[10.5px] font-medium text-sidebar-foreground/60">
                  Sales &amp; Editorial CRM
                </span>
              </div>
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
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {canUseAutomations(session) && (
          <SidebarGroup>
            <SidebarGroupLabel className="text-[11px] font-bold tracking-wider">Automations</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu className="gap-1.5">
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={<Link href="/automations" />}
                    isActive={pathname === "/automations"}
                    className={NAV_ITEM}
                  >
                    Overview
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={<Link href="/automations/review" />}
                    isActive={pathname.startsWith("/automations/review")}
                    className={NAV_ITEM}
                  >
                    Review queue
                  </SidebarMenuButton>
                </SidebarMenuItem>
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
