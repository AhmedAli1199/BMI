import { backendFetch } from "@/lib/backend";
import type { MailTemplate, MergeField } from "@/lib/messaging-types";
import type { SalesMeta } from "@/lib/sales-types";

export async function loadEditorData() {
  const [templates, fields, meta] = await Promise.all([
    backendFetch<MailTemplate[]>("/api/mail/templates").catch(() => [] as MailTemplate[]),
    backendFetch<MergeField[]>("/api/mail/fields").catch(() => [] as MergeField[]),
    backendFetch<SalesMeta>("/api/sales/meta").catch(() => null),
  ]);
  return { templates, fields, titles: meta?.titles ?? [] };
}
