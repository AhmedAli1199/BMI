import Link from "next/link";
import {
  Building2,
  Compass,
  Plane,
  Sparkles,
  Users,
  UsersRound,
} from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { DashboardStats } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EntityAvatar } from "@/components/entity-avatar";
import { PublicationTileButton } from "@/components/publication-tile-button";
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
  const sourceDb = await getPublicationFilter();
  const stats = await backendFetch<DashboardStats>(
    `/api/dashboard/stats${sourceDb ? `?source_db=${sourceDb}` : ""}`
  );

  const KPIS = [
    {
      label: "Total Contacts",
      sublabel: sourceDb ? "In this publication" : "Across all 3 publication titles",
      value: stats.total_contacts,
      icon: Users,
      href: "/contacts",
      color: "text-amber-600 dark:text-amber-400",
      accent: "from-amber-600 to-amber-700",
    },
    {
      label: "Commercial Accounts",
      sublabel: "Airlines, caterers & travel partners",
      value: stats.total_companies,
      icon: Building2,
      href: "/companies",
      color: "text-blue-600 dark:text-blue-400",
      accent: "from-blue-600 to-blue-700",
    },
    {
      label: "Circulation Groups",
      sublabel: "Active buyer & awards segments",
      value: stats.total_groups,
      icon: UsersRound,
      href: "/groups",
      color: "text-emerald-600 dark:text-emerald-400",
      accent: "from-emerald-600 to-emerald-700",
    },
  ];

  const contactsFor = (source: string) =>
    stats.contacts_by_source.find((s) => s.source_db === source)?.count ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-4 sm:p-6 lg:p-8">
      {/* Editorial Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
            <Sparkles className="size-3.5" />
            <span>BMI Publishing Intelligence</span>
          </div>
          <h1 className="editorial-title text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            Sales &amp; Editorial Brain
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-2xl">
            Unified audience database, commercial advertising tracking, and circulation management across every BMI media brand.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <ContactFormDialog />
          <CompanyFormDialog />
          <GroupFormDialog />
        </div>
      </div>

      {/* Magazine Title Quick Switcher Cards - clicking one sets the global
          publication filter (persists across every tab) and stays right
          here, rather than navigating away. */}
      <div className="grid gap-4 sm:grid-cols-3">
        <PublicationTileButton sourceDb="onboard" className="group">
          <Card
            className={`editorial-card h-full transition-all hover:border-blue-500/50 hover:shadow-xs ${
              sourceDb === "onboard" ? "border-blue-500/60 ring-1 ring-blue-500/30" : ""
            }`}
          >
            <CardContent className="flex items-start gap-4 p-5">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 border border-blue-500/20 group-hover:scale-105 transition-transform">
                <Plane className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-foreground group-hover:text-blue-600 transition-colors">
                    Onboard Hospitality
                  </span>
                  <Badge variant="outline" className="text-[10px] border-blue-500/30 text-blue-600">
                    Lead Title
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                  Inflight retail, catering, WTCE &amp; awards
                </p>
                <div className="mt-2 flex items-center gap-2 text-xs font-semibold text-foreground">
                  <span>{contactsFor("onboard").toLocaleString()} Contacts</span>
                  <span className="text-muted-foreground">&rarr;</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </PublicationTileButton>

        <PublicationTileButton sourceDb="sellingtravel" className="group">
          <Card
            className={`editorial-card h-full transition-all hover:border-emerald-500/50 hover:shadow-xs ${
              sourceDb === "sellingtravel" ? "border-emerald-500/60 ring-1 ring-emerald-500/30" : ""
            }`}
          >
            <CardContent className="flex items-start gap-4 p-5">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 group-hover:scale-105 transition-transform">
                <Compass className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-foreground group-hover:text-emerald-600 transition-colors">
                    Selling Travel
                  </span>
                  <Badge variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-600">
                    Monthly Print
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                  UK travel agents, DMOs &amp; tour operators
                </p>
                <div className="mt-2 flex items-center gap-2 text-xs font-semibold text-foreground">
                  <span>{contactsFor("sellingtravel").toLocaleString()} Contacts</span>
                  <span className="text-muted-foreground">&rarr;</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </PublicationTileButton>

        <PublicationTileButton sourceDb="prospects" className="group">
          <Card
            className={`editorial-card h-full transition-all hover:border-amber-500/50 hover:shadow-xs ${
              sourceDb === "prospects" ? "border-amber-500/60 ring-1 ring-amber-500/30" : ""
            }`}
          >
            <CardContent className="flex items-start gap-4 p-5">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 border border-amber-500/20 group-hover:scale-105 transition-transform">
                <Sparkles className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-foreground group-hover:text-amber-600 transition-colors">
                    Prospects Database
                  </span>
                  <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-600">
                    Unclaimed leads
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                  Unclaimed prospects &amp; automated lead discovery
                </p>
                <div className="mt-2 flex items-center gap-2 text-xs font-semibold text-foreground">
                  <span>{contactsFor("prospects").toLocaleString()} Contacts</span>
                  <span className="text-muted-foreground">&rarr;</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </PublicationTileButton>
      </div>

      {sourceDb && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>
            Showing <span className="font-semibold text-foreground">{sourceDb}</span> only.
          </span>
          <PublicationTileButton sourceDb="">
            <span className="font-semibold text-primary hover:underline">Clear filter</span>
          </PublicationTileButton>
        </div>
      )}

      {/* KPI Stats Strip */}
      <div className="grid gap-4 sm:grid-cols-3">
        {KPIS.map((k) => (
          <Link key={k.label} href={k.href} className="group">
            <Card className="editorial-card h-full overflow-hidden transition-all hover:border-primary/50 hover:shadow-xs">
              <div className={`h-1 w-full bg-gradient-to-r ${k.accent}`} />
              <CardContent className="flex items-center justify-between p-6">
                <div>
                  <div className="editorial-stat text-3xl sm:text-4xl font-serif font-bold text-foreground tracking-tight">
                    {k.value.toLocaleString()}
                  </div>
                  <div className="text-sm font-bold text-foreground mt-1">
                    {k.label}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {k.sublabel}
                  </div>
                </div>
                <span className={`flex size-12 shrink-0 items-center justify-center rounded-xl bg-muted/60 ${k.color} border border-border`}>
                  <k.icon className="size-6" />
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Two Column Operational Feed: Recent Contacts & Top Accounts */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Contacts */}
        <Card className="editorial-card">
          <CardHeader className="flex flex-row items-center justify-between border-b pb-3">
            <div>
              <CardTitle className="editorial-heading text-base font-bold text-foreground">
                Recent Touchpoints &amp; Additions
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Latest editorial &amp; commercial contacts updated
              </p>
            </div>
            <Link
              href="/contacts"
              className="text-xs font-semibold text-primary hover:underline"
            >
              View all &rarr;
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 p-3">
            {stats.recent_contacts.length > 0 ? (
              stats.recent_contacts.map((c) => {
                const name =
                  c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "(no name)";
                return (
                  <Link
                    key={c.id}
                    href={`/contacts/${c.id}`}
                    className="flex items-center gap-3 rounded-lg p-2.5 transition-colors hover:bg-accent/50"
                  >
                    <EntityAvatar name={name} className="size-9 text-xs font-bold" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-bold text-foreground">{name}</div>
                      <div className="truncate text-[11px] text-muted-foreground">
                        {c.job_title}
                        {c.job_title && c.company_name ? " · " : ""}
                        <span className="font-medium text-foreground/80">{c.company_name}</span>
                      </div>
                    </div>
                    <span className="shrink-0 text-[11px] font-medium text-muted-foreground">
                      {timeAgo(c.created_at)}
                    </span>
                  </Link>
                );
              })
            ) : (
              <span className="text-xs text-muted-foreground p-4">No recent contacts.</span>
            )}
          </CardContent>
        </Card>

        {/* Top Accounts */}
        <Card className="editorial-card">
          <CardHeader className="flex flex-row items-center justify-between border-b pb-3">
            <div>
              <CardTitle className="editorial-heading text-base font-bold text-foreground">
                Key Publishing Accounts
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                High-density accounts with active advertising inserts
              </p>
            </div>
            <Link
              href="/companies"
              className="text-xs font-semibold text-primary hover:underline"
            >
              View all &rarr;
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 p-3">
            {stats.top_companies.length > 0 ? (
              stats.top_companies.map((c) => (
                <Link
                  key={c.id}
                  href={`/companies/${c.id}`}
                  className="flex items-center gap-3 rounded-lg p-2.5 transition-colors hover:bg-accent/50"
                >
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
                    <Building2 className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-bold text-foreground">{c.name}</div>
                    <div className="truncate text-[11px] text-muted-foreground">
                      {c.industry || "Commercial Partner"}
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-[11px] font-semibold">
                    {c.contact_count} contacts
                  </Badge>
                </Link>
              ))
            ) : (
              <span className="text-xs text-muted-foreground p-4">No companies found.</span>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
