import Link from "next/link";
import { ChevronRight } from "lucide-react";

export type Crumb = { label: string; href: string };

/** The one header every page uses (docs/design/ui-audit.md, "one page header"):
 *  - above the title, EITHER a breadcrumb (`crumbs`: the pages above this one; the title is added as the last step)
 *    OR the area's name in small capitals (`section`, e.g. "Sales", "The Brain", "Clients") - never both, never neither
 *  - the title is a name ("Bookings", "Automation settings"), not a sentence
 *  - one short plain description; anything longer goes in an InfoHint
 *  - actions on the right, primary action last
 *  - `below` is for something that belongs to the title, like a status line (tabs go after the header, see PageTabs)
 */
export function PageHeader({ title, description, crumbs, section = "", actions, below }: {
  title: React.ReactNode;
  description?: React.ReactNode;
  crumbs?: Crumb[];
  section?: string;
  actions?: React.ReactNode;
  below?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
      <div className="min-w-0">
        <nav aria-label="Breadcrumb" className="mb-1.5 flex min-h-4 flex-wrap items-center gap-1 text-xs font-semibold text-muted-foreground">
          {crumbs?.length ? (
            <>
              {crumbs.map((c) => (
                <span key={c.href} className="flex items-center gap-1">
                  <Link href={c.href} className="hover:text-foreground">{c.label}</Link>
                  <ChevronRight className="size-3.5" aria-hidden="true" />
                </span>
              ))}
              <span className="truncate text-foreground" aria-current="page">{title}</span>
            </>
          ) : (
            section && <span className="uppercase tracking-wider text-primary">{section}</span>
          )}
        </nav>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">{title}</h1>
        {below && <div className="mt-1">{below}</div>}
        {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
