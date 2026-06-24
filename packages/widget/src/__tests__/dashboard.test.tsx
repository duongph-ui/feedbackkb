import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { applyFilter, type FeedbackRow } from "../dashboard/filter";
import { FeedbackDashboard } from "../dashboard/FeedbackDashboard";

const rows: FeedbackRow[] = [
  { id: "1", system: "FPS", status: "new", message: "a", severity: "crit" },
  { id: "2", system: "FPA", status: "resolved", message: "b" },
  { id: "3", system: "FPS", status: "triaged", message: "c" },
];

describe("dashboard filter", () => {
  it("filters by system", () => {
    expect(applyFilter(rows, { system: "FPS" }).map((r) => r.id)).toEqual(["1", "3"]);
  });
  it("filters by status", () => {
    expect(applyFilter(rows, { status: "resolved" }).map((r) => r.id)).toEqual(["2"]);
  });
  it("all = no filter", () => {
    expect(applyFilter(rows, { system: "all", status: "all" })).toHaveLength(3);
  });
});

describe("FeedbackDashboard render", () => {
  it("renders rows from the API", async () => {
    const fetchImpl = vi.fn(async () => ({ json: async () => rows }) as Response);
    render(
      <FeedbackDashboard apiBase="http://x" getJwt={() => "jwt"} fetchImpl={fetchImpl as never} />,
    );
    expect(await screen.findAllByTestId("row")).toHaveLength(3);
    expect(fetchImpl).toHaveBeenCalledOnce();
  });
});
