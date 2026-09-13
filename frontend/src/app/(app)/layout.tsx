import { Suspense } from "react";
import { cookies } from "next/headers";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";
import { LiveClock } from "@/components/live-clock";
import { ThemeSwitcher } from "@/components/theme-switcher";
import { PublicationSwitcher } from "@/components/publication-switcher";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const verified = token ? await verifySessionToken(token) : null;
  const session =
    verified ??
    (process.env.NODE_ENV !== "production" || process.env.LOCAL_BYPASS === "true"
      ? {
          sub: "local-dev",
          email: "publisher@bmipublishing.co.uk",
          name: "Editorial Team",
          role: "admin",
        }
      : null);

  return (
    <SidebarProvider>
      <AppSidebar session={session} />
      <SidebarInset>
        <header className="app-topbar flex h-14 shrink-0 items-center gap-3 border-b border-sidebar-border px-4 text-sidebar-foreground">
          <SidebarTrigger className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
          <Separator orientation="vertical" className="h-5 bg-sidebar-border" />
          <span className="hidden text-[15px] font-semibold text-sidebar-foreground/90 md:inline">
            BMI Publishing
          </span>
          <Separator orientation="vertical" className="hidden h-5 bg-sidebar-border md:block" />
          <Suspense fallback={<div className="h-8 w-24 rounded bg-sidebar-accent/40 animate-pulse" />}>
            <PublicationSwitcher />
          </Suspense>
          <LiveClock className="ml-auto text-[15px] font-semibold text-sidebar-foreground" />
          <ThemeSwitcher />
        </header>
        <div className="flex flex-1 flex-col overflow-y-auto">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
