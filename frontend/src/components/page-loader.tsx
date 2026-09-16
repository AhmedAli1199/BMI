/** Two counter-rotating rings around a static center dot - reads as
 * "working", not just spinning, and matches the app's editorial-serif
 * voice for the caption. Used as the fallback for every (app) route's
 * loading.tsx, so it's what shows during any navigation whose
 * destination page has to fetch data first. */
export function PageLoader() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-24">
      <div className="relative size-14">
        <div className="absolute inset-0 rounded-full border-[3px] border-primary/15" />
        <div className="absolute inset-0 animate-spin rounded-full border-[3px] border-transparent border-t-primary border-r-primary" />
        <div
          className="absolute inset-[7px] animate-spin rounded-full border-[2.5px] border-transparent border-b-primary/60"
          style={{ animationDirection: "reverse", animationDuration: "1.3s" }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="size-1.5 rounded-full bg-primary/70" />
        </div>
      </div>
      <p className="editorial-sub text-sm text-muted-foreground">Loading&hellip;</p>
    </div>
  );
}
