import { notFound } from "next/navigation";
import { TemplateEditor } from "@/components/mail-merge/template-editor";
import { loadEditorData } from "../_load";

/** Change one email template, on a page of its own. */
export default async function EditTemplatePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { templates, fields, titles } = await loadEditorData();
  const t = templates.find((x) => x.id === id);
  if (!t || !t.can_edit) notFound();
  return (
    <TemplateEditor
      draft={{ id: t.id, name: t.name, subject: t.subject ?? "", body: t.body, shared: t.shared, brand: t.brand ?? "", title_id: t.title_id ?? "",
        kind: t.kind ?? "general", description: t.description ?? "", needs_check: !!t.needs_check }}
      fields={fields}
      titles={titles}
    />
  );
}
