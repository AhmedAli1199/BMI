import Link from "next/link";
import { Settings2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { isAdmin } from "@/lib/access";
import type { AutomationSetting } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AutomationSettingField } from "@/components/automation-setting-field";

export default async function AutomationSettingsPage() {
  const [settingsList, session] = await Promise.all([backendFetch<AutomationSetting[]>("/api/automations/settings"), getSession()]);
  const readOnly = !isAdmin(session);

  const groups = new Map<string, AutomationSetting[]>();
  for (const s of settingsList) {
    if (!groups.has(s.group)) groups.set(s.group, []);
    groups.get(s.group)!.push(s);
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
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

      <div className="flex flex-col gap-4">
        {[...groups.entries()].map(([group, items]) => (
          <Card key={group} className="editorial-card">
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
  );
}
