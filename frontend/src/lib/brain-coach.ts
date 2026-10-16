"use server";

import { backendFetch } from "@/lib/backend";

export type CoachTip = { id: string; text: string; mood: "happy" | "pointing"; action?: string; link?: string; show?: string; forever?: boolean };
export type CoachState = { tips: boolean; celebrations: boolean; tours_done: string[]; tip: CoachTip | null };

const json = { "Content-Type": "application/json" };

export async function coachState(path: string) {
  return backendFetch<CoachState>(`/api/brain/coach?path=${encodeURIComponent(path)}`);
}

export async function dismissTip(tipId: string, forever = false) {
  await backendFetch("/api/brain/coach/dismiss", { method: "POST", headers: json, body: JSON.stringify({ tip_id: tipId, forever }) });
}

export async function setTourDone(tour: string, done = true) {
  await backendFetch("/api/brain/coach/tour", { method: "POST", headers: json, body: JSON.stringify({ tour, done }) });
}
