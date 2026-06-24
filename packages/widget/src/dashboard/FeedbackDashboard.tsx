// Dashboard (Step 19 / W2). Read-only list with system/status filter + expandable
// detail row. Fetches GET /api/feedback (admin JWT).

import { useEffect, useMemo, useState } from "react";
import { applyFilter, type FeedbackRow, type Filters } from "./filter";

export interface DashboardProps {
  apiBase: string;
  getJwt: () => string | null;
  fetchImpl?: typeof fetch;
}

export function FeedbackDashboard(props: DashboardProps) {
  const [rows, setRows] = useState<FeedbackRow[]>([]);
  const [filters, setFilters] = useState<Filters>({ system: "all", status: "all" });
  const [expanded, setExpanded] = useState<string | null>(null);
  const doFetch = props.fetchImpl ?? fetch;

  useEffect(() => {
    doFetch(`${props.apiBase}/api/feedback?limit=100`, {
      headers: { Authorization: `Bearer ${props.getJwt()}` },
    })
      .then((r) => r.json())
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch(() => setRows([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shown = useMemo(() => applyFilter(rows, filters), [rows, filters]);

  return (
    <div data-testid="fbk-dash">
      <select
        data-testid="filter-system"
        value={filters.system}
        onChange={(e) => setFilters({ ...filters, system: e.target.value })}
      >
        <option value="all">all</option>
        {[...new Set(rows.map((r) => r.system))].map((s) => (
          <option key={s}>{s}</option>
        ))}
      </select>
      <select
        data-testid="filter-status"
        value={filters.status}
        onChange={(e) => setFilters({ ...filters, status: e.target.value })}
      >
        <option value="all">all</option>
        {[...new Set(rows.map((r) => r.status))].map((s) => (
          <option key={s}>{s}</option>
        ))}
      </select>
      <table>
        <tbody>
          {shown.map((r) => (
            <tr key={r.id} data-testid="row" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>
              <td>{r.severity ?? "—"}</td>
              <td>{r.system}</td>
              <td>{r.status}</td>
              <td>{r.message}</td>
              {expanded === r.id && <td data-testid="detail">{r.id}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
