"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { PUBLICATION_COOKIE } from "@/lib/publication";
import type {
  ActivityOut,
  ActivitiesPage,
  ActivityRecurrence,
  CompanyListItem,
  ContactDetail,
  ContactListItem,
  FieldChange,
  GroupListItem,
  HistoryOut,
  Page,
  Publication,
  ReviewQueueItem,
  RoleDef,
  UserAccessEntry,
  UserAccount,
} from "@/lib/types";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** session.sub is "local-dev" under the auth bypass (see lib/session.ts) -
 * never a real user id. The backend's created_by_user_id columns are typed
 * UUID, so sending that literal string would 422 rather than gracefully
 * becoming "no user" - filter it out here, the one place every caller in
 * this file goes through. */
function currentUserId(sub: string | undefined): string | null {
  return sub && UUID_RE.test(sub) ? sub : null;
}

/** Every CRUD mutation for Contacts/Companies/Groups, callable straight from
 * client components (Next.js server actions run on the server regardless of
 * where they're invoked from - this is how forms/buttons reach the FastAPI
 * backend without ever exposing BACKEND_API_KEY to the browser).
 */

// ---- Publication filter -----------------------------------------------------

/** Sets the site-wide "which publication" filter (see lib/publication.ts).
 * sourceDb === "" clears it back to "All titles". Every page reads this
 * cookie itself and re-fetches on the next render - callers just need to
 * follow this with a router.refresh(). */
export async function setPublicationFilter(sourceDb: string) {
  const store = await cookies();
  if (sourceDb) {
    store.set(PUBLICATION_COOKIE, sourceDb, { path: "/", maxAge: 60 * 60 * 24 * 365 });
  } else {
    store.delete(PUBLICATION_COOKIE);
  }
}

// ---- Contacts --------------------------------------------------------------

export type ContactFormInput = {
  first_name?: string;
  last_name?: string;
  job_title?: string;
  department?: string;
  category?: string;
  referred_by?: string;
  birthdate?: string;
  company_id?: string | null;
  email?: string;
  phone?: string;
  source_db?: string;
};

function cleanPayload<T extends Record<string, unknown>>(input: T): Partial<T> {
  const out: Partial<T> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value !== "" && value !== undefined) out[key as keyof T] = value as T[keyof T];
  }
  return out;
}

/** Same as cleanPayload but for a PATCH/update, where an empty string is a
 * real, intentional edit ("clear this field out") rather than "field not
 * filled in yet" - dropping it here silently turned "clear the name" into
 * a no-op that never reached the backend, so nothing changed on the page,
 * on reload, or in the field-change history. Only `undefined` (a key the
 * form never touched) is dropped; `null` and `""` are sent as-is. */
function cleanUpdatePayload<T extends Record<string, unknown>>(input: T): Partial<T> {
  const out: Partial<T> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value === undefined) continue;
    // An empty string is "clear this field" for a text field, but the
    // backend's typed fields (birthdate: date, company_id: uuid) reject ""
    // outright - Pydantic can't parse it as a date/uuid at all, which used
    // to 422 the *entire* PATCH (every other field in the same request
    // included) the moment a date field was touched while empty. null is
    // what every field type actually accepts as "no value" - and reads the
    // same as "" everywhere a field is displayed (see field-change-
    // history.tsx: `new_value || "(cleared)"` treats both identically).
    out[key as keyof T] = (value === "" ? null : value) as T[keyof T];
  }
  return out;
}

export async function createContact(input: ContactFormInput) {
  const contact = await backendFetch<ContactDetail>("/api/contacts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanPayload(input)),
  });
  revalidatePath("/contacts");
  if (input.company_id) revalidatePath(`/companies/${input.company_id}`);
  return contact;
}

