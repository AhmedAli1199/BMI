import type { AddressOut } from "@/lib/types";

/** Renders one address the way Act!'s own contact screen laid it out -
 * Address 1/2, City, County, Postcode, Country each their own line -
 * instead of one comma-joined string. "County" here is Act!'s STATE
 * column; UK Act! installs use it for county, not US state. */
export function AddressBlock({ address }: { address: AddressOut }) {
  const fields: Array<[string, string | null]> = [
    ["Address", address.line1],
    ["", address.line2],
    ["", address.line3],
    ["City", address.city],
    ["County", address.state],
    ["Postcode", address.postal_code],
    ["Country", address.country],
  ].filter(([, value]) => Boolean(value)) as Array<[string, string | null]>;

  if (fields.length === 0) return null;

  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-sm">
      {fields.map(([label, value], i) => (
        <div key={i} className="contents">
          <dt className="text-muted-foreground">{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
