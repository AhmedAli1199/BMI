import Link from "next/link";
import { Building2, Sparkles, Users, UsersRound } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { DashboardStats, UserPreferences } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { getSession } from "@/lib/session";
import { listPublications } from "@/lib/actions";
import { iconForKey, styleForColor } from "@/lib/publication-style";
import { accessLabel, allowedSourceDbSlugs, canAddDatabase, resolveScope } from "@/lib/access";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EntityAvatar } from "@/components/entity-avatar";
import { PublicationTileButton } from "@/components/publication-tile-button";
import { PublicationFormDialog } from "@/components/publication-form-dialog";
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
  const [rawSourceDb, session, allPublications] = await Promise.all([
    getPublicationFilter(),
    getSession(),
    listPublications(),
  ]);

  // Clamps whatever the publication cookie says to what this session is
  // actually allowed to see (and resolves any group restriction within
  // it) - see lib/access.ts. Admins pass through untouched.
  const scope = resolveScope(session, rawSourceDb);
  const sourceDb = scope.source_db === "__no_access__" ? "" : scope.source_db;
  // Non-admins only ever see their own allowed titles as tiles/switcher
  // options - never the other two.
  const publications = session?.role === "admin"
    ? allPublications
    : allPublications.filter((p) => allowedSourceDbSlugs(session).includes(p.slug));

  // The "Recently Active" sort is a per-user preference (see /settings +
  // backend/app/preferences.py) - this was the one piece that never
  // actually got wired up: the setting saved fine, but nothing read it
  // back and passed it to the stats call, so it silently kept using the
  // default no matter what was chosen.
  const recentActivitySort = session
    ? (
        await backendFetch<UserPreferences>(
          `/api/users/${session.sub}/preferences`
        ).catch(() => undefined)
      )?.values?.recent_activity_sort
    : undefined;

  const statsParams = new URLSearchParams();
  if (sourceDb) statsParams.set("source_db", sourceDb);
  if (scope.group_id) statsParams.set("group_id", scope.group_id);
  if (recentActivitySort) statsParams.set("recent_activity_sort", recentActivitySort);

  if (scope.source_db === "__no_access__") {
    return (
      <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-3 p-6 pt-24 text-center">
        <h1 className="text-xl font-bold text-foreground">No database access yet</h1>
        <p className="text-sm text-muted-foreground">
          Your account doesn&apos;t have any database assigned. Ask an administrator to grant you access under
          Settings → Team.
        </p>
      </div>
    );
  }

  const stats = await backendFetch<DashboardStats>(`/api/dashboard/stats${statsParams.size ? `?${statsParams}` : ""}`);

  const KPIS = [
    {
      label: "Total Contacts",
      sublabel: sourceDb ? "In this publication" : "Across all 3 publication titles",
      value: stats.total_contacts,
      icon: Users,
      href: "/contacts",
      color: "text-[#132c6b]",
      accent: "bg-[#132c6b]",
    },
    {
      label: "Companies",
      sublabel: "Airlines, caterers & travel partners",
      value: stats.total_companies,
      icon: Building2,
      href: "/companies",
      color: "text-[#0099e5]",
      accent: "bg-[#0099e5]",
    },
    {
      label: "Groups",
      sublabel: "Active buyer & awards segments",
      value: stats.total_groups,
      icon: UsersRound,
      href: "/groups",
      color: "text-[#c0392b]",
      accent: "bg-[#c0392b]",
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
          {scope.group_name && (
            <p className="mt-1 text-[11px] font-medium text-primary">
              Showing {accessLabel({ source_db: sourceDb, group_id: scope.group_id, group_name: scope.group_name })} only
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <ContactFormDialog defaultSourceDb={sourceDb} />
          <CompanyFormDialog defaultSourceDb={sourceDb} />
          <GroupFormDialog />
        </div>
      </div>

      {/* Magazine Title Quick Switcher Cards - only shown on "All Titles"
          (no sourceDb filter). Once a specific title is selected, showing
          the other two titles' "0 Contacts" tiles here is just clutter -
          nothing on this page reads them at that point, the single-line
          "Showing X only" strip below already says which title is active.
          Clicking one sets the global publication filter (persists across
          every tab) and stays right here, rather than navigating away.
          Renders entirely from `publications` (fetched from
          /api/publications) - adding a database via the tile below shows
          up here immediately, same styling as the three original titles. */}
      {!sourceDb && (
        <div className="grid gap-4 sm:grid-cols-3">
          {publications.map((pub) => {
            const style = styleForColor(pub.color);
            const Icon = iconForKey(pub.icon);
            return (
              <PublicationTileButton key={pub.slug} sourceDb={pub.slug} className="group">
                <Card className="editorial-card h-full overflow-hidden transition-all hover:shadow-xs hover:border-primary/40">
                  <div className={`masthead-rule w-full ${style.accent}`} />
                  <CardContent className="flex items-start gap-4 p-5">
                    <div
                      className={`brand-icon size-10 shrink-0 transition-transform group-hover:scale-105 ${style.chipBg}`}
                    >
                      <Icon className="size-4.5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <span className="text-sm font-bold text-foreground transition-colors">
                        {pub.name}
                      </span>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                        {pub.description || "No description yet"}
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-xs font-semibold text-foreground">
                        <span>{contactsFor(pub.slug).toLocaleString()} Contacts</span>
                        <span className="text-muted-foreground">&rarr;</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </PublicationTileButton>
            );
          })}

          {/* "Add a database" - not a separate Postgres database, a new
              source_db label any contact/company can be filed under (see
              backend/app/models/publication.py). Admin-only. */}
          {canAddDatabase(session) && (
            <Card className="editorial-card flex h-full items-center justify-center border-dashed p-5">
              <PublicationFormDialog />
            </Card>
          )}
        </div>
      )}

      {sourceDb && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>
            Showing <span className="font-semibold text-foreground">{sourceDb}</span> only.
          </span>
          {/* "Show all titles" is only a real option for someone who can
              actually see more than one database - for anyone locked to a
              single title (see scope.locked / resolveScope), this link
              used to appear and do nothing when clicked, since the scope
              would just clamp straight back to their one allowed database. */}
          {!scope.locked && (
            <PublicationTileButton sourceDb="">
              <span className="font-semibold text-primary hover:underline">Show all titles</span>
            </PublicationTileButton>
          )}
        </div>
      )}

      {/* KPI Stats Strip */}
      <div className="grid gap-4 sm:grid-cols-3">
        {KPIS.map((k) => (
          <Link key={k.label} href={k.href} className="group">
            <Card className="editorial-card h-full overflow-hidden transition-all hover:border-primary/50 hover:shadow-xs">
              <div className={`masthead-rule w-full ${k.accent}`} />
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
                <span className={`brand-icon size-11 shrink-0 ${k.color}`}>
                  <k.icon className="size-5" />
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Two Column Operational Feed: Recent Contacts & Top Companies */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Contacts */}
        <Card className="editorial-card">
          <CardHeader className="flex flex-row items-center justify-between border-b pb-3">
            <div>
              <CardTitle className="editorial-heading text-base font-bold text-foreground">
                Recently Active Contacts
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                {recentActivitySort === "engagement"
                  ? "Most recent note or logged call - see /settings to change"
                  : "Most recently added or edited in Act! - see /settings to change"}
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

        {/* Top Companies */}
        <Card className="editorial-card">
          <CardHeader className="flex flex-row items-center justify-between border-b pb-3">
            <div>
              <CardTitle className="editorial-heading text-base font-bold text-foreground">
                Top Companies
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Companies with the most contacts on file
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
                  <div className="brand-icon size-9 shrink-0 text-primary">
                    <Building2 className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-bold text-foreground">{c.name}</div>
                    <div className="truncate text-[11px] text-muted-foreground">
                      {c.industry || "No industry on file"}
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
