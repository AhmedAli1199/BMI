"use server";

import { backendFetch } from "@/lib/backend";
import type { BrainActivity, BrainConversation, BrainConversationSummary, BrainSuggestions } from "@/lib/brain-types";

const json = { "Content-Type": "application/json" };

export async function brainConversations() {
  return (await backendFetch<{ conversations: BrainConversationSummary[] }>("/api/brain/conversations")).conversations;
}

export async function brainConversation(id: string) {
  return backendFetch<BrainConversation>(`/api/brain/conversations/${id}`);
}

export async function renameBrainConversation(id: string, title: string) {
  return backendFetch(`/api/brain/conversations/${id}`, { method: "PATCH", headers: json, body: JSON.stringify({ title }) });
}

export async function deleteBrainConversation(id: string) {
  await backendFetch(`/api/brain/conversations/${id}`, { method: "DELETE" });
}

export async function rateBrainAnswer(id: string, rating: 1 | -1 | null) {
  return backendFetch<{ id: string; rating: 1 | -1 | null }>(`/api/brain/messages/${id}/rating`, { method: "POST", headers: json, body: JSON.stringify({ rating }) });
}

export async function brainAnswerToFeedback(id: string, note?: string) {
  return backendFetch<{ feedback_id: string; number: number }>(`/api/brain/messages/${id}/feedback`, { method: "POST", headers: json, body: JSON.stringify({ note }) });
}

export async function brainSuggestions(page: string) {
  return backendFetch<BrainSuggestions>(`/api/brain/suggestions?page=${encodeURIComponent(page)}`);
}

export async function brainActivity(days = 14) {
  return backendFetch<BrainActivity>(`/api/brain/activity?days=${days}`);
}
