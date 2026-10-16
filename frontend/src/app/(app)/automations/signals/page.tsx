import { PageHeader } from "@/components/page-header";
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
      <PageHeader
        title="Email signals"
        crumbs={[{ label: "Automations Hub", href: "/automations" }]}
        description={`${rows.length} ${rows.length === 1 ? "thing" : "things"} the Brain has picked out of client emails so far, such as budgets, renewal dates and promised call-backs, with how sure it was of each.`}
      />

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
