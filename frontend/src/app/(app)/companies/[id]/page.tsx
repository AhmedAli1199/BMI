import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, Layers, Users } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { CompanyDetail } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EntityAvatar } from "@/components/entity-avatar";
import { AddNoteDialog } from "@/components/add-note-dialog";
import { addCompanyNote } from "@/lib/actions";
import { cleanNoteBody } from "@/lib/notes";
import { sourceLabel } from "@/lib/sources";
import { CompanyDossier } from "@/components/company-dossier";
import { ContactFormDialog } from "@/components/contact-form-dialog";
import { AddExistingContactPicker } from "@/components/add-existing-contact-picker";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let company: CompanyDetail;
  try {
    company = await backendFetch<CompanyDetail>(`/api/companies/${id}`);
  } catch {
    notFound();
  }

  const customEntries = Object.entries(company.custom_fields || {});

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      {/* Top Editorial Breadcrumb */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3">
        <div className="flex items-center gap-2">
          <Link
            href="/companies"
            className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            <span>Back to Companies</span>
          </Link>
          <span className="text-muted-foreground/50">/</span>
          <span className="text-xs font-medium text-muted-foreground">
            {sourceLabel(company.source_db)}
          </span>
          <span className="text-muted-foreground/50">/</span>
          <span className="text-xs font-bold text-foreground truncate max-w-[200px]">
            {company.name}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[11px] font-mono">
            {company.source_act_id || `ID: ${company.id.slice(0, 8)}`}
          </Badge>
        </div>
      </div>

      {/* 3-Zone Split-Pane Company Canvas */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Zone 1: Sticky Company Dossier (Left Column, 4 cols) */}
        <aside className="lg:col-span-4 xl:col-span-4">
          <div className="sticky top-4 flex flex-col gap-4">
            <CompanyDossier company={company} />
          </div>
        </aside>

        {/* Zone 2 & 3: Right Tabbed Canvas (8 cols) */}
        <main className="lg:col-span-8 xl:col-span-8 flex flex-col gap-5">
          <Tabs defaultValue="contacts" className="w-full">
            <div className="flex items-center justify-between border-b border-border/80 pb-1">
              <TabsList className="bg-transparent gap-2 sm:gap-4 p-0">
                <TabsTrigger
                  value="contacts"
                  className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-3 py-2 text-xs sm:text-sm font-semibold cursor-pointer"
                >
                  Contacts ({company.contacts.length})
                </TabsTrigger>
                <TabsTrigger
                  value="notes"
                  className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-3 py-2 text-xs sm:text-sm font-semibold cursor-pointer"
                >
                  Notes ({company.notes.length})
                </TabsTrigger>
                <TabsTrigger
                  value="custom"
                  className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-3 py-2 text-xs sm:text-sm font-semibold cursor-pointer"
                >
                  Custom Fields ({customEntries.length})
                </TabsTrigger>
              </TabsList>

              <AddNoteDialog id={company.id} action={addCompanyNote} />
            </div>

            {/* TAB 1: Associated Contacts Directory */}
            <TabsContent value="contacts" className="mt-4 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-foreground">
                    Contacts
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    People linked to {company.name}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <AddExistingContactPicker companyId={company.id} companyName={company.name} />
                  <ContactFormDialog />
                </div>
              </div>

              {company.contacts.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {company.contacts.map((c) => {
                    const cname =
                      c.full_name ||
                      [c.first_name, c.last_name].filter(Boolean).join(" ") ||
                      "(no name)";
                    return (
                      <Link
                        key={c.id}
                        href={`/contacts/${c.id}`}
                        className="group flex items-start gap-3 rounded-lg border border-border bg-card p-3.5 transition-all hover:border-primary/50 hover:shadow-xs"
                      >
                        <EntityAvatar
                          name={cname}
                          className="size-10 text-xs font-semibold shrink-0"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                            {cname}
                          </div>
                          {c.job_title && (
                            <div className="text-xs text-muted-foreground truncate">
                              {c.job_title}
                            </div>
                          )}
                          {c.primary_email && (
                            <div className="mt-1 text-[11px] font-mono text-muted-foreground truncate">
                              {c.primary_email}
                            </div>
                          )}
                        </div>
                        <ExternalLink className="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </Link>
                    );
                  })}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
                  <Users className="size-8 mx-auto mb-2 opacity-40" />
                  <p className="font-medium">No contacts associated with this company yet.</p>
                  <p className="text-xs mt-1">Use the &apos;New contact&apos; button above to link a person.</p>
                </div>
              )}
            </TabsContent>

            {/* TAB 2: Notes */}
            <TabsContent value="notes" className="mt-4 flex flex-col gap-3">
              {company.notes.length > 0 ? (
                company.notes.map((n) => (
                  <div
                    key={n.id}
                    className="rounded-lg border border-border bg-card p-4 shadow-2xs"
                  >
                    <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
                      <Badge variant="outline" className="text-[10px]">
                        {n.note_type || "Note"}
                      </Badge>
                      <time>
                        {n.act_created_at
                          ? new Date(n.act_created_at).toLocaleDateString()
                          : ""}
                      </time>
                    </div>
                    <p className="text-xs leading-relaxed text-foreground whitespace-pre-wrap">
                      {cleanNoteBody(n.body) || "No content."}
                    </p>
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
                  No notes recorded for this company.
                </div>
              )}
            </TabsContent>

            {/* TAB 3: Custom Fields */}
            <TabsContent value="custom" className="mt-4">
              <Card className="editorial-card p-4">
                <CardHeader className="p-0 pb-3">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Layers className="size-4 text-primary" />
                    <span>Custom Fields</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  {customEntries.length > 0 ? (
                    <div className="grid gap-2.5 sm:grid-cols-2 text-xs">
                      {customEntries.map(([key, value]) => (
                        <div
                          key={key}
                          className="flex flex-col justify-center rounded border border-border/60 bg-muted/20 p-2.5"
                        >
                          <span className="text-[11px] text-muted-foreground font-mono">
                            {key}
                          </span>
                          <span className="font-medium text-foreground mt-0.5">
                            {String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground italic">
                      No custom fields recorded.
                    </span>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </div>
  );
}
