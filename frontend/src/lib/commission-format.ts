export const pctLabel = (r: number | null | undefined) => (r == null ? "-" : `${(r * 100).toLocaleString("en-GB", { maximumFractionDigits: 2 })}%`);

export const monthLabel = (period: string, short = false) => {
  const [y, m] = period.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString("en-GB", { month: short ? "short" : "long", year: short ? undefined : "numeric", timeZone: "UTC" });
};
