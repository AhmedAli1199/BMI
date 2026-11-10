"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ExternalLink } from "lucide-react";
import { emailMatches, type EmailMatch } from "@/lib/actions";
import { sourceLabel } from "@/lib/sources";

/** Under an email box: "already on another contact", with links that open in a new tab (Craig, feedback #17).
 * A warning only - shared addresses like info@ are real, so saving still works. */
export function EmailInUseWarning({ email, excludeId }: { email: string; excludeId?: string }) {
  const [matches, setMatches] = useState<EmailMatch[]>([]);

  useEffect(() => {
    const value = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      setMatches([]); // eslint-disable-line react-hooks/set-state-in-effect -- clearing stale matches
      return;
    }
    const id = setTimeout(() => {
      emailMatches(value, excludeId).then(setMatches).catch(() => setMatches([]));
    }, 350);
    return () => clearTimeout(id);
  }, [email, excludeId]);

  if (!matches.length) return null;
  return (
    <div role="status" className="mt-1 flex flex-col gap-1 rounded-md border border-[var(--warn)]/40 bg-[color-mix(in_oklab,var(--warn)_8%,transparent)] px-2.5 py-1.5 text-[11px]">
      <span className="flex items-center gap-1.5 font-semibold text-[var(--warn)]">
        <AlertTriangle className="size-3.5 shrink-0" />
        This email is already on {matches.length === 1 ? "another contact" : `${matches.length} other contacts`}
      </span>
      {matches.map((m) => (
        <Link key={m.id} href={`/contacts/${m.id}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-foreground hover:underline">
          <ExternalLink className="size-3 shrink-0 text-muted-foreground" />
          {m.name}
          <span className="text-muted-foreground">
            {m.company ? `· ${m.company} ` : ""}· {sourceLabel(m.source_db)}
          </span>
        </Link>
      ))}
      <span className="text-muted-foreground">Check it isn&apos;t the same person. If it&apos;s a shared address (e.g. info@), carry on.</span>
    </div>
  );
}
