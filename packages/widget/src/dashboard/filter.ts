// Dashboard filter logic (Step 19). Pure -> unit-testable without React.

export interface FeedbackRow {
  id: string;
  system: string;
  type?: string | null;
  severity?: string | null;
  message: string;
  status: string;
  created_at?: string;
}

export interface Filters {
  system?: string; // "all" | code
  status?: string; // "all" | status
}

export function applyFilter(rows: FeedbackRow[], f: Filters): FeedbackRow[] {
  return rows.filter(
    (r) =>
      (!f.system || f.system === "all" || r.system === f.system) &&
      (!f.status || f.status === "all" || r.status === f.status),
  );
}
