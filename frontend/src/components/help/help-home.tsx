"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, BookOpen, Briefcase, Clock, Search, Users } from "lucide-react";
import { BrainBuddy } from "@/components/brain/brain-buddy";
import { EmptyState } from "@/components/empty-state";
import { Input } from "@/components/ui/input";
import { AskTheBrain } from "@/components/help/ask-the-brain";
import { ARTICLES, CATEGORY_BLURB, type HelpArticle, type HelpCategory } from "@/content/help/articles";

const ICONS: Partial<Record<HelpCategory, typeof BookOpen>> = { Sales: Briefcase, Clients: Users };

const plain = (s: string) => s.replace(/\*\*|\[|\]\([^)]*\)/g, "");
const haystack = (a: HelpArticle) =>
  [a.title, a.summary, a.intro ?? "", ...a.steps.map((s) => s.text), ...(a.problems ?? []).map((p) => `${p.q} ${p.a}`)].map(plain).join(" ").toLowerCase();

/** The Help Centre's front page: search across every article, then the articles grouped like the menu. */
export function HelpHome() {
  const [q, setQ] = useState("");
  const found = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return words.length ? ARTICLES.filter((a) => words.every((w) => haystack(a).includes(w))) : null;
  }, [q]);
  const groups = useMemo(() => {
    const m = new Map<HelpCategory, HelpArticle[]>();
    for (const a of ARTICLES) m.set(a.category, [...(m.get(a.category) ?? []), a]);
    return [...m.entries()];
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
        <div className="flex items-start gap-4">
          <BrainBuddy mood="happy" size={64} className="hidden shrink-0 sm:block" />
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold">What do you need to do?</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">Short guides with pictures, one job each.</p>
            <label className="relative mt-4 block max-w-xl">
              <span className="sr-only">Search the Help Centre</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Try “confirmation” or “reminder”" className="h-11 pl-9 text-base" autoFocus />
            </label>
          </div>
        </div>
      </div>

      {found ? (
        <section aria-label="Search results" className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">{found.length} article{found.length === 1 ? "" : "s"} found</p>
          {found.length ? (
            <ul className="grid gap-3 sm:grid-cols-2">{found.map((a) => <li key={a.slug}><ArticleCard a={a} /></li>)}</ul>
          ) : (
            <EmptyState mood="puzzled" title="No articles match that yet" action={<AskTheBrain question={q} />}>
              Try other words, or ask the Brain - it knows every screen.
            </EmptyState>
          )}
        </section>
      ) : (
        <>
          <section aria-labelledby="start-here" className="flex flex-col gap-3">
            <h2 id="start-here" className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Start here</h2>
            <ul className="grid gap-3 md:grid-cols-3">
              {["make-a-booking", "send-the-confirmation", "ask-the-brain"].map((s) => ARTICLES.find((a) => a.slug === s)!).map((a) => (
                <li key={a.slug}><ArticleCard a={a} picture /></li>
              ))}
            </ul>
          </section>
          <section aria-label="All articles" className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {groups.map(([cat, list]) => {
              const Icon = ICONS[cat] ?? BookOpen;
              return (
                <div key={cat} id={cat.toLowerCase().replace(/ /g, "-")} className="flex scroll-mt-6 flex-col rounded-xl border border-border bg-card p-5">
                  <div className="flex items-center gap-2.5">
                    <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon className="size-4" /></span>
                    <div>
                      <h2 className="text-base font-semibold">{cat}</h2>
                      <p className="text-xs text-muted-foreground">{CATEGORY_BLURB[cat]}</p>
                    </div>
                  </div>
                  <ul className="mt-4 flex flex-col gap-0.5">
                    {list.map((a) => (
                      <li key={a.slug}>
                        <Link href={`/help/${a.slug}`} className="group flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent">
                          <span className="group-hover:text-primary">{a.title}</span>
                          <ArrowRight className="size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </section>
        </>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-border bg-card/50 px-5 py-4 text-sm">
        <BrainBuddy mood="waving" head size={28} className="shrink-0" />
        <span className="min-w-0 flex-1">Can&apos;t find what you need? The Brain can explain any screen.</span>
        <AskTheBrain />
      </div>
    </div>
  );
}

export function ArticleCard({ a, picture = false }: { a: HelpArticle; picture?: boolean }) {
  return (
    <Link href={`/help/${a.slug}`} className="group flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card transition-colors hover:border-primary/60">
      {picture && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={`/help/${a.slug}/${a.cover ?? a.steps.find((s) => s.shot)?.shot ?? 1}.png`} alt="" className="aspect-[16/8] w-full border-b border-border object-cover object-top" />
      )}
      <div className="flex flex-1 flex-col gap-1 p-4">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">{a.category}</span>
        <span className="font-semibold group-hover:text-primary">{a.title}</span>
        <span className="text-sm text-muted-foreground">{a.summary}</span>
        <span className="mt-auto flex items-center gap-1 pt-2 text-xs text-muted-foreground"><Clock className="size-3" aria-hidden="true" /> {a.minutes} min read</span>
      </div>
    </Link>
  );
}