export async function updateContact(id: string, input: ContactFormInput) {
  const contact = await backendFetch<ContactDetail>(`/api/contacts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanUpdatePayload(input)),
  });
  revalidatePath("/contacts");
  revalidatePath(`/contacts/${id}`);
  // company_id may have changed (linking this contact to a company, or
  // re-assigning it) - that company's page shows a contacts list that
  // needs to reflect the change.
  if (input.company_id) revalidatePath(`/companies/${input.company_id}`);
  return contact;
}

export async function deleteContact(id: string) {
  await backendFetch<void>(`/api/contacts/${id}`, { method: "DELETE" });
  revalidatePath("/contacts");
}

/** Moves every note/history entry from one contact to another - "when a
 * contact leaves a particular company, we can easily move notes in ACT
 * from that person to a new person" (BMI's own Act pain-points doc). See
 * backend/app/services/contact_transfer.py for what actually moves. */
export async function reassignContact(contactId: string, successorId: string) {
  await backendFetch<void>(`/api/contacts/${contactId}/reassign/${successorId}`, { method: "POST" });
  revalidatePath(`/contacts/${contactId}`);
  revalidatePath(`/contacts/${successorId}`);
}

/** Who changed what on this record, newest first - "the ability to
 * identify which BMI user has made changes to specific data" (BMI's Act
 * pain-points doc). Fetched on demand from the expandable history panel
 * rather than bundled into ContactDetail/CompanyDetail, so a page that
 * never opens it never pays for it. */
export async function getContactFieldChanges(contactId: string): Promise<FieldChange[]> {
  return backendFetch<FieldChange[]>(`/api/contacts/${contactId}/field-changes`);
}

export async function getCompanyFieldChanges(companyId: string): Promise<FieldChange[]> {
  return backendFetch<FieldChange[]>(`/api/companies/${companyId}/field-changes`);
}

export async function addContactToGroup(contactId: string, groupId: string) {
  await backendFetch<void>(`/api/contacts/${contactId}/groups/${groupId}`, { method: "POST" });
  revalidatePath(`/contacts/${contactId}`);
  revalidatePath(`/groups/${groupId}`);
}

export async function removeContactFromGroup(contactId: string, groupId: string) {
  await backendFetch<void>(`/api/contacts/${contactId}/groups/${groupId}`, { method: "DELETE" });
  revalidatePath(`/contacts/${contactId}`);
  revalidatePath(`/groups/${groupId}`);
}

/** Bulk version of removeContactFromGroup - one request for the whole
 * selection instead of one per contact, so a large mailing-prep cleanup
 * doesn't mean N round trips (and N chances for the list to jump back to
 * the top - see group-members-table.tsx, which removes the selected rows
 * from its own local state rather than re-fetching after this call). */
export async function removeGroupMembers(groupId: string, contactIds: string[]) {
  await backendFetch<void>(`/api/groups/${groupId}/members/remove`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contact_ids: contactIds }),
  });
  revalidatePath(`/groups/${groupId}`);
}

export async function addContactNote(
  contactId: string,
  body: string,
  note_type: string = "Note",
  is_private: boolean = false
) {
  const session = await getSession();
  await backendFetch(`/api/contacts/${contactId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body, note_type, is_private, created_by_user_id: currentUserId(session?.sub) }),
  });
  revalidatePath(`/contacts/${contactId}`);
}

export async function deleteContactNote(contactId: string, noteId: string) {
  await backendFetch(`/api/contacts/${contactId}/notes/${noteId}`, { method: "DELETE" });
  revalidatePath(`/contacts/${contactId}`);
}

export type LogHistoryInput = {
  history_type: string;
  subject?: string;
  details?: string;
  duration_minutes?: number;
  is_private?: boolean;
  occurred_at: string;
};

export async function logContactHistory(contactId: string, input: LogHistoryInput) {
  const session = await getSession();
  const entry = await backendFetch<HistoryOut>(`/api/contacts/${contactId}/history`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, created_by_user_id: currentUserId(session?.sub) }),
  });
  revalidatePath(`/contacts/${contactId}`);
  return entry;
}

export async function logCompanyHistory(companyId: string, input: LogHistoryInput) {
  const session = await getSession();
  const entry = await backendFetch<HistoryOut>(`/api/companies/${companyId}/history`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, created_by_user_id: currentUserId(session?.sub) }),
  });
  revalidatePath(`/companies/${companyId}`);
  return entry;
}

export async function deleteContactHistory(contactId: string, historyId: string) {
  await backendFetch(`/api/contacts/${contactId}/history/${historyId}`, { method: "DELETE" });
  revalidatePath(`/contacts/${contactId}`);
}

export async function deleteCompanyHistory(companyId: string, historyId: string) {
  await backendFetch(`/api/companies/${companyId}/history/${historyId}`, { method: "DELETE" });
  revalidatePath(`/companies/${companyId}`);
}

export type ScheduleActivityInput = {
  activity_type: string;
  subject?: string;
  details?: string;
  location?: string;
  start_at: string;
  end_at?: string;
  is_timeless?: boolean;
  is_private?: boolean;
  recurrence?: ActivityRecurrence;
  contact_id?: string | null;
  company_id?: string | null;
  source_db: string;
};

