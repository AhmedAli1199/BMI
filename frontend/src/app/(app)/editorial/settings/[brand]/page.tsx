import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { EditorialSettings, Planner } from "@/lib/editorial-types";
import { BrandSettingsForm } from "@/components/editorial/brand-settings-form";

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
      <BrandSettingsForm settings={settings} brandName={b.name} canEdit={b.can_edit} />
    </div>
  );
}
