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
import { automations, type RequirementStage } from "@/lib/requirements-data";
import type { SessionPayload } from "@/lib/session";

const STAGE_LABELS: Record<Exclude<RequirementStage, "overview">, string> = {
  foundation: "Foundation",
  stage1: "Stage 1: Clean Foundation",
  stage2: "Stage 2: Living Memory + AI Chat",
  stage3: "Stage 3: Daily Engine",
  stage4: "Stage 4: Reporting & Leadership",
};

const STAGE_ORDER: Exclude<RequirementStage, "overview">[] = [
  "foundation",
  "stage1",
  "stage2",
  "stage3",
  "stage4",
];

export function AppSidebar({ session }: { session: SessionPayload | null }) {
  const pathname = usePathname();

  const isDocsActive = pathname.startsWith("/docs");

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link href="/" />}
              isActive={pathname === "/"}
            >
              <span className="font-semibold">BMI Sales Brain</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Platform</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/" />}
                  isActive={pathname === "/"}
                >
                  Dashboard
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/contacts" />}
                  isActive={pathname.startsWith("/contacts")}
                >
                  Contacts
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/companies" />}
                  isActive={pathname.startsWith("/companies")}
                >
                  Companies
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/requirements" />}
                  isActive={pathname === "/requirements"}
                >
                  Requirements &amp; questions
                </SidebarMenuButton>
              </SidebarMenuItem>

              {STAGE_ORDER.map((stage) => {
                const items = automations.filter((a) => a.stage === stage);
                if (items.length === 0) return null;
                const isStageActive = items.some(
                  (item) => pathname === `/requirements/${item.id}`
                );
                return (
                  <Collapsible
                    key={stage}
                    defaultOpen={isStageActive}
                    className="group/collapsible"
                  >
                    <SidebarMenuItem>
                      <CollapsibleTrigger render={<SidebarMenuButton />}>
                        {STAGE_LABELS[stage]}
                        <ChevronRight className="ml-auto transition-transform group-data-[panel-open]/collapsible:rotate-90" />
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <SidebarMenuSub>
                          {items.map((item) => (
                            <SidebarMenuSubItem key={item.id}>
                              <SidebarMenuSubButton
                                render={<Link href={`/requirements/${item.id}`} />}
                                isActive={pathname === `/requirements/${item.id}`}
                              >
                                {item.code ?? item.name}
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          ))}
                        </SidebarMenuSub>
                      </CollapsibleContent>
                    </SidebarMenuItem>
                  </Collapsible>
                );
              })}

              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/docs/original-spec" />}
                  isActive={isDocsActive}
                >
                  Original spec (raw)
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        {session && (
          <div className="flex items-center justify-between gap-2 px-2 py-1.5">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{session.name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {session.email}
              </p>
            </div>
            <LogoutButton />
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