export async function createActivity(input: ScheduleActivityInput) {
  const session = await getSession();
  const activity = await backendFetch<ActivityOut>("/api/activities", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, created_by_user_id: currentUserId(session?.sub) }),
  });
  if (input.contact_id) revalidatePath(`/contacts/${input.contact_id}`);
  if (input.company_id) revalidatePath(`/companies/${input.company_id}`);
  revalidatePath("/activities");
  return activity;
}

export async function setActivityDone(id: string, is_cleared: boolean, revalidate?: { contactId?: string; companyId?: string }) {
  await backendFetch<ActivityOut>(`/api/activities/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_cleared }),
  });
  if (revalidate?.contactId) revalidatePath(`/contacts/${revalidate.contactId}`);
  if (revalidate?.companyId) revalidatePath(`/companies/${revalidate.companyId}`);
  revalidatePath("/activities");
}

export async function deleteActivity(id: string, revalidate?: { contactId?: string; companyId?: string }) {
  await backendFetch<void>(`/api/activities/${id}`, { method: "DELETE" });
  if (revalidate?.contactId) revalidatePath(`/contacts/${revalidate.contactId}`);
  if (revalidate?.companyId) revalidatePath(`/companies/${revalidate.companyId}`);
  revalidatePath("/activities");
}

export async function listActivities(params: {
  source_db?: string;
  assigned_user_id?: string;
  is_cleared?: boolean;
  priority?: string;
  activity_type?: string;
  q?: string;
  start_after?: string;
  start_before?: string;
  page?: number;
  page_size?: number;
}): Promise<ActivitiesPage> {
  const q = new URLSearchParams();
  if (params.source_db) q.set("source_db", params.source_db);
  if (params.assigned_user_id) q.set("assigned_user_id", params.assigned_user_id);
  if (params.is_cleared !== undefined) q.set("is_cleared", String(params.is_cleared));
  if (params.priority) q.set("priority", params.priority);
  if (params.activity_type) q.set("activity_type", params.activity_type);
  if (params.q) q.set("q", params.q);
  if (params.start_after) q.set("start_after", params.start_after);
  if (params.start_before) q.set("start_before", params.start_before);
  q.set("page", String(params.page ?? 1));
  q.set("page_size", String(params.page_size ?? 100));
  return backendFetch<ActivitiesPage>(`/api/activities?${q}`);
}

// ---- Contact channels (email/phone/address) --------------------------------
// One shared shape per channel type - a plain object matching the backend's
// *Write schema (type_label + the one value field). "" for id means create;
// a real id means update; ChannelActions.remove(id) deletes.

export type EmailInput = { type_label?: string; address?: string };
export type PhoneInput = { type_label?: string; number?: string };
export type AddressInput = {
  type_label?: string;
  line1?: string;
  line2?: string;
  line3?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
};

function channelPath(entity: "contacts" | "companies", channel: "emails" | "phones" | "addresses", entityId: string, channelId?: string) {
  return `/api/${entity}/${entityId}/${channel}${channelId ? `/${channelId}` : ""}`;
}

async function saveChannel<T extends Record<string, unknown>>(
  entity: "contacts" | "companies",
  channel: "emails" | "phones" | "addresses",
  entityId: string,
  channelId: string | undefined,
  input: T
) {
  await backendFetch(channelPath(entity, channel, entityId, channelId), {
    method: channelId ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidatePath(`/${entity}/${entityId}`);
}

async function removeChannel(
  entity: "contacts" | "companies",
  channel: "emails" | "phones" | "addresses",
  entityId: string,
  channelId: string
) {
  await backendFetch(channelPath(entity, channel, entityId, channelId), { method: "DELETE" });
  revalidatePath(`/${entity}/${entityId}`);
}

// Next's "use server" file convention only recognizes top-level `async
// function` declarations as callable server actions - a `const foo = (...)
// => ...` export (even one that just forwards to an async helper, as these
// did originally) silently fails to register, so every one of these needs
// to be its own async function statement rather than a thin arrow wrapper.

export async function saveContactEmail(contactId: string, channelId: string | undefined, input: EmailInput) {
  return saveChannel("contacts", "emails", contactId, channelId, input);
}
export async function removeContactEmail(contactId: string, channelId: string) {
  return removeChannel("contacts", "emails", contactId, channelId);
}

export async function saveContactPhone(contactId: string, channelId: string | undefined, input: PhoneInput) {
  return saveChannel("contacts", "phones", contactId, channelId, input);
}
export async function removeContactPhone(contactId: string, channelId: string) {
  return removeChannel("contacts", "phones", contactId, channelId);
}

export async function saveContactAddress(contactId: string, channelId: string | undefined, input: AddressInput) {
  return saveChannel("contacts", "addresses", contactId, channelId, input);
}
export async function removeContactAddress(contactId: string, channelId: string) {
  return removeChannel("contacts", "addresses", contactId, channelId);
}

export async function saveCompanyEmail(companyId: string, channelId: string | undefined, input: EmailInput) {
  return saveChannel("companies", "emails", companyId, channelId, input);
}
export async function removeCompanyEmail(companyId: string, channelId: string) {
  return removeChannel("companies", "emails", companyId, channelId);
}

export async function saveCompanyPhone(companyId: string, channelId: string | undefined, input: PhoneInput) {
  return saveChannel("companies", "phones", companyId, channelId, input);
}
export async function removeCompanyPhone(companyId: string, channelId: string) {
  return removeChannel("companies", "phones", companyId, channelId);
}

export async function saveCompanyAddress(companyId: string, channelId: string | undefined, input: AddressInput) {
  return saveChannel("companies", "addresses", companyId, channelId, input);
}
export async function removeCompanyAddress(companyId: string, channelId: string) {
  return removeChannel("companies", "addresses", companyId, channelId);
}

// ---- Companies --------------------------------------------------------------

export type CompanyFormInput = {
  name: string;
  description?: string;
  industry?: string;
  category?: string;
  territory?: string;
  region?: string;
  website?: string;
  num_employees?: number;
  source_db?: string;
};

export async function createCompany(input: CompanyFormInput) {
  const company = await backendFetch<{ id: string }>("/api/companies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanPayload(input)),
  });
  revalidatePath("/companies");
  return company;
}

export async function updateCompany(id: string, input: Partial<CompanyFormInput>) {
  await backendFetch<void>(`/api/companies/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanUpdatePayload(input)),
  });
  revalidatePath("/companies");
  revalidatePath(`/companies/${id}`);
}

export async function deleteCompany(id: string) {
  await backendFetch<void>(`/api/companies/${id}`, { method: "DELETE" });
  revalidatePath("/companies");
}

export async function addCompanyNote(companyId: string, body: string, is_private: boolean = false) {
  const session = await getSession();
  await backendFetch(`/api/companies/${companyId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body, is_private, created_by_user_id: currentUserId(session?.sub) }),
  });
  revalidatePath(`/companies/${companyId}`);
}

