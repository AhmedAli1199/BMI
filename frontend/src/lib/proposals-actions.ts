"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { Proposal, ProposalEmailDraft, ProposalLine, ProposalSection } from "@/lib/proposals-types";

const json = { "Content-Type": "application/json" };

function refresh(p: Proposal) {
  revalidatePath("/sales/proposals");
  revalidatePath(`/sales/proposals/${p.id}`);
  revalidatePath(`/companies/${p.company_id}`);
}

export async function createProposal(input: {
  company_id: string;
  contact_id?: string | null;
  title_id: string | null;
  template: string;
  campaign_name: string;
  year: number;
  lines: ProposalLine[];
}): Promise<Proposal> {
  const p = await backendFetch<Proposal>("/api/proposals", { method: "POST", headers: json, body: JSON.stringify(input) });
  refresh(p);
  return p;
}

export async function saveProposal(
  id: string,
  patch: { campaign_name?: string; template?: string; lines?: ProposalLine[]; sections?: ProposalSection[]; notes?: string | null }
): Promise<Proposal> {
  const p = await backendFetch<Proposal>(`/api/proposals/${id}`, { method: "PATCH", headers: json, body: JSON.stringify(patch) });
  refresh(p);
  return p;
}

export async function redraftProposal(id: string, useAi = true): Promise<Proposal> {
  const p = await backendFetch<Proposal>(`/api/proposals/${id}/redraft`, { method: "POST", headers: json, body: JSON.stringify({ use_ai: useAi }) });
  refresh(p);
  return p;
}

export async function finishProposal(id: string, via: "downloaded" | "other", followUpDays: number): Promise<Proposal> {
  const p = await backendFetch<Proposal>(`/api/proposals/${id}/finish`, {
    method: "POST",
    headers: json,
    body: JSON.stringify({ via, follow_up_days: followUpDays }),
  });
  refresh(p);
  return p;
}

export async function deleteProposal(id: string): Promise<void> {
  await backendFetch(`/api/proposals/${id}`, { method: "DELETE" });
  revalidatePath("/sales/proposals");
}

export async function getProposalEmailDraft(id: string): Promise<ProposalEmailDraft> {
  return backendFetch<ProposalEmailDraft>(`/api/proposals/${id}/email-draft`);
}

export async function sendProposal(
  id: string,
  input: { to: string[]; cc: string[]; subject: string; body: string; follow_up_days: number }
): Promise<Proposal> {
  const p = await backendFetch<Proposal>(`/api/proposals/${id}/send`, { method: "POST", headers: json, body: JSON.stringify(input) });
  refresh(p);
  return p;
}
