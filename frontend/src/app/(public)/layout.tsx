import Link from "next/link";
import { LEGAL } from "@/content/legal";

/** Public pages anyone can open without signing in: Privacy, Terms and Support (linked from the Zoom app's listing). */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="border-b border-border/70">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4">
          <Link href="/" className="text-base font-bold tracking-tight">{LEGAL.product}</Link>
          <nav className="flex gap-4 text-sm text-muted-foreground">
            <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
            <Link href="/terms" className="hover:text-foreground">Terms</Link>
            <Link href="/support" className="hover:text-foreground">Support</Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8 sm:py-12">{children}</main>
      <footer className="border-t border-border/70">
        <div className="mx-auto max-w-3xl px-4 py-6 text-xs text-muted-foreground">
          {LEGAL.product} is run by {LEGAL.owner} and built for them by {LEGAL.builder}. Questions: <a className="underline" href={`mailto:${LEGAL.supportEmail}`}>{LEGAL.supportEmail}</a>
        </div>
      </footer>
    </div>
  );
}
