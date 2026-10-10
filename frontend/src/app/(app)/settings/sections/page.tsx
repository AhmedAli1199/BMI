import Link from "next/link";
import { ArrowLeft, ShieldAlert, Sparkles } from "lucide-react";
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
      <div className="border-b border-border/80 pb-5">
        <Link href="/settings" className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          Settings
        </Link>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles className="size-3.5" aria-hidden="true" />
          <span>Sections people see</span>
        </div>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Keep the screens simple</h1>
        <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
          Untick a section to take it out of the menu for that role. Administrators always see everything. Hiding a section
          only tidies the menu: it doesn&apos;t change what anyone is allowed to see or do, which is still set under Team &amp; access.
        </p>
      </div>
      <SectionsEditor info={info} />
    </div>
  );
}
