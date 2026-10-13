export type CallActionItem = { task: string; owner?: string | null; due?: string | null };
export type CallNotes = {
  title: string;
  summary: string;
  key_points: string[];
  decisions: string[];
  action_items: CallActionItem[];
  money_mentioned: string[];
  dates_mentioned: string[];
  next_step: string | null;
  sentiment: "positive" | "neutral" | "negative" | string;
};
export type CallUtterance = { speaker: string; start_ms: number; end_ms: number; text: string };
export type Call = {
  id: string;
  title: string | null;
  meeting_url: string;
  platform: string | null;
  status: string;
  status_label: string;
  status_detail: string | null;
  participants: string[];
  contact: { id: string; name: string | null } | null;
  company: { id: string; name: string } | null;
  owner: string | null;
  started_at: string | null;
  ended_at: string | null;
  saved_to_history_at: string | null;
  created_at: string;
  summary: string | null;
  notes?: CallNotes | null;
  transcript?: CallUtterance[];
};

export const PLATFORM_LABEL: Record<string, string> = { google_meet: "Google Meet", teams: "Microsoft Teams", zoom: "Zoom" };
export const LIVE_STATUSES = ["scheduled", "joining", "waiting_room", "recording", "processing"];
