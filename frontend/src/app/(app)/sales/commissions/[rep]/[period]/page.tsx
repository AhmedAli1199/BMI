import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { CommissionStatement } from "@/lib/commission-types";
import { StatementView } from "@/components/commission/statement-view";

export default async function StatementPage({ params }: { params: Promise<{ rep: string; period: string }> }) {
  const { rep, period } = await params;
  if (!/^\d{4}-\d{2}$/.test(period)) notFound();
  const s = await backendFetch<CommissionStatement>(`/api/commission/statement?rep_id=${rep}&period=${period}`).catch(() => null);
  if (!s) notFound();
  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <StatementView key={`${rep}-${period}-${s.approved?.at ?? ""}`} s={s} />
    </div>
  );
}
