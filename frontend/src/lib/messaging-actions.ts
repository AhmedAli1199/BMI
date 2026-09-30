"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type {
  AppNotification,
  MailMergeSummary,
  MailStatus,
  MailTemplate,
  MergeField,
  MergeRequest,
  RecipientSource,
  RecipientsResult,
  Reminder,
} from "@/lib/messaging-types";
import type { ContactDetail } from "@/lib/types";

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// ---- Reminders ----------------------------------------------------------

export async function listReminders(params: { status?: string; contact_id?: string; company_id?: string } = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
  return backendFetch<Reminder[]>(`/api/reminders?${qs}`);
}

export async function createReminder(input: {
  due_at: string;
  note?: string;
  contact_id?: string | null;
  company_id?: string | null;
  email_me: boolean;
}) {
  const r = await backendFetch<Reminder>("/api/reminders", json(input));
  revalidatePath("/reminders");
  return r;
}

export async function updateReminder(
  id: string,
  patch: { due_at?: string; note?: string | null; email_me?: boolean; status?: "open" | "done" | "cancelled" }
) {
  const r = await backendFetch<Reminder>(`/api/reminders/${id}`, { ...json(patch), method: "PATCH" });
  revalidatePath("/reminders");
  return r;
}

export async function deleteReminder(id: string) {
  await backendFetch(`/api/reminders/${id}`, { method: "DELETE" });
  revalidatePath("/reminders");
}

// ---- Notifications ------------------------------------------------------

export async function listNotifications(limit = 30) {
  return backendFetch<{ items: AppNotification[]; unread: number }>(`/api/notifications?limit=${limit}`);
}

export async function markNotificationRead(id: string) {
  await backendFetch(`/api/notifications/${id}/read`, { method: "POST" });
}

export async function markAllNotificationsRead() {
  await backendFetch("/api/notifications/read-all", { method: "POST" });
}

// ---- Outlook / templates ------------------------------------------------

export async function getMailStatus() {
  return backendFetch<MailStatus>("/api/mail/status");
}

export async function disconnectOutlook() {
  await backendFetch("/api/mail/outlook", { method: "DELETE" });
  revalidatePath("/settings");
}

export async function listMergeFields() {
  return backendFetch<MergeField[]>("/api/mail/fields");
}

export async function listTemplates() {
  return backendFetch<MailTemplate[]>("/api/mail/templates");
}

export async function saveTemplate(
  input: { name: string; subject?: string | null; body: string; shared: boolean },
  id?: string
) {
  return id
    ? backendFetch<MailTemplate>(`/api/mail/templates/${id}`, { ...json(input), method: "PUT" })
    : backendFetch<MailTemplate>("/api/mail/templates", json(input));
}

export async function deleteTemplate(id: string) {
  await backendFetch(`/api/mail/templates/${id}`, { method: "DELETE" });
}

// ---- Mail merge ---------------------------------------------------------

export async function previewRecipients(source: RecipientSource) {
  return backendFetch<RecipientsResult>("/api/mail-merge/recipients", json(source));
}

export async function previewMerge(input: { contact_id?: string | null; subject?: string; body: string }) {
  return backendFetch<{ subject: string; body: string; html: string; unknown_fields: string[] }>(
    "/api/mail-merge/preview",
    json(input)
  );
}

/** Email output only (documents download through /api/files). */
export async function startEmailMerge(input: MergeRequest) {
  const res = await backendFetch<MailMergeSummary | { test_sent_to: string; rendered_for: string }>(
    "/api/mail-merge",
    json({ ...input, output: "email" })
  );
  revalidatePath("/mail-merge");
  return res;
}

export async function cancelMerge(id: string) {
  const m = await backendFetch<MailMergeSummary>(`/api/mail-merge/${id}/cancel`, { method: "POST" });
  revalidatePath(`/mail-merge/${id}`);
  return m;
}

export async function resumeMerge(id: string) {
  const m = await backendFetch<MailMergeSummary>(`/api/mail-merge/${id}/resume`, { method: "POST" });
  revalidatePath(`/mail-merge/${id}`);
  return m;
}

export async function deleteAttachment(id: string) {
  await backendFetch(`/api/mail-merge/attachments/${id}`, { method: "DELETE" });
}

// ---- Contacts & groups --------------------------------------------------

export async function duplicateContact(
  id: string,
  input: { first_name?: string; last_name?: string; email?: string; job_title?: string; phone?: string; copy_groups: boolean }
) {
  const c = await backendFetch<ContactDetail>(`/api/contacts/${id}/duplicate`, json(input));
  revalidatePath("/contacts");
  return c;
}

export async function lookupContactIds(params: Record<string, string>) {
  return backendFetch<string[]>(`/api/contacts/lookup-ids?${new URLSearchParams(params)}`);
}

export async function addContactsToGroup(groupId: string, contactIds: string[]) {
  const r = await backendFetch<{ added: number; already_members: number }>(
    `/api/groups/${groupId}/members/add`,
    json({ contact_ids: contactIds })
  );
  revalidatePath(`/groups/${groupId}`);
  revalidatePath("/groups");
  return r;
}

export async function createGroupWithMembers(input: {
  name: string;
  description?: string;
  source_db?: string;
  contact_ids: string[];
}) {
  const g = await backendFetch<{ id: string; name: string }>("/api/groups", json(input));
  revalidatePath("/groups");
  return g;
}
