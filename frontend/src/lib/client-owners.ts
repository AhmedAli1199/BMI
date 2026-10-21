"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";

/** Who looks after a client on each magazine (backend app/sales/ownership.py). */
export type ClientOwner = {
  area: string; magazine: string; rep_id: string | null; rep_name: string | null; rep_user_id: string | null;
  rule: string; rule_label: string; reason: string; chosen: boolean; fixed: boolean; regions: string[];
};
export type ClientOwners = { owners: ClientOwner[]; can_change: boolean; people: { id: string; name: string }[] };

export async function getClientOwners(companyId: string): Promise<ClientOwners> {
  return backendFetch<ClientOwners>(`/api/companies/${companyId}/owners`);
}

export async function changeClientOwner(companyId: string, area: string, body: { rep_id: string | null; back_to_rules?: boolean }): Promise<ClientOwners> {
  const out = await backendFetch<ClientOwners>(`/api/companies/${companyId}/owners/${area}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  revalidatePath(`/companies/${companyId}`);
  return out;
}
