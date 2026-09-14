import { Settings as SettingsIcon, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import type { PreferenceDef, UserPreferences } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { PreferenceGroup } from "@/components/preference-group";

export default async function SettingsPage() {
  const session = await getSession();
  const [defs, prefs] = await Promise.all([
    backendFetch<PreferenceDef[]>("/api/settings/definitions"),
    session
      ? backendFetch<UserPreferences>(`/api/users/${session.sub}/preferences`)
      : Promise.resolve<UserPreferences>({ values: {} }),
  ]);

  // Grouped by each def's `group` field (e.g. "Dashboard"), in the order
  // groups first appear in the registry - purely data-driven, so a new
  // preference (backend/app/preferences.py) gets its own section
  // automatically without any change here.
  const groups = new Map<string, PreferenceDef[]>();
  for (const def of defs) {
    if (!groups.has(def.group)) groups.set(def.group, []);
    groups.get(def.group)!.push(def);
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div className="border-b border-border/80 pb-5">
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles className="size-3.5" />
          <span>Settings</span>
        </div>
        <h1 className="editorial-title text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          How the app behaves for you
        </h1>
        <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
          These are personal to your account — changing one only changes what you see, and takes
          effect immediately, no page reload needed.
        </p>
      </div>

      {!session && (
        <Card className="editorial-card border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-4 text-sm text-muted-foreground">
            You&apos;re not signed in, so changes here can&apos;t be saved. Sign in to set your own preferences.
          </CardContent>
        </Card>
      )}

      {[...groups.entries()].map(([groupName, groupDefs]) => (
        <div key={groupName} className="flex flex-col gap-4">
          <h2 className="editorial-heading text-lg font-bold text-foreground">{groupName}</h2>
          {groupDefs.map((def) => (
            <PreferenceGroup
              key={def.key}
              def={def}
              value={prefs.values[def.key] ?? def.default}
              userId={session?.sub ?? null}
            />
          ))}
        </div>
      ))}

      {defs.length === 0 && (
        <Card className="editorial-card">
          <CardContent className="flex flex-col items-center gap-2 py-14 text-center text-sm text-muted-foreground">
            <SettingsIcon className="size-8 opacity-40" />
            <p className="font-medium text-foreground">No settings yet.</p>
            <p>Nothing to configure right now — check back as more preferences are added.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
