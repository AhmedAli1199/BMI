"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import type { SessionPayload } from "@/lib/session";

// Nav items get a deliberately bigger, bolder treatment than shadcn's
// default text-sm - the client asked for this explicitly ("bigger bolder
// for easy viewing"), applied here rather than in the shared ui/sidebar.tsx
// primitive so it's specific to this app's nav, not every future sidebar use.
const NAV_ITEM = "text-[15px] font-semibold [&_svg]:size-[18px]";
const NAV_SUBITEM = "text-[13.5px] font-medium";

export function AppSidebar({ session }: { session: SessionPayload | null }) {
  const pathname = usePathname();

  const isSpecActive = pathname.startsWith("/requirements") || pathname.startsWith("/docs");

  return (
    <Sidebar>
      <SidebarHeader className="relative overflow-hidden">
        <div className="ambient-glow" aria-hidden="true" />
        <div className="ambient-stars" aria-hidden="true" />
        <SidebarMenu className="relative">
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link href="/" />}
              isActive={pathname === "/"}
              className="gap-3"
            >
              <ThemeMotif className="theme-motif size-7 shrink-0" />
              <span className="text-base font-bold tracking-tight">BMI Sales Brain</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-[11px] font-bold tracking-wider">Platform</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
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

        {/* Everything from the original automations planning pass - kept,
            not deleted, but tucked under one collapsed group so it stops
            competing with the actual product for space. Collapsed by
            default; opens automatically if you're already on one of these
            pages (e.g. a direct link). */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <Collapsible defaultOpen={isSpecActive} className="group/collapsible">
                <SidebarMenuItem>
                  <CollapsibleTrigger render={<SidebarMenuButton className={NAV_ITEM} />}>
                    Build spec (reference)
                    <ChevronRight className="ml-auto transition-transform group-data-[panel-open]/collapsible:rotate-90" />
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <SidebarMenuSub>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton
                          render={<Link href="/requirements" />}
                          isActive={pathname === "/requirements"}
                          className={NAV_SUBITEM}
                        >
                          Requirements &amp; questions
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton
                          render={<Link href="/docs/original-spec" />}
                          isActive={pathname.startsWith("/docs")}
                          className={NAV_SUBITEM}
                        >
                          Original spec (raw)
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    </SidebarMenuSub>
                  </CollapsibleContent>
                </SidebarMenuItem>
              </Collapsible>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        {session && (
          <div className="flex items-center justify-between gap-2 px-2 py-1.5">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{session.name}</p>
              <p className="truncate text-xs text-sidebar-foreground/60">
                {session.email}
              </p>
            </div>
            <LogoutButton className="border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
