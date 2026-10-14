import { HubHeader } from "@/components/automations/hub-ui";
import { FeedbackBoardView } from "@/components/feedback/feedback-board";
import { listFeedback } from "@/lib/feedback-actions";
import type { FeedbackBoard } from "@/lib/feedback-types";

export default async function FeedbackPage({ searchParams }: { searchParams: Promise<{ open?: string }> }) {
  const sp = await searchParams;
  const initial = await listFeedback({ status: "open" }).catch(() => null as FeedbackBoard | null);
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <HubHeader
        title="Feedback"
        description="Everything people have said while trying BMI Brain: what's broken, what's confusing and what they'd like. Add your vote with Me too instead of sending the same thing again. Use the Feedback button on any page to add more."
      />
      <FeedbackBoardView initial={initial} openId={sp.open ?? null} />
    </div>
  );
}
