import Link from "next/link";
import { BarChart3 } from "lucide-react";
import { getSession } from "@/lib/session";
import { HubHeader } from "@/components/automations/hub-ui";
import { Button } from "@/components/ui/button";
import { BrainPage } from "@/components/brain/brain-page";

/** The assistant on its own page: your conversations on the left, the chat on the right. */
export default async function Page({ searchParams }: { searchParams: Promise<{ c?: string }> }) {
  const [session, sp] = await Promise.all([getSession(), searchParams]);
  return (
    <div className="mx-auto flex h-full w-full max-w-6xl flex-col gap-4 p-4 sm:p-6 lg:p-8">
      <HubHeader title="Ask AI"
        description="Ask how anything in BMI Brain works, or why a booking is the way it is. It knows the Sales Orders area inside out and can look at a real booking to explain it."
        actions={session?.role === "admin" ? (
          <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href="/brain/activity" />}><BarChart3 className="size-3.5" /> What it&apos;s been asked</Button>
        ) : null} />
      <BrainPage initial={sp.c ?? null} userName={session?.name} />
    </div>
  );
}
