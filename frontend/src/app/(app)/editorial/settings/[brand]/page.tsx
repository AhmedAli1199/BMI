import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { EditorialSettings, Planner } from "@/lib/editorial-types";
import { BrandSettingsForm } from "@/components/editorial/brand-settings-form";
import { PageHeader } from "@/components/page-header";
import { brandColor } from "@/components/rate-card/brand-style";

export default async function EditorialSettingsPage({ params }: { params: Promise<{ brand: string }> }) {
  const { brand } = await params;
  const [settings, plan] = await Promise.all([
    backendFetch<EditorialSettings>(`/api/editorial/brands/${encodeURIComponent(brand)}/settings`).catch(() => null),
    backendFetch<Planner>("/api/editorial/planner"),
  ]);
  const b = plan.brands.find((x) => x.key === brand);
  if (!settings || !b) notFound();
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-5 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title={`${b.name} settings`}
        crumbs={[{ label: "Editorial plan", href: `/editorial?brand=${settings.brand}` }]}
        below={<span className="masthead-rule block w-16" style={{ background: brandColor(settings.brand) }} aria-hidden="true" />}
        description="Tell the Brain how this brand's deadlines usually work. When you add an issue with a publication date, its deadlines are filled in for you, and you can always change them on the issue."
      />
      <BrandSettingsForm settings={settings} canEdit={b.can_edit} />
    </div>
  );
}
