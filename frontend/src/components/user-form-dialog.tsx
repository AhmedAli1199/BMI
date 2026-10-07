"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Copy, Plus, Shuffle, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { createTeamUser, listGroupsForDatabase, listSalesRepsForLogins, updateTeamUser } from "@/lib/actions";
import type { GroupListItem, Publication, RoleDef, UserAccessEntry, UserAccount } from "@/lib/types";

type AccessRow = { source_db: string; group_id: string | null };

/** A random, easy-to-read-aloud temporary password - excludes visually
 * confusable characters (0/O, 1/l/I) since this is meant to be read over
 * a call or typed from a note, not just pasted. */
function generatePassword(): string {
  const chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";
  const bytes = new Uint32Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => chars[b % chars.length]).join("");
}

function AccessRowEditor({
  row,
  publications,
  onChange,
  onRemove,
}: {
  row: AccessRow;
  publications: Publication[];
  onChange: (row: AccessRow) => void;
  onRemove: () => void;
}) {
  const [groups, setGroups] = useState<GroupListItem[]>([]);

  useEffect(() => {
    if (!row.source_db) return;
    listGroupsForDatabase(row.source_db).then(setGroups);
  }, [row.source_db]);

  const visibleGroups = row.source_db ? groups : [];

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border/70 bg-muted/20 p-2.5">
      <select
        className="h-8 flex-1 rounded-md border border-input bg-background px-2 text-xs"
        value={row.source_db}
        onChange={(e) => onChange({ source_db: e.target.value, group_id: null })}
      >
        <option value="" disabled>
          Choose a database…
        </option>
        {publications.map((p) => (
          <option key={p.slug} value={p.slug}>
            {p.name}
          </option>
        ))}
      </select>
      <select
        className="h-8 flex-1 rounded-md border border-input bg-background px-2 text-xs disabled:opacity-50"
        value={row.group_id ?? ""}
        disabled={!row.source_db}
        onChange={(e) => onChange({ ...row, group_id: e.target.value || null })}
      >
        <option value="">Full database (no group restriction)</option>
        {visibleGroups.map((g) => (
          <option key={g.id} value={g.id}>
            {"—".repeat(g.hier_level ?? 0)} {g.name}
          </option>
        ))}
      </select>
      <Button type="button" size="icon-sm" variant="ghost" onClick={onRemove} title="Remove this grant">
        <Trash2 className="size-3.5 text-destructive" />
      </Button>
    </div>
  );
}

/** Handles both creating a new team account and editing an existing one -
 * see backend/app/roles.py (role -> what they can do) and
 * app/models/user_access.py (access rows -> what data they can see). An
 * admin submits the FULL access list on every save (not a diff), matching
 * how PATCH /api/users/{id} treats `access` - replace, not merge. */
