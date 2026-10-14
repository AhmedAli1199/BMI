import { backendFetch } from "@/lib/backend";
import type { ExampleLibrary } from "@/lib/proposals-types";
import { SalesHeader } from "@/components/sales/sales-ui";
import { ExamplesLibrary } from "@/components/sales/examples-library";

/** Links to past pages and resources that anyone can drop into a proposal, one library per brand. */
export default async function ExamplesPage({ searchParams }: { searchParams: Promise<{ brand?: string }> }) {
  const { brand = "tbtm" } = await searchParams;
  const lib = await backendFetch<ExampleLibrary>(`/api/proposal-examples?brand=${encodeURIComponent(brand)}&include_archived=true`)
    .catch((): ExampleLibrary => ({ items: [], sectors: {}, formats: [], brands: [] }));
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Examples library"
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Proposals", href: "/sales/proposals" }]}
        description="Links to past pages that show what each format looks like, and resources like the media pack. Everyone on the brand shares them, and the Examples block in a proposal picks from here, the client's sector first."
      />
      <ExamplesLibrary lib={lib} brand={brand} />
    </div>
  );
}
