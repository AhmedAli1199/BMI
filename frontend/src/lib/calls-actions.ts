"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { Call, NotetakerHealth } from "@/lib/calls-types";

const json = { "Content-Type": "application/json" };

export async function sendNotetaker(input: { meeting_url: string; title?: string | null; contact_id?: string | null; company_id?: string | null }) {
  const c = await backendFetch<Call>("/api/calls", { method: "POST", headers: json, body: JSON.stringify(input) });
  revalidatePath("/calls");
  return c;
}

export async function getCall(id: string) {
  return backendFetch<Call>(`/api/calls/${id}`);
}

export async function stopNotetaker(id: string) {
  const c = await backendFetch<Call>(`/api/calls/${id}/stop`, { method: "POST" });
  revalidatePath(`/calls/${id}`);
  return c;
}

export async function linkCall(id: string, patch: { contact_id?: string | null; company_id?: string | null; title?: string | null }) {
  const c = await backendFetch<Call>(`/api/calls/${id}`, { method: "PATCH", headers: json, body: JSON.stringify(patch) });
  revalidatePath(`/calls/${id}`);
  return c;
}

export async function saveCallToHistory(id: string) {
  const c = await backendFetch<Call>(`/api/calls/${id}/save-to-history`, { method: "POST" });
  revalidatePath(`/calls/${id}`);
  if (c.contact) revalidatePath(`/contacts/${c.contact.id}`);
  return c;
}

/** SALES-023: a proposal draft that answers what the client said on the call. */
export async function makePitchFromCall(id: string) {
  const r = await backendFetch<{ proposal_id: string; href: string }>(`/api/calls/${id}/pitch`, { method: "POST" });
  revalidatePath(`/calls/${id}`);
  revalidatePath("/sales/proposals");
  return r;
}

export async function setMeetingChoice(id: string, choice: "record" | "skip" | null) {
  const m = await backendFetch(`/api/calendar/meetings/${id}/override`, { method: "POST", headers: json, body: JSON.stringify({ choice }) });
  revalidatePath("/calls/meetings");
  return m;
}

export async function setRecordingPreference(mode: "auto" | "remind" | "off") {
  await backendFetch(`/api/calendar/preference`, { method: "PUT", headers: json, body: JSON.stringify({ mode }) });
  revalidatePath("/calls/meetings");
}

export async function disconnectCalendar(provider: "google" | "microsoft") {
  await backendFetch(`/api/calendar/connections/${provider}`, { method: "DELETE" });
  revalidatePath("/calls/meetings");
}

export async function disconnectZoom() {
  await backendFetch(`/api/zoom/connection`, { method: "DELETE" });
  revalidatePath("/calls/meetings");
}

export async function syncCalendarsNow() {
  const r = await backendFetch<{ booked: number; called_off: number }>(`/api/calendar/sync`, { method: "POST" });
  revalidatePath("/calls/meetings");
  return r;
}

export async function getNotetakerHealth() {
  return backendFetch<NotetakerHealth>(`/api/calendar/health`);
}

export async function startCalendarOver() {
  const r = await backendFetch<{ meetings: number; bots_called_off: number; calls_removed: number; booked: number }>(`/api/calendar/start-over`, { method: "POST" });
  revalidatePath("/calls/meetings");
  revalidatePath("/calls");
  return r;
}
