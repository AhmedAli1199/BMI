import { PageHeader } from "@/components/page-header";
import { StaffOnly } from "@/components/automations/hub-ui";
import { backendFetch } from "@/lib/backend";
import { canUseAutomations } from "@/lib/access";
import { getSession } from "@/lib/session";

// A read-only check on what the email exchange summary scan (email_summary.py) has picked out of client
// emails. Not in the menu or the Hub on purpose - it's an occasional "is the scan reading emails sensibly?"
// look for administrators and data managers (the Automations Hub help guide points to it).

/** What each kind of fact is called on screen. */
const SIGNAL_LABELS: Record<string, string> = {
  budget_window: "Budget timing",
  renewal_date: "Renewal date",
  promised_callback: "Promised call-back",
  personal_touchpoint: "Personal moment",
  decline: "Said no",
};
const STATUS_LABELS: Record<string, string> = { open: "Waiting", actioned: "Acted on", dismissed: "Dismissed" };

function words(code: string, labels: Record<string, string>): string {
  const known = labels[code];
  if (known) return known;
  const tidy = code.replace(/[_-]+/g, " ").trim();
  return tidy ? tidy.charAt(0).toUpperCase() + tidy.slice(1) : "-";
}
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
  const session = await getSession();
  if (!canUseAutomations(session)) return <StaffOnly />;

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
                <td className="px-3 py-2">{words(r.signal_type, SIGNAL_LABELS)}</td>
                <td className="px-3 py-2">{r.due_date ?? "-"}</td>
                <td className="max-w-md px-3 py-2 text-muted-foreground">{r.summary}</td>
                <td className="px-3 py-2">{Math.round(r.confidence * 100)}%</td>
                <td className="px-3 py-2">{words(r.status, STATUS_LABELS)}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {new Date(r.created_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
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
