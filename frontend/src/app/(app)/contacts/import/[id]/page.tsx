import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { allowedSourceDbSlugs } from "@/lib/access";
import { listPublications } from "@/lib/actions";
import type { ContactImport, ImportTarget } from "@/lib/contact-tools-types";
import { ImportWizard } from "@/components/contacts/import/import-wizard";

export default async function ImportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [imp, targets, session, all] = await Promise.all([
    backendFetch<ContactImport>(`/api/contact-imports/${id}`).catch(() => null),
    backendFetch<ImportTarget[]>("/api/contact-imports/targets").catch(() => [] as ImportTarget[]),
    getSession(),
    listPublications(),
  ]);
  if (!imp) notFound();
  const publications = session?.role === "admin" ? all : all.filter((p) => allowedSourceDbSlugs(session).includes(p.slug));
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      <ImportWizard initial={imp} targets={targets} publications={publications.map((p) => ({ slug: p.slug, name: p.name }))} />
    </div>
  );
}
