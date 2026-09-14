"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import { PUBLICATION_COOKIE } from "@/lib/publication";
import type { CompanyListItem, ContactDetail, ContactListItem, GroupListItem, Page } from "@/lib/types";

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
};

function cleanPayload<T extends Record<string, unknown>>(input: T): Partial<T> {
  const out: Partial<T> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value !== "" && value !== undefined) out[key as keyof T] = value as T[keyof T];
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
    body: JSON.stringify(cleanPayload(input)),
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

export async function addContactNote(contactId: string, body: string, note_type: string = "Note") {
  await backendFetch(`/api/contacts/${contactId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body, note_type }),
  });
  revalidatePath(`/contacts/${contactId}`);
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
    body: JSON.stringify(cleanPayload(input)),
  });
  revalidatePath("/companies");
  revalidatePath(`/companies/${id}`);
}

export async function deleteCompany(id: string) {
  await backendFetch<void>(`/api/companies/${id}`, { method: "DELETE" });
  revalidatePath("/companies");
}

export async function addCompanyNote(companyId: string, body: string) {
  await backendFetch(`/api/companies/${companyId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  revalidatePath(`/companies/${companyId}`);
}

// ---- Groups --------------------------------------------------------------

export type GroupFormInput = {
  name: string;
  description?: string;
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
    body: JSON.stringify(cleanPayload(input)),
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
  input: { note?: string; contact_id?: string; fields?: Record<string, string> }
) {
  await backendFetch(`/api/review-queue/${itemId}/actions/${actionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidatePath("/automations");
  revalidatePath("/automations/review");
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
