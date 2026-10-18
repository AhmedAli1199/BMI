import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { getSession } from "@/lib/session";
import { isAdmin } from "@/lib/access";
import { backendFetch } from "@/lib/backend";
import type { SectionsInfo } from "@/lib/sections";
import { SectionsEditor } from "@/components/sections-editor";

export default async function SectionsSettingsPage() {
  const session = await getSession();
  if (!isAdmin(session)) {
    return (
      <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-3 p-6 pt-24 text-center">
        <ShieldAlert className="size-8 text-muted-foreground opacity-60" />
        <h1 className="text-lg font-bold text-foreground">Administrators only</h1>
        <p className="text-sm text-muted-foreground">Only administrators can choose which sections people see.</p>
        <Link href="/settings" className="text-xs font-semibold text-primary hover:underline">
          Back to Settings
        </Link>
      </div>
    );
  }
  const info = await backendFetch<SectionsInfo>("/api/ui/sections");

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        crumbs={[{ label: "Settings", href: "/settings" }]}
        title="Sections people see"
        description={
          <>
            Untick a section to take it out of the menu for that role, or give one person their own choice. Administrators always see
            everything. A hidden section leaves the menu, its pages won&apos;t open for that person and the Brain won&apos;t answer
            about it. Which databases someone can see is still set under Team &amp; access.
          </>
        }
      />
      <SectionsEditor info={info} />
    </div>
  );
}
