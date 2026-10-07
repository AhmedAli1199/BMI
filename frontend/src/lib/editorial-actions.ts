"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { DeadlineRule, EditorialSettings, Feature, IssueDetail, Milestone, NextYearRow, RegularSection } from "@/lib/editorial-types";

const json = (body: unknown, method = "POST") => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const refresh = () => revalidatePath("/editorial", "layout");

export type IssueInput = {
  name?: string; kind?: string; format?: string | null; period_label?: string | null; edition_date?: string | null;
  editorial_deadline?: string | null; ad_deadline?: string | null; copy_deadline?: string | null; milestones?: Milestone[];
  theme?: string | null; distribution?: string | null; notes?: string | null; needs_check?: boolean;
};

export async function addIssue(input: IssueInput & { brand: string; title_id: string; year: number; name: string; use_rules?: boolean }): Promise<IssueDetail> {
  const r = await backendFetch<IssueDetail>("/api/editorial/issues", json(input));
  refresh();
  return r;
}

export async function editIssue(id: string, input: IssueInput): Promise<IssueDetail> {
  const r = await backendFetch<IssueDetail>(`/api/editorial/issues/${id}`, json(input, "PATCH"));
  refresh();
  return r;
}

export async function applyIssueRules(id: string): Promise<IssueDetail> {
  const r = await backendFetch<IssueDetail>(`/api/editorial/issues/${id}/apply-rules`, { method: "POST" });
  refresh();
  return r;
}

export async function deleteIssue(id: string): Promise<void> {
  await backendFetch(`/api/editorial/issues/${id}`, { method: "DELETE" });
  refresh();
}

export async function addFeature(issueId: string, input: { title: string; description?: string | null; sponsorable?: boolean; status?: string }): Promise<Feature> {
  const r = await backendFetch<Feature>(`/api/editorial/issues/${issueId}/features`, json(input));
  refresh();
  return r;
}

export async function editFeature(id: string, input: Partial<Pick<Feature, "title" | "description" | "status" | "sponsorable">>): Promise<Feature> {
  const r = await backendFetch<Feature>(`/api/editorial/features/${id}`, json(input, "PATCH"));
  refresh();
  return r;
}

export async function deleteFeature(id: string): Promise<void> {
  await backendFetch(`/api/editorial/features/${id}`, { method: "DELETE" });
  refresh();
}

export async function reorderFeatures(issueId: string, ids: string[]): Promise<void> {
  await backendFetch(`/api/editorial/issues/${issueId}/features/reorder`, json({ ids }));
  refresh();
}

export async function saveEditorialSettings(brand: string, input: { deadline_rules: DeadlineRule[]; regular_sections: RegularSection[]; about: string | null }): Promise<EditorialSettings> {
  const r = await backendFetch<EditorialSettings>(`/api/editorial/brands/${brand}/settings`, json(input, "PUT"));
  refresh();
  return r;
}

export async function loadPublishedPlan(brand: string, year: number): Promise<{ issues: number; features: number }> {
  const r = await backendFetch<{ issues: number; features: number }>(`/api/editorial/brands/${brand}/load-plan?year=${year}`, { method: "POST" });
  refresh();
  return r;
}

export async function previewPlanNextYear(brand: string, fromYear: number): Promise<NextYearRow[]> {
  return backendFetch<NextYearRow[]>("/api/editorial/next-year/preview", json({ brand, from_year: fromYear }));
}

export async function applyPlanNextYear(brand: string, fromYear: number, keepFeatures: boolean, skipIds: string[]): Promise<{ created: number; year: number }> {
  const r = await backendFetch<{ created: number; year: number }>("/api/editorial/next-year", json({ brand, from_year: fromYear, keep_features: keepFeatures, skip_ids: skipIds }));
  refresh();
  return r;
}
