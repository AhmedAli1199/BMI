import { backendFetch } from "@/lib/backend";
import type { WritingProfileState } from "@/lib/proposals-types";
import { SalesHeader } from "@/components/sales/sales-ui";
import { WritingProfile } from "@/components/sales/writing-profile";

/** "Teach the Brain how you write": the profile your drafted replies and new proposals follow. */
export default async function StylePage() {
  const st = await backendFetch<WritingProfileState>("/api/proposal-style");
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="How you write"
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Proposals", href: "/sales/proposals" }]}
        description="Show the Brain a few of your past proposals and it drafts your replies and proposals the way you write them: your order, your tone, your greeting and sign-off, and your prices for direct clients. Everyone's profile is their own."
      />
      <WritingProfile initial={st} />
    </div>
  );
}
