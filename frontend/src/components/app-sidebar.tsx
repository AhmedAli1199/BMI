"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BadgePoundSterling,
  Banknote,
  Building2,
  CalendarClock,
  CalendarDays,
  CalendarRange,
  ChevronRight,
  ClipboardCheck,
  Coins,
  Ellipsis,
  FileText,
  HeartPulse,
  House,
  LayoutDashboard,
  Mail,
  MessageSquareText,
  Mic,
  Newspaper,
  ReceiptText,
  Send,
  Settings,
  Tags,
  Users,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import { BrainBuddy } from "@/components/brain/brain-buddy";
import { LogoutButton } from "@/components/logout-button";
import { canUseAutomations, canViewAutomationsQueue } from "@/lib/access";
import type { SessionPayload } from "@/lib/session";
import type { WorkstreamSummary } from "@/lib/types";
import type { SectionKey } from "@/lib/sections";

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
  salesOverdue = 0,
  hidden = [],
}: {
  session: SessionPayload | null;
  workstreams?: WorkstreamSummary[];
  scanners?: { active: number; total: number };
  salesOverdue?: number;
  /** Sections an admin has hidden for this person's role. */
  hidden?: SectionKey[];
}) {
  const pathname = usePathname();
  const show = (key: SectionKey) => !hidden.includes(key);
  const salesKeys: SectionKey[] = [
    "sales_overview",
    "sales_dashboard",
    "editions",
    "bookings",
    "renewals",
    "proposals",
    "orders",
    "rate_card",
    "invoicing",
    "commissions",
  ];
  // Weekly summary is a staff page that can't be hidden, so staff always keep the Sales Orders menu.
  const anySales = salesKeys.some(show) || canUseAutomations(session);
  const moreSales = [
    show("bookings") && { href: "/sales/bookings", label: "All items" },
    show("renewals") && { href: "/sales/renewals", label: "Renewals" },
    canUseAutomations(session) && { href: "/sales/summaries", label: "Weekly summary" },
    canUseAutomations(session) && { href: "/sales/costs", label: "Costs & profit" },
  ].filter(Boolean) as { href: string; label: string }[];
  const inMore = moreSales.some((m) => pathname === m.href);
  const [moreOpen, setMoreOpen] = useState(inMore);
  const [wasInMore, setWasInMore] = useState(inMore);
  if (inMore !== wasInMore) {
    setWasInMore(inMore);
    if (inMore) setMoreOpen(true);
  }
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
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              <NavItem href="/" label="Home" icon={House} active={pathname === "/"} />
              {canViewAutomationsQueue(session) && show("today") && (
                <NavItem href="/automations/today" label="Today" icon={CalendarClock} active={pathname.startsWith("/automations/today")} />
              )}
              {(show("calendar") || show("reminders")) && (
                <NavItem href={show("calendar") ? "/activities" : "/reminders"} label="Calendar & Reminders" icon={CalendarDays}
                  active={pathname.startsWith("/activities") || pathname.startsWith("/reminders")} />
              )}
              {show("calls") && <NavItem href="/calls" label="Call notes" icon={Mic} active={pathname.startsWith("/calls")} />}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {(show("contacts") || show("companies") || show("groups")) && (
          <NavGroup label="Clients">
            {show("contacts") && <NavItem href="/contacts" label="Contacts" icon={Users} active={pathname.startsWith("/contacts")} />}
            {show("companies") && <NavItem href="/companies" label="Companies" icon={Building2} active={pathname.startsWith("/companies")} />}
            {show("groups") && <NavItem href="/groups" label="Groups" icon={Tags} active={pathname.startsWith("/groups")} />}
          </NavGroup>
        )}

        {session && anySales && (
          <NavGroup label="Sales">
            {(show("sales_overview") || show("sales_dashboard")) && (
              <NavItem href="/sales" label="Overview" icon={LayoutDashboard} active={pathname === "/sales" || pathname === "/sales/dashboard"} />
            )}
            {show("orders") && <NavItem href="/sales/deals" label="Bookings" icon={ReceiptText} active={pathname.startsWith("/sales/deals")} />}
            {show("proposals") && <NavItem href="/sales/proposals" label="Proposals" icon={FileText} active={pathname.startsWith("/sales/proposals")} />}
            {show("rate_card") && <NavItem href="/sales/rate-card" label="Rate card" icon={BadgePoundSterling} active={pathname.startsWith("/sales/rate-card")} />}
            {show("editions") && <NavItem href="/sales/editions" label="Editions" icon={Newspaper} active={pathname.startsWith("/sales/editions") || pathname === "/sales/compare"} />}
            {show("invoicing") && (
              <NavItem href="/sales/invoicing" label="Invoicing" icon={Banknote} active={pathname === "/sales/invoicing"}
                badge={salesOverdue > 0 ? salesOverdue.toLocaleString("en-GB") : undefined} badgeTitle="Bookings overdue for an invoice" />
            )}
            {show("commissions") && (
              <NavItem href="/sales/commissions" label={canUseAutomations(session) ? "Commissions" : "My commission"} icon={Coins}
                active={pathname.startsWith("/sales/commissions")} />
            )}
            {moreSales.length > 0 && (
              <Collapsible open={moreOpen} onOpenChange={setMoreOpen} render={<SidebarMenuItem />}>
                <CollapsibleTrigger render={<SidebarMenuButton isActive={inMore && !moreOpen} className={NAV_ITEM} />}>
                  <Ellipsis className={iconCls(inMore)} />
                  <span>More</span>
                  <ChevronRight aria-hidden="true" className={`ml-auto size-4! shrink-0 text-sidebar-foreground/60 transition-transform duration-200 ${moreOpen ? "rotate-90" : ""}`} />
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <SidebarMenuSub className="mt-1">
                    {moreSales.map((m) => <HubSubItem key={m.href} href={m.href} label={m.label} active={pathname === m.href} />)}
                  </SidebarMenuSub>
                </CollapsibleContent>
              </Collapsible>
            )}
          </NavGroup>
        )}

        {show("editorial") && (
          <NavGroup label="Editorial">
            <NavItem href="/editorial" label="Editorial plan" icon={CalendarRange} active={pathname.startsWith("/editorial")} />
          </NavGroup>
        )}

        {(show("mail_merge") || show("email_templates")) && (
          <NavGroup label="Outreach">
            {show("mail_merge") && (
              <NavItem href="/mail-merge" label="Mail merge" icon={Send}
                active={pathname.startsWith("/mail-merge") && !pathname.startsWith("/mail-merge/templates")} />
            )}
            {show("email_templates") && <NavItem href="/mail-merge/templates" label="Email templates" icon={Mail} active={pathname.startsWith("/mail-merge/templates")} />}
          </NavGroup>
        )}

        {session && (
          <NavGroup label="The Brain">
            <SidebarMenuItem>
              <SidebarMenuButton render={<Link href="/brain" />} isActive={pathname.startsWith("/brain")} className={NAV_ITEM}>
                <BrainBuddy head mood="happy" size={20} still className="mr-1.5" />
                <span>Chat with the Brain</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            {canViewAutomationsQueue(session) && show("review_queue") && (
              <NavItem href="/automations/review" label="Review Queue" icon={ClipboardCheck} active={pathname.startsWith("/automations/review")} />
            )}
            {/* The job/settings/cost control panel - admins and data managers only (Today and the Review Queue are
                open to sales too, scoped to their own data server-side - see lib/access.ts). */}
            {canUseAutomations(session) && show("automations_hub") && (
              <Collapsible open={hubOpen} onOpenChange={setHubOpen} render={<SidebarMenuItem />}>
                <CollapsibleTrigger render={<SidebarMenuButton isActive={inHub && !hubOpen} className={NAV_ITEM} />}>
                  <Workflow className={iconCls(inHub)} />
                  <span>Automations</span>
                  {!hubOpen && hubPending > 0 && (
                    <span className="ml-auto rounded-full bg-amber-600 px-1.5 py-px text-[10.5px] font-bold text-white tabular-nums">
                      {hubPending.toLocaleString("en-GB")}
                    </span>
                  )}
                  <ChevronRight aria-hidden="true"
                    className={`${!hubOpen && hubPending > 0 ? "" : "ml-auto"} size-4! shrink-0 text-sidebar-foreground/60 transition-transform duration-200 ${hubOpen ? "rotate-90" : ""}`} />
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <SidebarMenuSub className="mt-1">
                    <HubSubItem href="/automations" label="Overview" active={pathname === "/automations"} />
                    {workstreams.map((w) => (
                      <HubSubItem key={w.id} href={`/automations/${w.id}`} label={w.label} active={pathname === `/automations/${w.id}`}
                        badge={w.pending > 0 ? w.pending.toLocaleString("en-GB") : undefined} />
                    ))}
                    <HubSubItem href="/automations/engine" label="Scanners & Settings"
                      active={pathname === "/automations/engine" || pathname === "/automations/settings"}
                      badge={scanners && scanners.total > 0 ? `${scanners.active}/${scanners.total}` : undefined} badgeTone="neutral" />
                  </SidebarMenuSub>
                </CollapsibleContent>
              </Collapsible>
            )}
            {canUseAutomations(session) && show("data_health") && (
              <NavItem href="/data-health" label="Data Health" icon={HeartPulse} active={pathname === "/data-health"} />
            )}
          </NavGroup>
        )}
      </SidebarContent>
      <SidebarFooter>
        {session && (
          <div className="flex flex-col gap-2 px-2 py-1.5">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{session.name}</p>
              <p className="truncate text-xs text-sidebar-foreground/60">
                {ROLE_LABELS[session.role] ?? session.role}
              </p>
            </div>
            <div className="flex items-center gap-1">
              <Button
                nativeButton={false}
                size="icon-sm"
                variant="outline"
                title="Feedback"
                aria-label="Feedback"
                render={<Link href="/feedback" />}
                className={`border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground ${
                  pathname.startsWith("/feedback") ? "bg-sidebar-accent text-sidebar-accent-foreground" : ""
                }`}
              >
                <MessageSquareText className="size-4" />
              </Button>
              <Button
                nativeButton={false}
                size="icon-sm"
                variant="outline"
                title="Settings"
                aria-label="Settings"
                render={<Link href="/settings" />}
                className={`border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground ${
                  pathname === "/settings"
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : ""
                }`}
              >
                <Settings className="size-4" />
              </Button>
              <LogoutButton className="ml-auto border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
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

const iconCls = (on: boolean) => `mr-1.5 size-4 ${on ? "text-primary" : "text-sidebar-foreground/70"}`;

function NavGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <SidebarGroup className="py-1">
      <SidebarGroupLabel className="text-[11px] font-bold tracking-wider">{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu className="gap-1">{children}</SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

function NavItem({ href, label, icon: Icon, active, badge, badgeTitle }: {
  href: string; label: string; icon: LucideIcon; active: boolean; badge?: string; badgeTitle?: string;
}) {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton render={<Link href={href} />} isActive={active} aria-current={active ? "page" : undefined} className={NAV_ITEM}>
        <Icon className={iconCls(active)} />
        <span>{label}</span>
        {badge && (
          <span className="ml-auto rounded-full bg-amber-600 px-1.5 py-px text-[10.5px] font-bold text-white tabular-nums" title={badgeTitle}>
            {badge}
          </span>
        )}
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}
