import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { IssueDetail, PitchList } from "@/lib/editorial-types";
import { IssuePage } from "@/components/editorial/issue-page";

export default async function EditorialIssuePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [issue, pitch] = await Promise.all([
    backendFetch<IssueDetail>(`/api/editorial/issues/${id}`).catch(() => null),
    backendFetch<PitchList>(`/api/editorial/issues/${id}/pitch`).catch(() => null),
  ]);
  if (!issue) notFound();
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 sm:p-6 lg:p-8">
      <IssuePage key={`${issue.id}-${issue.edition_date}-${issue.needs_check}`} issue={issue} pitch={pitch} />
    </div>
  );
}
