import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, Layers, Users } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { CompanyDetail } from "@/lib/types";
import { getSession } from "@/lib/session";
import { allowedSourceDbSlugs } from "@/lib/access";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EntityAvatar } from "@/components/entity-avatar";
import { TouchpointBar } from "@/components/touchpoint-bar";
import { UnifiedActivityTimeline } from "@/components/unified-activity-timeline";
import { cleanNoteBody } from "@/lib/notes";
import { sourceLabel } from "@/lib/sources";
import { ContactFormDialog } from "@/components/contact-form-dialog";
import { AddExistingContactPicker } from "@/components/add-existing-contact-picker";
import { ActSubbar } from "@/components/act-subbar";
import { ActCompanyCard } from "@/components/act-company-card";

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

  // Defense in depth against a guessed/direct URL - companies aren't
  // group-scoped (see contacts/[id]/page.tsx's comment on why), so
  // unlike a contact, only the database itself is checked here: any
  // grant on this database (full or group-scoped) is enough.
  const session = await getSession();
  if (session && session.role !== "admin" && !allowedSourceDbSlugs(session).includes(company.source_db)) {
    notFound();
  }

  const customEntries = Object.entries(company.custom_fields || {});

  return (
    <div className="flex w-full flex-col">
      {/* ACT! Sub-header Navigation Ribbon */}
      <ActSubbar module="companies" />

      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-4 sm:p-6">
        {/* Top Editorial Breadcrumb */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
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
            <span className="text-xs font-bold text-foreground truncate max-w-[240px]">
              {company.name}
            </span>
          </div>
        </div>

        {/* Tier 1: ACT! Authentic 3-Column Upper Company Card */}
        <ActCompanyCard company={company} />

        {/* Tier 2: ACT! Full-Width Bottom Sub-Workstation Tabs */}
        <Tabs defaultValue="contacts" className="w-full">
          <div className="flex items-center justify-between border-b border-border/80 bg-muted/30 px-3 pt-1">
            <TabsList className="bg-transparent gap-1 p-0 h-auto">
              <TabsTrigger
                value="contacts"
                className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-card rounded-t-md rounded-b-none px-3.5 py-2 text-xs font-semibold cursor-pointer gap-1.5"
              >
                <Users className="size-3.5 text-blue-600" />
                <span>Associated Contacts ({company.contacts.length})</span>
              </TabsTrigger>
              <TabsTrigger
                value="activity"
                className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-card rounded-t-md rounded-b-none px-3.5 py-2 text-xs font-semibold cursor-pointer gap-1.5"
              >
                <span>Activity &amp; History ({company.history.length + company.activities.length})</span>
              </TabsTrigger>
              <TabsTrigger
                value="notes"
                className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-card rounded-t-md rounded-b-none px-3.5 py-2 text-xs font-semibold cursor-pointer gap-1.5"
              >
                <span>Company Notes ({company.notes.length})</span>
              </TabsTrigger>
              <TabsTrigger
                value="custom"
                className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-card rounded-t-md rounded-b-none px-3.5 py-2 text-xs font-semibold cursor-pointer gap-1.5"
              >
                <Layers className="size-3.5 text-muted-foreground" />
                <span>User Fields ({customEntries.length})</span>
              </TabsTrigger>
            </TabsList>
          </div>

          {/* TAB 1: Associated Contacts Directory */}
          <TabsContent value="contacts" className="mt-4 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-foreground">
                  Contacts linked to {company.name}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Key decision-makers, media directors, and editorial contacts
                </p>
              </div>
              <div className="flex items-center gap-2">
                <AddExistingContactPicker companyId={company.id} companyName={company.name} />
                <ContactFormDialog defaultSourceDb={company.source_db} />
              </div>
            </div>

            {company.contacts.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
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
                <p className="text-xs mt-1">Use the &apos;Link Existing Contact&apos; or &apos;New Contact&apos; button above to connect people.</p>
              </div>
            )}
          </TabsContent>

          {/* TAB 2: Activity & History */}
          <TabsContent value="activity" className="mt-4 flex flex-col gap-4">
            <TouchpointBar companyId={company.id} contactName={company.name} sourceDb={company.source_db} />
            <UnifiedActivityTimeline notes={[]} history={company.history} activities={company.activities} />
          </TabsContent>

          {/* TAB 3: Notes */}
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
            <Card className="editorial-card p-5 border border-border">
              <CardHeader className="p-0 pb-3 border-b mb-3">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <Layers className="size-4 text-primary" />
                  <span>Act! Custom Database Fields</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {customEntries.length > 0 ? (
                  <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 text-xs">
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
      </div>
    </div>
  );
}
