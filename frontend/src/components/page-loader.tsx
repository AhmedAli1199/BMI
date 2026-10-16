import { BrainBuddy } from "@/components/brain/brain-buddy";

/** The Brain thinking - the fallback for every (app) route's loading.tsx, so it's what shows during any navigation
 * whose page has to fetch data first. */
export function PageLoader() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-24" role="status">
      <BrainBuddy mood="thinking" size={84} />
      <p className="editorial-sub text-sm text-muted-foreground">Getting that ready&hellip;</p>
    </div>
  );
}
