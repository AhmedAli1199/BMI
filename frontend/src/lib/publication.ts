import { cookies } from "next/headers";

/** The single source of truth for "which publication's data am I looking
 * at" - set from the header PublicationSwitcher (or any page's own quick
 * filter) via setPublicationFilter (lib/actions.ts), read here by every
 * page that lists or aggregates data. A cookie, not a URL search param, on
 * purpose: a query string resets the moment you navigate to a different
 * route, which was the actual bug being fixed (picking a title on the
 * dashboard "jumped to Contacts" and picking one on Contacts didn't carry
 * over to Companies or Groups). Empty string means "All titles".
 */
export const PUBLICATION_COOKIE = "pub_source_db";

export async function getPublicationFilter(): Promise<string> {
  const store = await cookies();
  return store.get(PUBLICATION_COOKIE)?.value || "";
}
