import Link from "next/link";
import { BrainBuddy } from "@/components/brain/brain-buddy";

/** Any address that doesn't exist (an old link, a typo, a record that's been deleted). */
export default function NotFound() {
  return (
    <div className="flex min-h-svh flex-1 flex-col items-center justify-center gap-3 bg-background p-4 text-center">
      <BrainBuddy mood="puzzled" size={110} />
      <h1 className="text-xl font-bold text-foreground">This page isn&apos;t here</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        The link may be old, or the record may have been removed. Check the address, or start again from the home page.
      </p>
      <Link href="/" className="mt-2 inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
        Go to the home page
      </Link>
    </div>
  );
}
