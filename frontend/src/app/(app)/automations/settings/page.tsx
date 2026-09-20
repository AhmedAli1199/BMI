import Link from "next/link";
import { ArrowLeft, Settings2, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { AutomationSetting } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AutomationSettingField } from "@/components/automation-setting-field";

export default async function AutomationSettingsPage() {
  const settingsList = await backendFetch<AutomationSetting[]>("/api/automations/settings");

  const groups = new Map<string, AutomationSetting[]>();
  for (const s of settingsList) {
    if (!groups.has(s.group)) groups.set(s.group, []);
    groups.get(s.group)!.push(s);
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div>
        <Link
          href="/automations"
          className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Automations
        </Link>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles className="size-3.5" />
          <span>Automations · Settings</span>
        </div>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Tune every scan
        </h1>
        <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
          Changes here take effect on that scan&apos;s next scheduled run, or the next time you hit
          &quot;Run now&quot; - no restart or redeploy needed. Anything not changed here keeps using its
          env var default.
        </p>
      </div>

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
                <AutomationSettingField key={s.key} setting={s} />
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
