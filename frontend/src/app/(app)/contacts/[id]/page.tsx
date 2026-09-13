import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  FileText,
  Layers,
  Sparkles,
  UserCheck,
} from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactDetail } from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ContactDossier } from "@/components/contact-dossier";
import { UnifiedActivityTimeline } from "@/components/unified-activity-timeline";
import { InlineActivityComposer } from "@/components/inline-activity-composer";
import { sourceLabel } from "@/lib/sources";

export default async function ContactDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let contact: ContactDetail;
  try {
    contact = await backendFetch<ContactDetail>(`/api/contacts/${id}`);
  } catch {
    notFound();
  }

  const name =
    contact.full_name ||
    [contact.first_name, contact.last_name].filter(Boolean).join(" ") ||
    "(no name)";

  // Partition custom fields into meaningful publishing groups
  const customEntries = Object.entries(contact.custom_fields || {});
  const publishingFields = customEntries.filter(([k]) =>
    /issue|ad|print|circulation|tier|title|sponsor|expo|wtce/i.test(k)
  );
  const generalFields = customEntries.filter(
    ([k]) => !/issue|ad|print|circulation|tier|title|sponsor|expo|wtce/i.test(k)
  );

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      {/* Editorial Navigation Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3">
        <div className="flex items-center gap-2">
          <Link
            href="/contacts"
            className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            <span>Back to Contacts</span>
          </Link>
          <span className="text-muted-foreground/50">/</span>
          <span className="text-xs font-medium text-muted-foreground">
            {sourceLabel(contact.source_db)}
          </span>
          <span className="text-muted-foreground/50">/</span>
          <span className="text-xs font-bold text-foreground truncate max-w-[200px]">
            {name}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[11px] font-mono">
            {contact.source_act_id || `ID: ${contact.id.slice(0, 8)}`}
          </Badge>
        </div>
      </div>

      {/* 3-Zone Split-Pane Editorial Workspace */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Zone 1: Sticky Identity Dossier (Left Column, 4 cols on lg, 3.5 on xl) */}
        <aside className="lg:col-span-4 xl:col-span-4">
          <div className="sticky top-4 flex flex-col gap-4">
            {/* Category/Department/Referred by/Source database are all
                shown (and, in edit mode, editable) on the dossier itself
                now - a separate read-only summary card here just repeated
                the same three fields under different labels. */}
            <ContactDossier contact={contact} />
          </div>
        </aside>

        {/* Zone 2 & 3: Tabbed Operational Canvas (Right Column, 8 cols) */}
        <main className="lg:col-span-8 xl:col-span-8 flex flex-col gap-5">
          {/* Quick Touchpoint Composer Bar */}
          <InlineActivityComposer contactId={contact.id} contactName={name} />

          {/* Workspace Tabs */}
          <Tabs defaultValue="timeline" className="w-full">
            <div className="flex items-center justify-between border-b border-border/80 pb-1">
              <TabsList className="bg-transparent gap-2 sm:gap-4 p-0">
                <TabsTrigger
                  value="timeline"
                  className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-3 py-2 text-xs sm:text-sm font-semibold cursor-pointer"
                >
                  Activity &amp; Notes ({contact.notes.length + contact.history.length})
                </TabsTrigger>
                <TabsTrigger
                  value="commercial"
                  className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-3 py-2 text-xs sm:text-sm font-semibold cursor-pointer"
                >
                  Magazine &amp; Commercial
                </TabsTrigger>
                <TabsTrigger
                  value="custom"
                  className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-3 py-2 text-xs sm:text-sm font-semibold cursor-pointer"
                >
                  Custom Fields ({customEntries.length})
                </TabsTrigger>
              </TabsList>
            </div>

            {/* TAB 1: Activity Timeline */}
            <TabsContent value="timeline" className="mt-4">
              <UnifiedActivityTimeline
                notes={contact.notes}
                history={contact.history}
              />
            </TabsContent>

            {/* TAB 2: Magazine & Commercial */}
            <TabsContent value="commercial" className="mt-4 flex flex-col gap-4">
              <Card className="editorial-card">
                <CardHeader>
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <BookOpen className="size-4 text-primary" />
                    <span>Issue &amp; Advertising Placement</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3 text-xs">
                  {publishingFields.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {publishingFields.map(([k, v]) => (
                        <div
                          key={k}
                          className="rounded-md border border-border/80 bg-muted/30 p-3"
                        >
                          <span className="text-muted-foreground block text-[11px] mb-1">
                            {k}
                          </span>
                          <span className="font-semibold text-foreground text-sm">
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-lg border border-dashed p-6 text-center text-muted-foreground">
                      No ad campaign or issue-specific data recorded yet.
                    </div>
                  )}

                  {contact.company && (
                    <div className="mt-2 rounded-md border border-primary/20 bg-primary/5 p-3 flex items-center justify-between">
                      <div>
                        <span className="font-semibold text-foreground block">
                          Company: {contact.company.name}
                        </span>
                        <span className="text-muted-foreground text-[11px]">
                          Industry: {contact.company.industry || "No industry on file"}
                        </span>
                      </div>
                      <Link
                        href={`/companies/${contact.company.id}`}
                        className="text-xs font-semibold text-primary hover:underline"
                      >
                        View Company &rarr;
                      </Link>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* TAB 3: Custom Fields & Legacy Act! Archive */}
            <TabsContent value="custom" className="mt-4 flex flex-col gap-4">
              <Card className="editorial-card">
                <CardHeader>
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Layers className="size-4 text-primary" />
                    <span>Custom Fields</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
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
                      No custom fields on file.
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
