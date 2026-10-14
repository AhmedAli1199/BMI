"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { ExampleLibrary, Proposal, WritingProfileData, WritingProfileState, ProposalBlock, ProposalEmailDraft, ProposalExample, ProposalLine, ProposalSection, UpcomingIssue } from "@/lib/proposals-types";

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
  kind?: string;
  discount_pct?: number;
}): Promise<Proposal> {
  const p = await backendFetch<Proposal>("/api/proposals", { method: "POST", headers: json, body: JSON.stringify(input) });
  refresh(p);
  return p;
}

export async function saveProposal(
  id: string,
  patch: { campaign_name?: string; template?: string; edition_id?: string | null; lines?: ProposalLine[]; sections?: ProposalSection[]; notes?: string | null; kind?: string; discount_pct?: number; output?: "word" | "email" }
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
  input: { to: string[]; cc: string[]; subject: string; body: string; follow_up_days: number; as_body?: boolean; attach_word?: boolean }
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

/** The proposal exactly as it goes out (blocks filled in), and anything that may not show well in an email. */
export async function previewProposal(id: string): Promise<{ html: string; warnings: string[] }> {
  return backendFetch(`/api/proposals/${id}/preview`);
}

export async function previewBlock(id: string, block: ProposalBlock): Promise<string> {
  const r = await backendFetch<{ html: string }>(`/api/proposals/${id}/block-preview`, { method: "POST", headers: json, body: JSON.stringify(block) });
  return r.html;
}

export async function getExampleLibrary(brand: string, includeArchived = false): Promise<ExampleLibrary> {
  return backendFetch<ExampleLibrary>(`/api/proposal-examples?brand=${encodeURIComponent(brand)}${includeArchived ? "&include_archived=true" : ""}`);
}

export async function saveExample(id: string | null, input: Omit<ProposalExample, "id" | "link_ok" | "checked_at" | "use_count">): Promise<ProposalExample> {
  const r = await backendFetch<ProposalExample>(id ? `/api/proposal-examples/${id}` : "/api/proposal-examples", {
    method: id ? "PUT" : "POST", headers: json, body: JSON.stringify(input),
  });
  revalidatePath("/sales/proposals/examples");
  return r;
}

export async function checkExampleLinks(brand: string): Promise<void> {
  await backendFetch(`/api/proposal-examples/check?brand=${encodeURIComponent(brand)}`, { method: "POST" });
}

// ---- your writing profile ------------------------------------------------------------------------------

const styleRefresh = () => revalidatePath("/sales/proposals/style");

export async function pasteStyleSample(name: string, text: string): Promise<WritingProfileState> {
  const r = await backendFetch<WritingProfileState>("/api/proposal-style/samples/paste", { method: "POST", headers: json, body: JSON.stringify({ name, text }) });
  styleRefresh();
  return r;
}

export async function deleteStyleSample(id: string): Promise<WritingProfileState> {
  const r = await backendFetch<WritingProfileState>(`/api/proposal-style/samples/${id}`, { method: "DELETE" });
  styleRefresh();
  return r;
}

export async function findStyleSamplesInSent(): Promise<WritingProfileState> {
  const r = await backendFetch<WritingProfileState>("/api/proposal-style/find-sent", { method: "POST" });
  styleRefresh();
  return r;
}

export async function saveStyleNotes(notes: string): Promise<WritingProfileState> {
  return backendFetch<WritingProfileState>("/api/proposal-style/notes", { method: "PUT", headers: json, body: JSON.stringify({ notes }) });
}

export async function buildStyleProfile(): Promise<WritingProfileState> {
  return backendFetch<WritingProfileState>("/api/proposal-style/build", { method: "POST" });
}

export async function saveStyleProfile(profile: WritingProfileData): Promise<WritingProfileState> {
  const r = await backendFetch<WritingProfileState>("/api/proposal-style", { method: "PUT", headers: json, body: JSON.stringify({ profile }) });
  styleRefresh();
  return r;
}

export async function resetStyleProfile(): Promise<WritingProfileState> {
  const r = await backendFetch<WritingProfileState>("/api/proposal-style/reset", { method: "POST" });
  styleRefresh();
  return r;
}

export async function setLearned(key: string, active: boolean): Promise<WritingProfileState> {
  const r = await backendFetch<WritingProfileState>(`/api/proposal-style/learned/${encodeURIComponent(key)}`, { method: "PUT", headers: json, body: JSON.stringify({ active }) });
  styleRefresh();
  return r;
}