export function UserFormDialog({
  existing,
  roles,
  publications,
  trigger,
}: {
  existing?: UserAccount;
  roles: RoleDef[];
  publications: Publication[];
  trigger?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  const [name, setName] = useState(existing?.name ?? "");
  const [email, setEmail] = useState(existing?.email ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(existing?.role ?? roles[0]?.value ?? "sales");
  const [access, setAccess] = useState<AccessRow[]>(
    existing?.access.map((a) => ({ source_db: a.source_db, group_id: a.group_id })) ?? []
  );
  const [repId, setRepId] = useState<string>(existing?.sales_rep_id ?? "");
  const [repTouched, setRepTouched] = useState(false);
  const [reps, setReps] = useState<{ id: string; code: string; name: string; active: boolean; has_login: boolean }[] | null>(null);

  useEffect(() => {
    if (!open || reps) return;
    let live = true;
    listSalesRepsForLogins().then((r) => live && setReps(r)).catch(() => live && setReps([]));
    return () => { live = false; };
  }, [open, reps]);

  // Suggest the salesperson with the same name for a new login (or one not linked yet).
  const suggested = !repTouched && !repId && reps ? reps.find((r) => !r.has_login && r.name.trim().toLowerCase() === name.trim().toLowerCase()) : undefined;
  const chosenRep = repId || suggested?.id || "";

  function addRow() {
    setAccess([...access, { source_db: publications[0]?.slug ?? "", group_id: null }]);
  }

  function submit() {
    startTransition(async () => {
      try {
        if (existing) {
          await updateTeamUser(existing.id, {
            name,
            role,
            password: password || undefined,
            access: access as UserAccessEntry[],
            sales_rep_id: chosenRep !== (existing.sales_rep_id ?? "") ? chosenRep || null : undefined,
          });
          toast.success(`${name} updated`);
        } else {
          if (!password) {
            toast.error("Set a temporary password");
            return;
          }
          await createTeamUser({ email, name, password, role, access: access as UserAccessEntry[], sales_rep_id: chosenRep || null });
          toast.success(`${name} added`);
        }
        setOpen(false);
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't save this account");
      }
    });
  }

  const canSubmit = name.trim() && (existing || email.trim()) && role && (existing || password) && (role === "admin" || access.length > 0);

  return (
    <>
      {trigger ? (
        <span onClick={() => setOpen(true)}>{trigger}</span>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plus className="size-4" />
          Add team member
        </Button>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{existing ? `Edit ${existing.name}` : "Add a team member"}</DialogTitle>
            <DialogDescription>
              {existing
                ? "Change their role, database access, or reset their password."
                : "Creates a real login. Set a temporary password and share it securely - never over chat."}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="uf-name">Name</Label>
                <Input id="uf-name" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="uf-email">Email</Label>
                <Input
                  id="uf-email"
                  type="email"
                  value={email}
                  disabled={!!existing}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="uf-password">
                {existing ? "Reset password" : "Temporary password"}
                {!existing && <span className="text-destructive"> *</span>}
              </Label>
              <div className="flex items-center gap-1.5">
                <Input
                  id="uf-password"
                  type="text"
                  placeholder={existing ? "Leave blank to keep their current password" : "At least 8 characters"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="flex-1"
                />
                <Button
                  type="button"
                  size="icon-sm"
                  variant="outline"
                  title="Generate a random password"
                  onClick={() => setPassword(generatePassword())}
                >
                  <Shuffle className="size-3.5" />
                </Button>
                {password && (
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="outline"
                    title="Copy to clipboard"
                    onClick={async () => {
                      await navigator.clipboard.writeText(password);
                      toast.success("Password copied - share it securely, never over chat.");
                    }}
                  >
                    <Copy className="size-3.5" />
                  </Button>
                )}
              </div>
              {existing && password && (
                <p className="text-[11px] text-muted-foreground">
                  Saving will reset {existing.name}&apos;s password to this - they&apos;ll need it to log in again.
                </p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label>Role</Label>
              <div className="flex flex-wrap gap-1.5">
                {roles.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    onClick={() => setRole(r.value)}
                    className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors ${
                      role === r.value
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:bg-accent/40"
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="uf-rep">Their initials in the order register</Label>
              <select
                id="uf-rep"
                value={chosenRep}
                onChange={(e) => { setRepId(e.target.value); setRepTouched(true); }}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
              >
                <option value="">Not a salesperson</option>
                {(reps ?? []).filter((r) => r.active || r.id === chosenRep).map((r) => (
                  <option key={r.id} value={r.id} disabled={r.has_login && r.id !== (existing?.sales_rep_id ?? "")}>
                    {r.code} - {r.name}{r.has_login && r.id !== (existing?.sales_rep_id ?? "") ? " (linked to another login)" : ""}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-muted-foreground">
                {suggested ? `Picked ${suggested.code} because the names match - change it if that's wrong. ` : ""}
                Their renewals and booking follow-ups go on their Today list, and only they see them.
              </p>
            </div>

            {role === "admin" ? (
              <p className="rounded-lg border border-primary/20 bg-primary/5 p-2.5 text-xs text-muted-foreground">
                Administrators see every database automatically - no access grants needed.
              </p>
            ) : (
              <div className="flex flex-col gap-1.5">
                <Label>Database access</Label>
                {access.map((row, i) => (
                  <AccessRowEditor
                    key={i}
                    row={row}
                    publications={publications}
                    onChange={(r) => setAccess(access.map((a, j) => (j === i ? r : a)))}
                    onRemove={() => setAccess(access.filter((_, j) => j !== i))}
                  />
                ))}
                <Button type="button" size="sm" variant="outline" onClick={addRow} className="self-start">
                  <Plus className="size-3.5" />
                  Add database
                </Button>
                {access.length === 0 && (
                  <p className="text-[11px] text-destructive">
                    Needs at least one database grant, or they&apos;ll see nothing.
                  </p>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !canSubmit}>
              {pending ? "Saving…" : existing ? "Save changes" : "Create account"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