export async function deleteCompanyNote(companyId: string, noteId: string) {
  await backendFetch(`/api/companies/${companyId}/notes/${noteId}`, { method: "DELETE" });
  revalidatePath(`/companies/${companyId}`);
}

// ---- Groups --------------------------------------------------------------

export type GroupFormInput = {
  name: string;
  description?: string;
  source_db?: string;
  parent_group_id?: string | null;
};

export async function createGroup(input: GroupFormInput) {
  const group = await backendFetch<{ id: string }>("/api/groups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanPayload(input)),
  });
  revalidatePath("/groups");
  return group;
}

export async function updateGroup(id: string, input: Partial<GroupFormInput>) {
  await backendFetch<void>(`/api/groups/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanUpdatePayload(input)),
  });
  revalidatePath("/groups");
  revalidatePath(`/groups/${id}`);
}

export async function deleteGroup(id: string) {
  await backendFetch<void>(`/api/groups/${id}`, { method: "DELETE" });
  revalidatePath("/groups");
}

// ---- Search (for the company/group pickers in the forms) --------------------

export async function searchCompanies(q: string): Promise<CompanyListItem[]> {
  if (!q.trim()) return [];
  const page = await backendFetch<Page<CompanyListItem>>(
    `/api/companies?${new URLSearchParams({ q, page_size: "10" })}`
  );
  return page.items;
}

export async function searchGroups(q: string): Promise<GroupListItem[]> {
  const page = await backendFetch<Page<GroupListItem>>(
    `/api/groups?${new URLSearchParams({ q, page_size: "10" })}`
  );
  return page.items;
}

/** Every group in one database, for the Team access picker's "restrict to
 * this group" dropdown - unlike searchGroups, scoped to a single
 * source_db and returns everything (up to 500) rather than a text-search
 * top-10, since an admin picking an access grant needs to see the whole
 * tree, not guess a search term. */
export async function listGroupsForDatabase(source_db: string): Promise<GroupListItem[]> {
  const page = await backendFetch<Page<GroupListItem>>(
    `/api/groups?${new URLSearchParams({ source_db, page_size: "500" })}`
  );
  return page.items;
}

export async function searchContacts(q: string): Promise<ContactListItem[]> {
  if (!q.trim()) return [];
  const page = await backendFetch<Page<ContactListItem>>(
    `/api/contacts?${new URLSearchParams({ q, page_size: "10" })}`
  );
  return page.items;
}

// ---- Automations / review queue --------------------------------------------

/** Resolves one review-queue item by the specific action a reviewer picked
 * (see backend/app/automations/registry.py) - not a generic approve/reject,
 * since each automation's actions carry their own meaning and wording.
 * Throws with the backend's own message on failure (missing required
 * input, already resolved by someone else, stale data) - the caller shows
 * that text directly rather than a generic "something went wrong". */
export async function resolveReviewItem(
  itemId: string,
  actionId: string,
  input: { note?: string; contact_id?: string; fields?: Record<string, string>; chosen_entity_id?: string }
) {
  const resolved = await backendFetch<ReviewQueueItem>(`/api/review-queue/${itemId}/actions/${actionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidatePath("/automations");
  revalidatePath("/automations/review");
  revalidatePath("/automations/today");
  // Every other write in this file revalidates the exact contact/company
  // page it touched - this one didn't, so a note/field-update from here
  // (e.g. SALES-012's "Draft follow-up") could sit behind a stale cached
  // page if that contact was already open in the same tab.
  if (resolved.entity_type === "contact" && resolved.entity_id) revalidatePath(`/contacts/${resolved.entity_id}`);
  if (resolved.entity_type === "company" && resolved.entity_id) revalidatePath(`/companies/${resolved.entity_id}`);
  // requires_related_entity_choice actions (e.g. CS-004's merge) act on a
  // record named in related_entities, not entity_id - revalidate those too.
  for (const related of resolved.payload?.related_entities ?? []) {
    revalidatePath(`/${related.type === "contact" ? "contacts" : "companies"}/${related.id}`);
  }
}

/** Regenerates an AI-drafted follow-up with extra reviewer instructions -
 * see backend's POST /api/review-queue/{id}/redraft. Deliberately does
 * NOT resolve the item (no revalidate of the review queue itself needed
 * for that reason) - it's a preview step the reviewer can call as many
 * times as they like before actually approving via resolveReviewItem. */
export async function redraftReviewItem(itemId: string, instructions: string): Promise<string> {
  const result = await backendFetch<{ draft: string }>(`/api/review-queue/${itemId}/redraft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instructions }),
  });
  return result.draft;
}

/** Applies one action to every currently-pending item of one kind - see
 * backend's POST /api/review-queue/bulk-actions/{action_id}. Always scoped
 * to a single kind (bulk actions can't span kinds, since actions are
 * defined per kind) and rejected up front by the backend for any action
 * that needs per-item input it can't collect in bulk (a contact picker, a
 * required extra field). Throws with the backend's own message on that
 * rejection; on success, returns the counts so the caller can report
 * "412 dismissed" / "3 failed" rather than a bare success toast. */
export async function bulkResolveReviewItems(
  kind: string,
  actionId: string,
  note?: string
): Promise<{ matched: number; succeeded: number; failed: number; errors: string[] }> {
  const result = await backendFetch<{ matched: number; succeeded: number; failed: number; errors: string[] }>(
    `/api/review-queue/bulk-actions/${actionId}?${new URLSearchParams({ kind })}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    }
  );
  revalidatePath("/automations");
  revalidatePath("/automations/review");
  revalidatePath("/automations/today");
  return result;
}

/** Puts a rejected review item back to pending - see backend's
 * POST /api/review-queue/{id}/reopen for why this only works on a
 * rejected item, never an approved one. */
export async function reopenReviewItem(itemId: string) {
  await backendFetch(`/api/review-queue/${itemId}/reopen`, { method: "POST" });
  revalidatePath("/automations");
  revalidatePath("/automations/review");
}

/** Sets (or replaces) a runtime override for an automation tunable - see
 * backend's PUT /api/automations/settings/{key}. Takes effect on that
 * setting's next read (a scan's next tick, or the next "Run now" click),
 * never a restart. */
export async function updateAutomationSetting(key: string, value: boolean | number | string) {
  await backendFetch(`/api/automations/settings/${key}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
  revalidatePath("/automations/settings");
  revalidatePath("/automations");
}

/** Clears a stored override, reverting a setting to its env var default. */
export async function resetAutomationSetting(key: string) {
  await backendFetch(`/api/automations/settings/${key}`, { method: "DELETE" });
  revalidatePath("/automations/settings");
  revalidatePath("/automations");
}

/** SALES-002's one-confirm batch write - resolves every still-pending
 * business-card review item from one upload's batch_id with its sensible
 * default action (see backend's business_card.resolve_batch). Returns the
 * added/updated/logged/failed counts so the caller can show them. */
export async function confirmBusinessCardBatch(batchId: string): Promise<{
  added: number; updated: number; logged: number; failed: number;
}> {
  const result = await backendFetch<{ added: number; updated: number; logged: number; failed: number }>(
    `/api/automations/business-cards/batches/${batchId}/confirm`, { method: "POST" }
  );
  revalidatePath("/automations/review");
  return result;
}

// ---- Settings / preferences -------------------------------------------

/** Updates one or more of the current user's preferences (see
 * backend/app/preferences.py for the registry of what's settable).
 * Revalidates "/" too since the dashboard is the one place a preference
 * (recent_activity_sort, today) actually changes what's shown. */
export async function updateUserPreferences(userId: string, values: Record<string, string>) {
  await backendFetch(`/api/users/${userId}/preferences`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values }),
  });
  revalidatePath("/settings");
  revalidatePath("/");
}

// ---- Publications ("add a new database") -------------------------------
// See backend/app/models/publication.py - a Publication is a label
// (source_db value), never an actual new Postgres database.

export async function listPublications(): Promise<Publication[]> {
  try {
    return await backendFetch<Publication[]>("/api/publications");
  } catch {
    return [
      {
        id: "pub_1",
        name: "Onboard Hospitality",
        slug: "onboard",
        description: "Inflight catering & onboard services",
        color: "blue",
        icon: "plane",
      },
      {
        id: "pub_2",
        name: "Selling Travel",
        slug: "sellingtravel",
        description: "Travel trade & agent distribution",
        color: "emerald",
        icon: "compass",
      },
      {
        id: "pub_3",
        name: "Prospects",
        slug: "prospects",
        description: "Global leads & brand directory",
        color: "amber",
        icon: "globe",
      },
    ];
  }
}

export type PublicationFormInput = {
  name: string;
  slug?: string;
  description?: string;
  color: string;
  icon: string;
};

export async function createPublication(input: PublicationFormInput) {
  const publication = await backendFetch<Publication>("/api/publications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanPayload(input)),
  });
  // Every page that shows the publication list/switcher/tiles needs this -
  // simplest correct thing is to revalidate everywhere it can appear
  // rather than track each one individually.
  revalidatePath("/", "layout");
  return publication;
}

// ---- Team / role-based access -------------------------------------------
// See backend/app/roles.py (what a role grants) and
// backend/app/models/user_access.py (per-user database/group scoping).
// All of these hit admin-only-in-spirit backend routes - the actual
// enforcement is that /settings/users itself is gated to role === "admin"
// (see lib/access.ts's canManageUsers), same trust boundary as every
// other restriction in this app: the backend fully trusts whoever holds
// the shared API key, which only this Next.js server ever does.

export async function listRoles(): Promise<RoleDef[]> {
  return backendFetch<RoleDef[]>("/api/roles");
}

export async function listTeamUsers(): Promise<UserAccount[]> {
  return backendFetch<UserAccount[]>("/api/users");
}

export type TeamUserFormInput = {
  email: string;
  name: string;
  password?: string;
  role: string;
  access: UserAccessEntry[];
};

export async function createTeamUser(input: TeamUserFormInput) {
  const user = await backendFetch<UserAccount>("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: input.email,
      name: input.name,
      password: input.password,
      role: input.role,
      access: input.access.map((a) => ({ source_db: a.source_db, group_id: a.group_id })),
    }),
  });
  revalidatePath("/settings/users");
  return user;
}

export async function updateTeamUser(
  id: string,
  input: Partial<Omit<TeamUserFormInput, "email">> & { is_active?: boolean }
) {
  const body: Record<string, unknown> = {};
  if (input.name !== undefined) body.name = input.name;
  if (input.role !== undefined) body.role = input.role;
  if (input.is_active !== undefined) body.is_active = input.is_active;
  if (input.password) body.password = input.password;
  if (input.access !== undefined) {
    body.access = input.access.map((a) => ({ source_db: a.source_db, group_id: a.group_id }));
  }
  const user = await backendFetch<UserAccount>(`/api/users/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  revalidatePath("/settings/users");
  return user;
}
