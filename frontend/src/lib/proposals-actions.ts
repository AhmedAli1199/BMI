"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { Proposal, ProposalEmailDraft, ProposalLine, ProposalSection, UpcomingIssue } from "@/lib/proposals-types";

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
  edition_id?: string | null;
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
  patch: { campaign_name?: string; template?: string; edition_id?: string | null; lines?: ProposalLine[]; sections?: ProposalSection[]; notes?: string | null }
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

/** A title's issues from today on, for the issue picker (`include` keeps a proposal's current one in the list). */
export async function getUpcomingIssues(titleId: string, include?: string | null): Promise<UpcomingIssue[]> {
  const q = new URLSearchParams({ title_id: titleId });
  if (include) q.set("include", include);
  return backendFetch<UpcomingIssue[]>(`/api/editorial/upcoming?${q}`);
}

/** Applies the salesperson's own instruction to the whole proposal; returns what changed and the previous version (for Undo). */
export async function reviseProposal(id: string, instruction: string, sections: ProposalSection[]): Promise<{ proposal: Proposal; summary: string; previous_sections: ProposalSection[] }> {
  const r = await backendFetch<{ proposal: Proposal; summary: string; previous_sections: ProposalSection[] }>(`/api/proposals/${id}/revise`, {
    method: "POST", headers: json, body: JSON.stringify({ instruction, sections }),
  });
  refresh(r.proposal);
  return r;
}
