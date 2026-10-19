import Link from "next/link";
import { notFound } from "next/navigation";
import { CheckCircle2, Clock, Lightbulb, Info, UserRound } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { HelpText } from "@/components/help/help-text";
import { ArticleCard } from "@/components/help/help-home";
import { WasItHelpful } from "@/components/help/was-it-helpful";
import { ARTICLES, bySlug } from "@/content/help/articles";

export function generateStaticParams() {
  return ARTICLES.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const a = bySlug((await params).slug);
  return { title: a ? `${a.title} - Help Centre` : "Help Centre" };
}

/** One help article (docs/help-centre-plan.md): the task, numbered steps with pictures, what happens next, the usual
 * snags and related articles. */
export default async function HelpArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const a = bySlug((await params).slug);
  if (!a) notFound();
  const related = a.related.map(bySlug).filter((r) => !!r);
  const toc = [
    { id: "steps", label: "Step by step" },
    a.goodToKnow?.length ? { id: "good-to-know", label: "Good to know" } : null,
    a.next ? { id: "next", label: "What happens next" } : null,
    a.problems?.length ? { id: "problems", label: "If something's not right" } : null,
    related.length ? { id: "related", label: "Related articles" } : null,
  ].filter((t) => !!t);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader crumbs={[{ label: "Help Centre", href: "/help" }, { label: a.category, href: `/help#${a.category.toLowerCase().replace(/ /g, "-")}` }]} title={a.title}
        description={a.summary}
        below={
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><UserRound className="size-3.5" aria-hidden="true" /> For: {a.audience}</span>
            <span className="flex items-center gap-1"><Clock className="size-3.5" aria-hidden="true" /> {a.minutes} min read</span>
          </div>
        } />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_15rem]">
        <article className="flex min-w-0 flex-col gap-8">
          {a.intro && <p className="max-w-3xl text-[15px] leading-relaxed text-foreground/90"><HelpText text={a.intro} /></p>}

          <section aria-labelledby="steps" className="flex flex-col gap-6">
            <h2 id="steps" className="scroll-mt-20 text-lg font-semibold">Step by step</h2>
            <ol className="flex flex-col gap-8">
              {a.steps.map((s, i) => (
                <li key={i} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-4 gap-y-3">
                  <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">{i + 1}</span>
                  <div className="flex min-w-0 flex-col gap-3">
                    <p className="pt-1 text-[15px] leading-relaxed"><span className="sr-only">Step {i + 1}: </span><HelpText text={s.text} /></p>
                    {s.tip && (
                      <p className="flex gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm">
                        <Lightbulb className="mt-0.5 size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
                        <span><strong className="font-semibold">Tip: </strong><HelpText text={s.tip} /></span>
                      </p>
                    )}
                    {s.shot && (
                      <a href={`/help/${a.slug}/${s.shot}.png`} target="_blank" rel="noreferrer" title="Open the picture full size"
                        className="block overflow-hidden rounded-xl border border-border shadow-sm transition-shadow hover:shadow-md">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={`/help/${a.slug}/${s.shot}.png`} alt={s.alt ?? ""} loading="lazy" className="w-full" />
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {a.goodToKnow?.length ? (
            <section aria-labelledby="good-to-know" className="rounded-xl border border-border bg-primary/5 p-5">
              <h2 id="good-to-know" className="flex scroll-mt-20 items-center gap-2 text-base font-semibold"><Info className="size-4 text-primary" aria-hidden="true" /> Good to know</h2>
              <ul className="mt-3 flex flex-col gap-2 text-[15px] leading-relaxed">
                {a.goodToKnow.map((g, i) => <li key={i} className="flex gap-2"><span aria-hidden="true" className="mt-2.5 size-1.5 shrink-0 rounded-full bg-primary" /><span><HelpText text={g} /></span></li>)}
              </ul>
            </section>
          ) : null}

          {a.next && (
            <section aria-labelledby="next" className="flex gap-3">
              <CheckCircle2 className="mt-1 size-5 shrink-0" style={{ color: "var(--ok)" }} aria-hidden="true" />
              <div>
                <h2 id="next" className="scroll-mt-20 text-base font-semibold">What happens next</h2>
                <p className="mt-1 text-[15px] leading-relaxed"><HelpText text={a.next} /></p>
              </div>
            </section>
          )}

          {a.problems?.length ? (
            <section aria-labelledby="problems" className="flex flex-col gap-3">
              <h2 id="problems" className="scroll-mt-20 text-base font-semibold">If something&apos;s not right</h2>
              <div className="divide-y divide-border rounded-xl border border-border bg-card">
                {a.problems.map((p, i) => (
                  <details key={i} className="group px-4 py-3">
                    <summary className="cursor-pointer list-none font-medium marker:hidden">
                      <span className="mr-2 inline-block text-muted-foreground transition-transform group-open:rotate-90" aria-hidden="true">›</span>{p.q}
                    </summary>
                    <p className="mt-2 pl-4 text-[15px] leading-relaxed text-foreground/90"><HelpText text={p.a} /></p>
                  </details>
                ))}
              </div>
            </section>
          ) : null}

          <WasItHelpful title={a.title} />

          {related.length > 0 && (
            <section aria-labelledby="related" className="flex flex-col gap-3">
              <h2 id="related" className="scroll-mt-20 text-base font-semibold">Related articles</h2>
              <ul className="grid gap-3 sm:grid-cols-2">{related.map((r) => <li key={r.slug}><ArticleCard a={r} /></li>)}</ul>
            </section>
          )}
        </article>

        <aside className="hidden lg:block">
          <nav aria-label="On this page" className="sticky top-6 flex flex-col gap-1 text-sm">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">On this page</p>
            {toc.map((t) => <a key={t.id} href={`#${t.id}`} className="rounded-md px-2 py-1 text-muted-foreground hover:bg-accent hover:text-foreground">{t.label}</a>)}
            <Link href="/help" className="mt-4 rounded-md px-2 py-1 text-primary hover:bg-accent">← All articles</Link>
          </nav>
        </aside>
      </div>
    </div>
  );
}
