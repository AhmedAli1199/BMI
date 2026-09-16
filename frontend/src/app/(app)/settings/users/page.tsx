import Link from "next/link";
import { ArrowLeft, ShieldAlert, Sparkles, Users } from "lucide-react";
import { getSession } from "@/lib/session";
import { canManageUsers } from "@/lib/access";
import { listPublications, listRoles, listTeamUsers } from "@/lib/actions";
import { Card, CardContent } from "@/components/ui/card";
import { TeamRoster } from "@/components/team-roster";
import { UserFormDialog } from "@/components/user-form-dialog";

export default async function TeamSettingsPage() {
  const session = await getSession();

  if (!canManageUsers(session)) {
    return (
      <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-3 p-6 pt-24 text-center">
        <ShieldAlert className="size-8 text-muted-foreground opacity-60" />
        <h1 className="text-lg font-bold text-foreground">Administrators only</h1>
        <p className="text-sm text-muted-foreground">
          Team and access management is restricted to Administrator accounts. Ask an admin if you need a change
          made here.
        </p>
        <Link href="/settings" className="text-xs font-semibold text-primary hover:underline">
          Back to Settings
        </Link>
      </div>
    );
  }

  const [users, roles, publications] = await Promise.all([listTeamUsers(), listRoles(), listPublications()]);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div className="border-b border-border/80 pb-5">
        <Link
          href="/settings"
          className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Settings
        </Link>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles className="size-3.5" />
          <span>Team &amp; access</span>
        </div>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Who can see what
            </h1>
            <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
              Each account gets a role (what they can do) and one or more database/group grants (what data they
              can see). A role alone never grants access to data — see each role&apos;s description below.
            </p>
          </div>
          <UserFormDialog roles={roles} publications={publications} />
        </div>
      </div>

      {/* Role reference - shown once, plainly, so nobody has to guess what
          "Data Manager" actually means before picking it. */}
      <div className="grid gap-3 sm:grid-cols-3">
        {roles.map((r) => (
          <Card key={r.value} className="editorial-card">
            <CardContent className="p-4">
              <p className="text-sm font-bold text-foreground">{r.label}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{r.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {users.length > 0 ? (
        <TeamRoster users={users} roles={roles} publications={publications} currentUserId={session?.sub ?? null} />
      ) : (
        <Card className="editorial-card">
          <CardContent className="flex flex-col items-center gap-2 py-14 text-center text-sm text-muted-foreground">
            <Users className="size-8 opacity-40" />
            <p className="font-medium text-foreground">No team accounts yet.</p>
            <p>Add the first one above.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
