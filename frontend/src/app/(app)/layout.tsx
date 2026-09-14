import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { getSession } from "@/lib/session";
import { LiveClock } from "@/components/live-clock";
import { ThemeSwitcher } from "@/components/theme-switcher";
import { PublicationSwitcher } from "@/components/publication-switcher";
import { getPublicationFilter } from "@/lib/publication";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  const publicationFilter = await getPublicationFilter();

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
          <PublicationSwitcher current={publicationFilter} />
          <LiveClock className="ml-auto text-[15px] font-semibold text-sidebar-foreground" />
          <ThemeSwitcher />
        </header>
        <div className="flex flex-1 flex-col overflow-y-auto">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
