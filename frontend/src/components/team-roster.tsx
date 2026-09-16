"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Pencil, Power } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { updateTeamUser } from "@/lib/actions";
import { accessLabel } from "@/lib/access";
import { UserFormDialog } from "@/components/user-form-dialog";
import type { Publication, RoleDef, UserAccount } from "@/lib/types";

const ROLE_BADGE: Record<string, string> = {
  admin: "border-violet-500/30 bg-violet-500/10 text-violet-600",
  data_manager: "border-blue-500/30 bg-blue-500/10 text-blue-600",
  sales: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600",
};

export function TeamRoster({
  users,
  roles,
  publications,
  currentUserId,
}: {
  users: UserAccount[];
  roles: RoleDef[];
  publications: Publication[];
  currentUserId: string | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function toggleActive(user: UserAccount) {
    startTransition(async () => {
      try {
        await updateTeamUser(user.id, { is_active: !user.is_active });
        toast.success(user.is_active ? `${user.name} disabled` : `${user.name} re-enabled`);
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't change that");
      }
    });
  }

  const roleLabel = (value: string) => roles.find((r) => r.value === value)?.label ?? value;

  return (
    <Card className="editorial-card overflow-hidden p-0">
      <div className="flex flex-col divide-y divide-border/70">
        {users.map((u) => (
          <div key={u.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-bold text-foreground">{u.name}</span>
                <Badge variant="outline" className={`text-[10px] font-semibold ${ROLE_BADGE[u.role] ?? ""}`}>
                  {roleLabel(u.role)}
                </Badge>
                {!u.is_active && (
                  <Badge variant="outline" className="border-destructive/30 bg-destructive/10 text-[10px] text-destructive">
                    Disabled
                  </Badge>
                )}
                {u.id === currentUserId && (
                  <Badge variant="secondary" className="text-[10px]">You</Badge>
                )}
              </div>
              <p className="truncate text-xs text-muted-foreground">{u.email}</p>
              {u.role !== "admin" && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {u.access.length > 0 ? (
                    u.access.map((a, i) => (
                      <span key={i} className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                        {accessLabel(a)}
                      </span>
                    ))
                  ) : (
                    <span className="text-[10px] font-medium text-destructive">No database access - can&apos;t see anything</span>
                  )}
                </div>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <UserFormDialog
                existing={u}
                roles={roles}
                publications={publications}
                trigger={
                  <Button size="icon-sm" variant="outline" title="Edit">
                    <Pencil className="size-3.5" />
                  </Button>
                }
              />
              {u.id !== currentUserId && (
                <Button
                  size="icon-sm"
                  variant="outline"
                  disabled={pending}
                  onClick={() => toggleActive(u)}
                  title={u.is_active ? "Disable account" : "Re-enable account"}
                  className={u.is_active ? "text-destructive hover:text-destructive" : "text-emerald-600 hover:text-emerald-600"}
                >
                  <Power className="size-3.5" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
