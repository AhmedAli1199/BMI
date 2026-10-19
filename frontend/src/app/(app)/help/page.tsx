import { PageHeader } from "@/components/page-header";
import { HelpHome } from "@/components/help/help-home";

export const metadata = { title: "Help Centre" };

export default function HelpPage() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader section="Help" title="Help Centre" description="How to do things in BMI Brain, step by step." />
      <HelpHome />
    </div>
  );
}
