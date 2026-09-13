import Link from "next/link";
import { Building2, ListPlus, Users, UsersRound } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { DashboardStats } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EntityAvatar } from "@/components/entity-avatar";
import { sourceLabel } from "@/lib/sources";
import { ContactFormDialog } from "@/components/contact-form-dialog";
import { CompanyFormDialog } from "@/components/company-form-dialog";
import { GroupFormDialog } from "@/components/group-form-dialog";

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.round(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

export default async function DashboardPage() {
  const stats = await backendFetch<DashboardStats>("/api/dashboard/stats");

  const KPIS = [
    { label: "Contacts", value: stats.total_contacts, icon: Users, href: "/contacts" },
    { label: "Companies", value: stats.total_companies, icon: Building2, href: "/companies" },
    { label: "Groups", value: stats.total_groups, icon: UsersRound, href: "/groups" },
  ];

  const maxSourceCount = Math.max(1, ...stats.contacts_by_source.map((s) => s.count));

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">CRM overview</h1>
          <p className="text-sm text-muted-foreground">
            The BMI Publishing sales database, at a glance.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ContactFormDialog />
          <CompanyFormDialog />
          <GroupFormDialog />
        </div>
      </div>

      {/* KPI strip - the first thing anyone opening a CRM expects: how much
          data is in here, one click from each number to the full list. */}
      <div className="grid gap-4 sm:grid-cols-3">
        {KPIS.map((k) => (
          <Link key={k.label} href={k.href}>
            <Card className="h-full transition-colors hover:border-primary/40 hover:bg-accent/40">
              <CardContent className="flex items-center gap-4 py-5">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <k.icon className="size-5" />
                </span>
                <div>
                  <div className="text-2xl font-semibold tabular-nums">
                    {k.value.toLocaleString()}
                  </div>
                  <div className="text-sm text-muted-foreground">{k.label}</div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recently added contacts</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {stats.recent_contacts.length > 0 ? (
              stats.recent_contacts.map((c) => {
                const name =
                  c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "(no name)";
                return (
                  <Link
                    key={c.id}
                    href={`/contacts/${c.id}`}
                    className="flex items-center gap-3 rounded-md px-2 py-2 -mx-2 hover:bg-accent/60"
                  >
                    <EntityAvatar name={name} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{name}</div>
                      <div className="truncate text-xs text-muted-foreground">
                        {c.job_title}
                        {c.job_title && c.company_name ? " · " : ""}
                        {c.company_name}
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {timeAgo(c.created_at)}
                    </span>
                  </Link>
                );
              })
            ) : (
              <span className="text-sm text-muted-foreground">Nothing added yet.</span>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recently added companies</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {stats.recent_companies.length > 0 ? (
              stats.recent_companies.map((c) => (
                <Link
                  key={c.id}
                  href={`/companies/${c.id}`}
                  className="flex items-center gap-3 rounded-md px-2 py-2 -mx-2 hover:bg-accent/60"
                >
                  <EntityAvatar name={c.name} square />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{c.name}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {c.industry || "No industry on file"}
                    </div>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {timeAgo(c.created_at)}
                  </span>
                </Link>
              ))
            ) : (
              <span className="text-sm text-muted-foreground">Nothing added yet.</span>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Biggest accounts</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {stats.top_companies.length > 0 ? (
              stats.top_companies.map((c) => (
                <Link
                  key={c.id}
                  href={`/companies/${c.id}`}
                  className="flex items-center gap-3 rounded-md px-2 py-2 -mx-2 hover:bg-accent/60"
                >
                  <EntityAvatar name={c.name} square />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{c.name}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {c.industry || "No industry on file"}
                    </div>
                  </div>
                  <Badge variant="secondary" className="shrink-0">
                    {c.contact_count.toLocaleString()} contacts
                  </Badge>
                </Link>
              ))
            ) : (
              <span className="text-sm text-muted-foreground">No linked contacts yet.</span>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contacts by source</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {stats.contacts_by_source.map((s) => (
              <div key={s.source_db} className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{sourceLabel(s.source_db)}</span>
                  <span className="text-muted-foreground">{s.count.toLocaleString()}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.max(4, (s.count / maxSourceCount) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Automations</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            The Act! replacement automations - renewals, campaigns, data hygiene - get
            their own dashboard, kept separate so this one stays a clean CRM home.
          </p>
          <Button variant="outline" className="shrink-0" render={<Link href="/requirements" />}>
            <ListPlus className="size-4" />
            Browse automation specs
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
