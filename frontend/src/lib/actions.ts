"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { CompanyListItem, ContactDetail, ContactListItem, GroupListItem, Page } from "@/lib/types";

/** Every CRUD mutation for Contacts/Companies/Groups, callable straight from
 * client components (Next.js server actions run on the server regardless of
 * where they're invoked from - this is how forms/buttons reach the FastAPI
 * backend without ever exposing BACKEND_API_KEY to the browser).
 */

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
