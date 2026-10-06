export type FieldOp = { op: string; label: string };
export type ContactField = { key: string; label: string; group: string; kind: "text" | "bool" | "date" | "number"; ops: FieldOp[]; bulk: boolean; custom: boolean };
export type SearchCondition = { field: string; op: string; value: string };

/** Who a tool (copy emails, bulk update) should act on: ticked contacts, or a whole search. */
export type ContactScope = {
  ids?: string[];
  q?: string;
  source_db?: string;
  group_id?: string;
  company?: string;
  city?: string;
  country?: string;
  title?: string;
  conds?: string;
  match?: string;
  label?: string;
};

export type EmailsResult = {
  addresses: string[];
  text: string;
  contacts: number;
  skipped_unsubscribed: number;
  skipped_bounced: number;
  skipped_no_email: number;
  duplicates_removed: number;
};

export type BulkAction = "set" | "clear" | "replace";
export type BulkPreview = { field_label: string; total: number; will_change: number; unchanged: number; samples: { id: string; name: string | null; old: string | null; new: string | null }[] };
export type BulkEdit = {
  id: string; field_label: string; op: BulkAction; new_value: string | null; find_text: string | null; scope_label: string | null;
  total: number; changed: number; status: "applied" | "undone"; created_at: string; undone_at: string | null; by: string | null;
};

// ---- import ----
export type ImportTarget = { key: string; label: string; group: string };
export type ImportColumn = {
  index: number; header: string; samples: string[]; field: string; name: string | null; phone_type: string | null;
  suggested: string | null; level: "high" | "medium" | "ambiguous" | "none" | "empty" | "skip" | "manual"; confidence: number;
  reason: string; candidates: { field: string; label: string; score: number }[]; warning: string | null;
};
export type ImportOptions = {
  source_db: string | null;
  on_duplicate: "skip" | "fill_blanks" | "overwrite" | "create";
  create_companies: boolean;
  group_id: string | null;
  new_group_name: string | null;
};
export type ContactImport = {
  id: string; filename: string; kind: string; status: "mapping" | "imported" | "undone";
  sheets: { name: string; rows: number }[]; sheet_name: string | null; has_header: boolean; header_row: number;
  raw_top: string[][]; preview_rows: string[][]; row_count: number; columns: ImportColumn[]; options: ImportOptions;
  excluded: number[]; notes: string[]; ai_read: boolean; problems: string[]; matched: number;
  result: { created?: number; updated?: number; skipped?: number; unchanged?: number; totals?: Record<string, number> } | null;
  created_at: string; by: string | null;
};
export type ImportRowInfo = {
  n: number; name: string | null; email: string | null; company: string | null; phone: string | null;
  issues: { level: "error" | "warning"; text: string }[]; match: { id: string; name: string | null; kind: "email" | "name_company" | "possible" } | null;
  status: "new" | "update" | "skip_existing" | "skip_repeat" | "error" | "excluded";
};
export type ImportReview = { totals: Record<string, number>; rows: ImportRowInfo[]; total_rows: number; page: number; page_size: number; problems: string[] };
export type ImportListItem = { id: string; filename: string; status: string; row_count: number; created: number | null; updated: number | null; created_at: string; by: string | null };
