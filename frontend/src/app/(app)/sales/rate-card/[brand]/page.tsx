import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { BrandPage } from "@/lib/rate-card-types";
import { BrandRateCard } from "@/components/rate-card/brand-rate-card";

export default async function BrandRateCardPage({ params, searchParams }: { params: Promise<{ brand: string }>; searchParams: Promise<{ year?: string }> }) {
  const { brand } = await params;
  const sp = await searchParams;
  const data = await backendFetch<BrandPage>(`/api/rate-card/brands/${encodeURIComponent(brand)}${sp.year ? `?year=${Number(sp.year)}` : ""}`).catch(() => null);
  if (!data) notFound();
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <BrandRateCard data={data} />
    </div>
  );
}
