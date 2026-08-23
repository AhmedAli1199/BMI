"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
import { automations, type RequirementStage } from "@/lib/requirements-data";
import type { SessionPayload } from "@/lib/session";

const STAGE_LABELS: Record<Exclude<RequirementStage, "overview">, string> = {
  foundation: "Foundation",
  stage1: "Stage 1 — Clean Foundation",
  stage2: "Stage 2 — Living Memory + AI Chat",
  stage3: "Stage 3 — Daily Engine",
  stage4: "Stage 4 — Reporting & Leadership",
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

  const overviewItems = automations.filter((a) => a.stage === "overview");

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
          <SidebarGroupLabel>Overview</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/requirements" />}
                  isActive={pathname === "/requirements"}
                >
                  All automations
                </SidebarMenuButton>
              </SidebarMenuItem>
              {overviewItems
                .filter((a) => a.id !== "overview")
                .map((item) => (
                  <SidebarMenuItem key={item.id}>
                    <SidebarMenuButton
                      render={<Link href={`/requirements/${item.id}`} />}
                      isActive={pathname === `/requirements/${item.id}`}
                    >
                      {item.name}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/docs/original-spec" />}
                  isActive={pathname === "/docs/original-spec"}
                >
                  Original spec (raw)
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {STAGE_ORDER.map((stage) => {
          const items = automations.filter((a) => a.stage === stage);
          if (items.length === 0) return null;
          return (
            <SidebarGroup key={stage}>
              <SidebarGroupLabel>{STAGE_LABELS[stage]}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {items.map((item) => (
                    <SidebarMenuItem key={item.id}>
                      <SidebarMenuButton
                        render={<Link href={`/requirements/${item.id}`} />}
                        isActive={pathname === `/requirements/${item.id}`}
                      >
                        {item.code ?? item.name}
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          );
        })}
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
