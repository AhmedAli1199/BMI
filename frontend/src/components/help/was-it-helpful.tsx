"use client";

import Link from "next/link";
import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AskTheBrain } from "@/components/help/ask-the-brain";

/** "Was this helpful?" at the end of an article. (Pilot: answers aren't saved yet - see docs/help-centre-plan.md.) */
export function WasItHelpful({ title }: { title: string }) {
  const [said, setSaid] = useState<"yes" | "no" | null>(null);
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card px-5 py-4 sm:flex-row sm:items-center">
      {said === null && (
        <>
          <span className="flex-1 text-sm font-medium">Was this article helpful?</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setSaid("yes")}><ThumbsUp className="size-3.5" /> Yes</Button>
            <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setSaid("no")}><ThumbsDown className="size-3.5" /> Not really</Button>
          </div>
        </>
      )}
      {said === "yes" && <span className="text-sm">Thanks - glad it helped.</span>}
      {said === "no" && (
        <>
          <span className="flex-1 text-sm">Sorry about that. Ask the Brain, or tell the team what was missing so we can improve it.</span>
          <div className="flex gap-2">
            <AskTheBrain question={`I read "${title}" but I'm still stuck: `} />
            <Button size="sm" variant="outline" nativeButton={false} render={<Link href="/feedback" />}>Tell the team</Button>
          </div>
        </>
      )}
    </div>
  );
}
