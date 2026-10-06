"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type {
  BulkAction, BulkEdit, BulkPreview, ContactField, ContactImport, ContactScope, EmailsResult, ImportColumn, ImportListItem,
  ImportOptions, ImportReview, ImportTarget,
} from "@/lib/contact-tools-types";

const json = (body: unknown, method = "POST") => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---- search / tools ----
export async function getContactFields(): Promise<ContactField[]> {
  return backendFetch<ContactField[]>("/api/contacts/fields");
}

export async function getEmailAddresses(scope: ContactScope): Promise<EmailsResult> {
  return backendFetch<EmailsResult>("/api/contacts/emails", json(scope));
}

export async function previewBulkUpdate(input: { scope: ContactScope; field: string; op: BulkAction; value?: string; find?: string }): Promise<BulkPreview> {
  return backendFetch<BulkPreview>("/api/contacts/bulk-update/preview", json(input));
}

export async function applyBulkUpdate(input: { scope: ContactScope; field: string; op: BulkAction; value?: string; find?: string }): Promise<BulkEdit> {
  const r = await backendFetch<BulkEdit>("/api/contacts/bulk-update", json(input));
  revalidatePath("/contacts");
  return r;
}

export async function getBulkHistory(): Promise<BulkEdit[]> {
  return backendFetch<BulkEdit[]>("/api/contacts/bulk-update/history");
}

export async function undoBulkUpdate(id: string): Promise<{ restored: number; skipped: number }> {
  const r = await backendFetch<{ restored: number; skipped: number }>(`/api/contacts/bulk-update/${id}/undo`, { method: "POST" });
  revalidatePath("/contacts");
  return r;
}

// ---- import ----
export async function getImportTargets(): Promise<ImportTarget[]> {
  return backendFetch<ImportTarget[]>("/api/contact-imports/targets");
}

export async function getImport(id: string): Promise<ContactImport> {
  return backendFetch<ContactImport>(`/api/contact-imports/${id}`);
}

export async function listImports(): Promise<ImportListItem[]> {
  return backendFetch<ImportListItem[]>("/api/contact-imports");
}

export async function patchImport(
  id: string,
  patch: {
    sheet?: string;
    header_row?: number;
    has_header?: boolean;
    mapping?: Record<string, { field: string; name?: string | null; type?: string | null }>;
    options?: Partial<ImportOptions>;
    excluded?: number[];
  }
): Promise<ContactImport> {
  return backendFetch<ContactImport>(`/api/contact-imports/${id}`, json(patch, "PATCH"));
}

export async function autoMapImport(id: string): Promise<ContactImport> {
  return backendFetch<ContactImport>(`/api/contact-imports/${id}/automap`, { method: "POST" });
}

export async function reviewImport(id: string, input: { status?: string | null; q?: string; page?: number; page_size?: number }): Promise<ImportReview> {
  return backendFetch<ImportReview>(`/api/contact-imports/${id}/review`, json(input));
}

export async function commitImport(id: string): Promise<ContactImport> {
  const r = await backendFetch<ContactImport>(`/api/contact-imports/${id}/commit`, { method: "POST" });
  revalidatePath("/contacts");
  revalidatePath("/companies");
  revalidatePath("/groups");
  return r;
}

export async function undoImport(id: string): Promise<{ deleted: number; kept: number; reverted: number }> {
  const r = await backendFetch<{ deleted: number; kept: number; reverted: number }>(`/api/contact-imports/${id}/undo`, { method: "POST" });
  revalidatePath("/contacts");
  revalidatePath("/companies");
  revalidatePath("/groups");
  return r;
}

export async function discardImport(id: string): Promise<void> {
  await backendFetch(`/api/contact-imports/${id}`, { method: "DELETE" });
}

export type { ImportColumn };
