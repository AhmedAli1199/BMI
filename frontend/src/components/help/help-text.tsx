import Link from "next/link";
import { Fragment } from "react";

/** Inline text in a help article: **bold** for what's on screen, [words](article-slug) for another article,
 * [words](/path) for a page in the app (opens in a new tab, so the article stays open). */
export function HelpText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g);
  return (
    <>
      {parts.map((p, i) => {
        const bold = p.match(/^\*\*([^*]+)\*\*$/);
        if (bold) return <strong key={i} className="font-semibold text-foreground">{bold[1]}</strong>;
        const link = p.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
        if (link) {
          const [, label, to] = link;
          return to.startsWith("/")
            ? <a key={i} href={to} target="_blank" rel="noreferrer" className="font-medium text-primary underline-offset-2 hover:underline">{label}</a>
            : <Link key={i} href={`/help/${to}`} className="font-medium text-primary underline-offset-2 hover:underline">{label}</Link>;
        }
        return <Fragment key={i}>{p}</Fragment>;
      })}
    </>
  );
}
