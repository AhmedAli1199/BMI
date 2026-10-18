import type { FeedbackElement } from "@/lib/feedback-types";

/** What the assistant is told about the screen the question was asked from. */
export type BrainContext = {
  page_path?: string;
  page_title?: string;
  mode?: "chat" | "ask" | "card";
  record?: { kind: string; id: string; label?: string };
  elements?: FeedbackElement[];
  errors?: { message: string }[];
};

/** Something the Brain offered to do (Phase 4) - a card the person confirms; nothing happens before that. */
export type BrainAction = {
  id: string;
  kind: string;
  title: string;
  lines: [string, string][];
  links: { label: string; href: string }[];
  confirm: string;
  status: "pending" | "done" | "cancelled" | "failed" | "expired";
  result: { text?: string; links?: { label: string; href: string }[] };
  expires_at: string | null;
};

export type BrainMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  context: {
    suggestions?: string[]; show?: string[]; links?: { label: string; href: string }[];
    actions?: BrainAction[]; action_results?: BrainAction[]; error?: boolean;
  } & BrainContext;
  rating: 1 | -1 | null;
  feedback_id: string | null;
  created_at: string | null;
  images: { id: string; label: string | null }[];
};

export type BrainConversationSummary = { id: string; title: string; started_on: string | null; updated_at: string | null };
export type BrainConversation = { id: string; title: string; messages: BrainMessage[] };
export type BrainSuggestions = { configured: boolean; questions: string[]; guide: string | null };

export type BrainActivity = {
  items: {
    id: string; at: string; who: string; question: string; page: string | null; answer: string; rating: 1 | -1 | null;
    feedback_id: string | null; route: string | null; steps: string[]; ms: number | null;
    input_tokens: number | null; cached_tokens: number | null; output_tokens: number | null; problem: boolean;
  }[];
  index?: { chunks: number; embedded: number; meaning_search: boolean; last_indexed: string | null };
  summary: { answers: number; helpful: number; not_helpful: number; avg_seconds: number | null; cache_hit_pct: number | null };
};
