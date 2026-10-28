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
  /** The pitch drafted from this call (SALES-023), if one was made. */
  pitch_proposal_id?: string | null;
  /** Linked to a company (or a contact at one), so a pitch knows who it's for. */
  can_pitch?: boolean;
  created_at: string;
  summary: string | null;
  notes?: CallNotes | null;
  transcript?: CallUtterance[];
};

export const PLATFORM_LABEL: Record<string, string> = { google_meet: "Google Meet", teams: "Microsoft Teams", zoom: "Zoom" };
export const LIVE_STATUSES = ["scheduled", "joining", "waiting_room", "recording", "processing"];

export type CalendarConnectionInfo = { provider: "google" | "microsoft"; email: string; status: string; last_error: string | null; last_synced_at: string | null };
export type CalendarSetup = {
  connections: CalendarConnectionInfo[];
  google_available: boolean;
  microsoft_available: boolean;
  notetaker_available: boolean;
  preference: "auto" | "remind" | "off";
  /** Zoom lets the notetaker in only on behalf of a signed-in person in the call - each person connects theirs once. */
  zoom: { available: boolean; connected: boolean; status: "connected" | "error" | null; last_error: string | null; connected_at: string | null };
};
export type SharedMeeting = {
  id: string;
  start_at: string;
  end_at: string;
  is_all_day: boolean;
  status: string;
  mine: boolean;
  my_response: string | null;
  private: boolean;
  title: string;
  platform: string | null;
  join_url: string | null;
  organizer?: string | null;
  bmi_people: { name: string; response: string }[];
  outside_people: { name: string; email: string }[];
  decision: { record: boolean; reason: string };
  /** What actually happened (past meetings) or will happen (upcoming), in plain words. */
  outcome: { tone: "ok" | "warn" | "bad" | "muted" | "live"; text: string };
  override: "record" | "skip" | null;
  last_error?: string | null;
  call: { id: string; status: string; status_label: string } | null;
  contact: { id: string; name: string | null } | null;
  company: { id: string; name: string } | null;
};

export type NotetakerHealth = {
  checks: { label: string; ok: boolean; text: string }[];
  missed: { title: string; start_at: string; text: string }[];
  missed_count: number;
};
