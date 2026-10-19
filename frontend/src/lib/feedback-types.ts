export type FeedbackKind = "broken" | "confusing" | "idea" | "looks_wrong";
export type FeedbackStatus = "new" | "looking" | "fixed" | "wont_do";

export const FEEDBACK_KINDS: { kind: FeedbackKind; label: string; hint: string }[] = [
  { kind: "broken", label: "Something's broken", hint: "A button, page or number isn't working" },
  { kind: "confusing", label: "I don't understand this", hint: "It isn't clear what something does" },
  { kind: "idea", label: "I wish it could…", hint: "An idea or something missing" },
  { kind: "looks_wrong", label: "Looks wrong", hint: "Layout, words or colours look off" },
];

export const FEEDBACK_STATUSES: { status: FeedbackStatus; label: string }[] = [
  { status: "new", label: "New" },
  { status: "looking", label: "Looking at it" },
  { status: "fixed", label: "Fixed" },
  { status: "wont_do", label: "Won't do" },
];

/** Something on the page the person pointed at. */
export type FeedbackElement = {
  label: string;
  role?: string;
  text?: string;
  selector?: string;
  path?: string;
  heading?: string;
  /** Where it's made in the code ("components/deals/deal-form.tsx:389"), nearest first. */
  source?: string[];
  rect?: { x: number; y: number; w: number; h: number };
  viewport?: { w: number; h: number };
};

export type FeedbackComment = { id: string; user_id: string; name: string; text: string; at: string };

export type FeedbackItem = {
  id: string; number: number; kind: FeedbackKind; kind_label: string; message: string;
  page_path: string; page_title: string | null; user_name: string; user_role: string | null; mine: boolean;
  elements: FeedbackElement[]; status: FeedbackStatus; status_label: string; status_note: string | null; status_by: string | null; status_at: string | null;
  me_too: string[]; me_too_mine: boolean; comment_count: number; created_at: string | null; updated_at: string | null;
  github_url: string | null; images: { id: string; label: string | null; width: number | null; height: number | null }[];
  can_edit: boolean; can_set_status: boolean; can_delete: boolean;
  comments?: FeedbackComment[];
  context?: { browser?: string; viewport?: string; screen?: string; zoom?: string; theme?: string; time_zone?: string; errors?: { at: string; kind: string; message: string }[] };
  github_error?: string | null;
};

export type FeedbackBoard = {
  items: FeedbackItem[]; total: number; counts: Record<FeedbackStatus, number>;
  pages: { path: string; title: string | null; count: number }[]; github: boolean; can_manage: boolean;
};

export type FeedbackPin = {
  id: string; number: number; kind: FeedbackKind; kind_label: string; message: string; user_name: string; status: FeedbackStatus; me_too: number;
  /** You sent it - so there's no "Me too" for you. */
  mine: boolean; me_too_mine: boolean;
  elements: Pick<FeedbackElement, "label" | "selector" | "rect" | "viewport">[];
};

export const feedbackImageUrl = (id: string) => `/api/files/feedback/images/${id}`;
