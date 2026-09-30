import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { backendFetch } from "@/lib/backend";

// THROWAWAY page - quick visibility into what email_summary.py's scan has
// actually extracted, so it can be judged on real output before
// SALES-012/013 get built on top of it. Delete this file (and the matching
// GET /api/automations/email-signals route) once that decision's made.
type EmailSignalRow = {
  id: string;
  contact_name: string;
  signal_type: string;
  due_date: string | null;
  summary: string;
  confidence: number;
  status: string;
  created_at: string;
};

export default async function EmailSignalsPage() {
  const rows = await backendFetch<EmailSignalRow[]>("/api/automations/email-signals");

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 sm:p-6 lg:p-8">
      <div>
        <Link
          href="/automations"
          className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Automations
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Email signals (temporary viewer)
        </h1>
        <p className="mt-1 text-xs text-muted-foreground">
          {rows.length} signal{rows.length === 1 ? "" : "s"} extracted so far. Throwaway page - just
          for judging extraction quality before SALES-012/013 get built.
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-muted/50 text-[11px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Contact</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Due date</th>
              <th className="px-3 py-2">Summary</th>
              <th className="px-3 py-2">Confidence</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="px-3 py-2 font-medium text-foreground">{r.contact_name}</td>
                <td className="px-3 py-2">{r.signal_type}</td>
                <td className="px-3 py-2">{r.due_date ?? "-"}</td>
                <td className="max-w-md px-3 py-2 text-muted-foreground">{r.summary}</td>
                <td className="px-3 py-2">{Math.round(r.confidence * 100)}%</td>
                <td className="px-3 py-2">{r.status}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {new Date(r.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-muted-foreground">
                  Nothing extracted yet - run the email exchange summary scan and check back.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
