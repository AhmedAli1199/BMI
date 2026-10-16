import Link from "next/link";

/** Tabs across the top of a page where each tab is its own address (so links and the back button work). Hidden when
 * only one tab is left. */
export function PageTabs({ label, tabs }: { label: string; tabs: { label: string; href: string; active: boolean }[] }) {
  if (tabs.length < 2) return null;
  return (
    <nav className="-mt-3 flex gap-4 border-b border-border/80" aria-label={label}>
      {tabs.map((t) => (
        <Link key={t.href} href={t.href} aria-current={t.active ? "page" : undefined}
          className={`-mb-px border-b-2 px-1 pb-2 text-sm font-semibold transition-colors ${
            t.active ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
          }`}>
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
