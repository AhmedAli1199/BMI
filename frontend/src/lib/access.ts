import type { SessionAccess, SessionPayload } from "@/lib/session";

/** The one place role -> "what can they do" is decided, mirroring
 * backend/app/roles.py's CAN_* sets exactly - keep these two in sync by
 * hand (there's no shared source between a Python and a TS project) if
 * the role tiers ever change. */
export function isAdmin(session: SessionPayload | null): boolean {
  return session?.role === "admin";
}

/** The Automations Hub (job status/control, Settings, LLM cost, the
 * data-reset action) - admin/data_manager only, mirroring backend
 * app/roles.py's CAN_USE_AUTOMATIONS exactly (kept the same name/value
 * there since that's the narrower, hub-facing set its name always meant).
 * A sales rep's own Today/Review Queue views are a separate, wider grant -
 * see canViewAutomationsQueue below. */
export function canUseAutomations(session: SessionPayload | null): boolean {
  return session?.role === "admin" || session?.role === "data_manager";
}

/** Whether this session can see a Today/Review Queue view at all - every
 * role now, including sales (mirrors backend app/roles.py's
 * CAN_VIEW_OWN_QUEUE). WHAT they see within it is scoped server-side by
 * kind audience + database (+ owner for a sales rep's Today queue) - see
 * backend/app/api/routes/review_queue.py's _apply_scope and
 * automations.py's get_today_queue. */
export function canViewAutomationsQueue(session: SessionPayload | null): boolean {
  return session?.role === "admin" || session?.role === "data_manager" || session?.role === "sales";
}

export function canManageUsers(session: SessionPayload | null): boolean {
  return session?.role === "admin";
}

export function canAddDatabase(session: SessionPayload | null): boolean {
  return session?.role === "admin";
}

/** Every database slug this session may see at all (ignoring any group
 * restriction within it) - an admin sees every registered Publication,
 * which this can't know on its own, so callers pass the full list down
 * for an admin and use this only to filter it for everyone else. */
export function allowedSourceDbSlugs(session: SessionPayload | null): string[] {
  if (!session) return [];
  return [...new Set(session.access.map((a) => a.source_db))];
}

/** Clamps a requested source_db (typically the publication cookie's
 * value) to what this session is actually allowed to see, and resolves
 * any group restriction that applies to it - the one function every
 * list page calls before querying the backend. Admins pass through
 * untouched (requestedSourceDb === "" is valid for them = "all titles",
 * which no one else is ever allowed). A non-admin session with zero
 * access rows fails closed (returns a source_db that matches nothing)
 * rather than silently showing everything.
 */
export function resolveScope(
  session: SessionPayload | null,
  requestedSourceDb: string
): { source_db: string; group_id: string | null; group_name: string | null; locked: boolean } {
  if (!session) return { source_db: requestedSourceDb, group_id: null, group_name: null, locked: false };
  if (session.role === "admin") {
    return { source_db: requestedSourceDb, group_id: null, group_name: null, locked: false };
  }

  const access = session.access;
  if (access.length === 0) {
    return { source_db: "__no_access__", group_id: null, group_name: null, locked: true };
  }

  const match = access.find((a) => a.source_db === requestedSourceDb) ?? access[0];
  // "locked" - true whenever this session has exactly one allowed scope,
  // so the UI can skip showing a switcher that would only ever have one
  // real choice in it.
  return { ...match, locked: access.length === 1 };
}

/** Whether a specific record's own source_db (and, for a group-scoped
 * grant, group membership) falls inside this session's allowed access -
 * used on detail pages (a contact/company/group fetched by ID) to reject
 * access to a record outside their scope rather than trusting that the
 * list pages' filtering was the only way in. groupIdsOfRecord should be
 * the direct group memberships a ContactDetail/CompanyDetail already
 * returns; subtreeGroupIds (when the session's grant is group-scoped)
 * should be fetched via /api/groups?root_group_id=... and checked for
 * overlap - see contacts/[id]/page.tsx for the concrete usage. */
export function canAccessRecord(
  session: SessionPayload | null,
  sourceDb: string,
  groupIdsOfRecord: string[],
  subtreeGroupIdsForScope: string[] | null
): boolean {
  if (!session || session.role === "admin") return true;
  const grant = session.access.find((a) => a.source_db === sourceDb);
  if (!grant) return false;
  if (!grant.group_id) return true; // full-database grant
  if (!subtreeGroupIdsForScope) return false; // group-scoped but caller didn't check membership - fail closed
  return groupIdsOfRecord.some((id) => subtreeGroupIdsForScope.includes(id));
}

export function accessLabel(a: SessionAccess): string {
  return a.group_name ? `${a.source_db} / ${a.group_name}` : a.source_db;
}
