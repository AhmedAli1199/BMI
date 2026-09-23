import { Plus } from "lucide-react";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { getSession } from "@/lib/session";
import { PublicationSwitcher } from "@/components/publication-switcher";
import { LogInteractionDialog } from "@/components/log-interaction-dialog";
import { getPublicationFilter } from "@/lib/publication";
import { listPublications } from "@/lib/actions";
import { allowedSourceDbSlugs } from "@/lib/access";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  const [publicationFilter, allPublications] = await Promise.all([
    getPublicationFilter(),
    listPublications(),
  ]);
  // Same rule as the dashboard's own tiles (page.tsx) - a non-admin only
  // ever sees their own granted title(s) as switcher options, never the
  // other two just to immediately be told "no access" after picking one.
  const publications =
    session?.role === "admin"
      ? allPublications
      : allPublications.filter((p) => allowedSourceDbSlugs(session).includes(p.slug));

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
          <PublicationSwitcher
            current={publicationFilter}
            publications={publications}
            locked={session?.role !== "admin" && publications.length <= 1}
          />
          {session && (
            <LogInteractionDialog
              global
              trigger={
                <Button size="sm" className="gap-1.5">
                  <Plus className="size-4" />
                  <span className="hidden sm:inline">Log or schedule</span>
                </Button>
              }
            />
          )}
        </header>
        <div className="flex flex-1 flex-col overflow-y-auto">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
