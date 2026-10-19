import Link from "next/link";
import { Settings2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations, isAdmin } from "@/lib/access";
import { StaffOnly } from "@/components/automations/hub-ui";
import type { AutomationSetting } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AutomationSettingField } from "@/components/automation-setting-field";

const slug = (g: string) => g.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

/** One area at a time (chosen on the left, ?area=), or every area with ?area=all - the full list used to be one very
 * long page. */
export default async function AutomationSettingsPage({ searchParams }: { searchParams: Promise<{ area?: string }> }) {
  const { area } = await searchParams;
  const session = await getSession();
  if (!canUseAutomations(session)) return <StaffOnly />;
  const settingsList = await backendFetch<AutomationSetting[]>("/api/automations/settings");
  const readOnly = !isAdmin(session);

  const groups = new Map<string, AutomationSetting[]>();
  for (const s of settingsList) {
    if (!groups.has(s.group)) groups.set(s.group, []);
    groups.get(s.group)!.push(s);
  }

  const entries = [...groups.entries()];
  const current = area === "all" ? "all" : entries.some(([g]) => slug(g) === area) ? area! : slug(entries[0]?.[0] ?? "");
  const shown = current === "all" ? entries : entries.filter(([g]) => slug(g) === current);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        crumbs={[
          { label: "Automations Hub", href: "/automations" },
          { label: "Scanners & Settings", href: "/automations/engine" },
        ]}
        title="Automation settings"
        description={
          readOnly
            ? "You can see every setting here. Only administrators can change them - ask one if something needs adjusting."
            : <>Changes take effect automatically on the next scheduled run or when you click &quot;Run now&quot;.</>
        }
        actions={
          <Link
            href="/automations/llm-usage"
            className="inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-primary hover:underline"
          >
            View Brain usage &amp; cost &rarr;
          </Link>
        }
      />

      <div className="grid gap-6 md:grid-cols-[16rem_minmax(0,1fr)]">
        <nav aria-label="Areas" className="min-w-0 md:sticky md:top-4 md:self-start">
          <ul className="flex flex-wrap gap-1 md:flex-col md:flex-nowrap">
            {[...groups.entries()].map(([group, items]) => (
              <li key={group} className="min-w-0">
                <Link href={`/automations/settings?area=${slug(group)}`} aria-current={slug(group) === current ? "page" : undefined}
                  title={group} className={`flex w-full min-w-0 items-center justify-between gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                    slug(group) === current ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}>
                  <span className="truncate">{group}</span>
                  <span className="text-[11px] tabular-nums opacity-70">{items.length}</span>
                </Link>
              </li>
            ))}
            <li>
              <Link href="/automations/settings?area=all" aria-current={current === "all" ? "page" : undefined}
                className={`mt-1 block rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  current === "all" ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground hover:bg-accent hover:text-foreground"
                }`}>
                All areas
              </Link>
            </li>
          </ul>
        </nav>

        <div className="flex min-w-0 flex-col gap-4">
          {shown.map(([group, items]) => (
            <Card key={group} id={slug(group)} className="editorial-card">
              <CardHeader className="flex flex-row items-center gap-2 border-b pb-3">
                <span className="brand-icon size-8 shrink-0">
                  <Settings2 className="size-4" />
                </span>
                <span className="text-sm font-bold text-foreground">{group}</span>
              </CardHeader>
              <CardContent className="flex flex-col p-4">
                {items.map((s) => (
                  <AutomationSettingField key={s.key} setting={s} readOnly={readOnly} />
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
