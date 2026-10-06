import Link from "next/link";
import { ArrowLeft, FileSpreadsheet, Upload } from "lucide-react";
import { listImports } from "@/lib/contact-tools-actions";
import { ImportUpload } from "@/components/contacts/import/import-upload";

export default async function ImportContactsPage() {
  const recent = await listImports().catch(() => []);
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6">
      <div className="border-b border-border/80 pb-4">
        <Link href="/contacts" className="mb-1 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-3.5" /> Contacts
        </Link>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Upload className="size-3.5" /> Import
        </div>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Import contacts</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Add people from an Excel sheet, a CSV file or a PDF. We match the columns for you, check for people who are already in the CRM, and show you everything before it&apos;s saved.
        </p>
      </div>

      <ImportUpload />

      {recent.length > 0 && (
        <section aria-labelledby="recent-h" className="rounded-xl border border-border/80 bg-card shadow-2xs">
          <h2 id="recent-h" className="border-b border-border/70 px-4 py-3 text-sm font-bold">Recent imports</h2>
          <ul className="divide-y divide-border/60">
            {recent.map((r) => (
              <li key={r.id}>
                <Link href={`/contacts/import/${r.id}`} className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted/40">
                  <FileSpreadsheet className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate font-medium">{r.filename}</span>
                  <span className="hidden text-xs text-muted-foreground sm:inline">
                    {r.status === "imported" ? `${r.created ?? 0} added${r.updated ? `, ${r.updated} updated` : ""}` : r.status === "undone" ? "Undone" : `${r.row_count} rows`}
                  </span>
                  <span className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}{r.by ? ` · ${r.by}` : ""}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
