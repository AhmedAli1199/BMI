import { PageHeader } from "@/components/page-header";
import { StaffOnly } from "@/components/automations/hub-ui";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { isAdmin } from "@/lib/access";
import { friendlyError } from "@/lib/errors";
import { CopyBrevoLists, type BrevoList } from "./copy-lists";

/** TEMPORARY (29 Oct 2026): BMI's Brevo lists, to copy once so each magazine's newsletter list can be set. Delete this
 * folder and backend/app/api/routes/brevo_lists.py once that's done. */
export default async function BrevoListsPage() {
  const session = await getSession();
  if (!isAdmin(session)) return <StaffOnly />;
  let lists: BrevoList[] = [];
  let problem = "";
  try {
    lists = await backendFetch<BrevoList[]>("/api/brevo/lists");
  } catch (e) {
    problem = friendlyError(e, "Brevo's lists couldn't be loaded just now. Please try again in a minute.");
  }
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        crumbs={[{ label: "Automations Hub", href: "/automations" }, { label: "Automation settings", href: "/automations/settings?area=brevo" }]}
        title="Brevo lists"
        description="Every contact list in BMI's Brevo account. Press Copy all and send the result to the developer, so each magazine's newsletter list can be set up. This page is only here for now."
      />
      {problem ? (
        <p className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">{problem}</p>
      ) : (
        <CopyBrevoLists lists={lists} />
      )}
    </div>
  );
}
