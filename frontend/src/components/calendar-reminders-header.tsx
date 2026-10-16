import { hiddenSections } from "@/lib/hidden-sections";
import { PageHeader } from "@/components/page-header";
import { PageTabs } from "@/components/page-tabs";

/** One place for "what's coming up": the shared calendar and to-dos, and your own reminders, as two tabs of
 * Calendar & Reminders (sidebar). Each tab is its own page, so links to either still work; a tab is left out when an
 * administrator has hidden that section for the person. `actions` sit on the right (search, Log or schedule). */
export async function CalendarRemindersHeader({ active, actions }: { active: "calendar" | "reminders"; actions?: React.ReactNode }) {
  const hidden = await hiddenSections();
  const tabs = [
    { key: "calendar", label: "Calendar & tasks", href: "/activities", show: !hidden.includes("calendar") },
    { key: "reminders", label: "Reminders", href: "/reminders", show: !hidden.includes("reminders") },
  ].filter((t) => t.show || t.key === active);
  return (
    <>
      <PageHeader
        section="Everyday"
        title="Calendar & Reminders"
        description={active === "calendar"
          ? "Calls, meetings and to-dos across your contacts and companies - yours and the team's."
          : <>Set one from any contact or company with <strong>Remind me</strong>. When it&apos;s due you get a notification under the bell - and an email, if you asked for one.</>}
        actions={actions}
      />
      <PageTabs label="Calendar and reminders" tabs={tabs.map((t) => ({ label: t.label, href: t.href, active: t.key === active }))} />
    </>
  );
}
