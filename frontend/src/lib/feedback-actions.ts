"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { FeedbackBoard, FeedbackItem, FeedbackKind, FeedbackPin, FeedbackStatus } from "@/lib/feedback-types";

const json = { "Content-Type": "application/json" };

export type BoardQuery = { status?: string; kind?: string; path?: string; mine?: boolean; q?: string; sort?: string; offset?: number };

function qs(q: Record<string, string | number | boolean | undefined | null>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) if (v !== undefined && v !== null && v !== "" && v !== false) p.set(k, String(v));
  return p.toString();
}

export async function listFeedback(q: BoardQuery = {}): Promise<FeedbackBoard> {
  return backendFetch<FeedbackBoard>(`/api/feedback?${qs(q)}`);
}

export async function similarFeedback(path: string, text: string): Promise<FeedbackItem[]> {
  return backendFetch<FeedbackItem[]>(`/api/feedback/similar?${qs({ path, q: text })}`);
}

export async function feedbackPins(path: string): Promise<FeedbackPin[]> {
  return backendFetch<FeedbackPin[]>(`/api/feedback/pins?${qs({ path })}`);
}

export async function getFeedback(id: string): Promise<FeedbackItem> {
  return backendFetch<FeedbackItem>(`/api/feedback/${id}`);
}

export async function toggleMeToo(id: string): Promise<FeedbackItem> {
  const r = await backendFetch<FeedbackItem>(`/api/feedback/${id}/me-too`, { method: "POST" });
  revalidatePath("/feedback");
  return r;
}

export async function commentOnFeedback(id: string, text: string): Promise<FeedbackItem> {
  const r = await backendFetch<FeedbackItem>(`/api/feedback/${id}/comments`, { method: "POST", headers: json, body: JSON.stringify({ text }) });
  revalidatePath("/feedback");
  return r;
}

export async function setFeedbackStatus(id: string, status: FeedbackStatus, note: string | null): Promise<FeedbackItem> {
  const r = await backendFetch<FeedbackItem>(`/api/feedback/${id}/status`, { method: "PUT", headers: json, body: JSON.stringify({ status, note }) });
  revalidatePath("/feedback");
  return r;
}

export async function editFeedback(id: string, patch: { kind?: FeedbackKind; message?: string }): Promise<FeedbackItem> {
  const r = await backendFetch<FeedbackItem>(`/api/feedback/${id}`, { method: "PUT", headers: json, body: JSON.stringify(patch) });
  revalidatePath("/feedback");
  return r;
}

export async function deleteFeedback(id: string): Promise<void> {
  await backendFetch(`/api/feedback/${id}`, { method: "DELETE" });
  revalidatePath("/feedback");
}

export async function retryFeedbackGithub(id: string): Promise<FeedbackItem> {
  return backendFetch<FeedbackItem>(`/api/feedback/${id}/github`, { method: "POST" });
}
