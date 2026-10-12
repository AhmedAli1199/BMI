import { TemplateEditor } from "@/components/mail-merge/template-editor";
import { loadEditorData } from "../_load";

/** Write a new email template, or start from a copy of one (?copy=<id>). */
export default async function NewTemplatePage({ searchParams }: { searchParams: Promise<{ copy?: string }> }) {
  const { copy } = await searchParams;
  const { templates, fields, titles } = await loadEditorData();
  const t = copy ? templates.find((x) => x.id === copy) : undefined;
  const draft = t
    ? { name: `${t.name} (my copy)`, subject: t.subject ?? "", body: t.body, shared: false, brand: t.brand ?? "", title_id: t.title_id ?? "", kind: t.kind ?? "general", description: "" }
    : { name: "", subject: "", body: "Hi {{salutation|there}},\n\n\n\nKind regards\n{{my_name}}", shared: true, brand: "", title_id: "", kind: "pitch" as const, description: "" };
  return <TemplateEditor draft={draft} fields={fields} titles={titles} />;
}
