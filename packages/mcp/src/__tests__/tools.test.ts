import { describe, expect, it, vi } from "vitest";
import { TOOL_NAMES, tools, type ToolCtx } from "../tools";

function ctxWith(impl: ReturnType<typeof vi.fn>): ToolCtx {
  return { apiBase: "http://x", apiKey: "fbk_live_k", fetchImpl: impl as never };
}

const ok = (body: unknown) =>
  vi.fn(async () => ({ ok: true, json: async () => body }) as Response);

describe("mcp tools", () => {
  it("exposes the 7 contract tools", () => {
    expect(TOOL_NAMES.sort()).toEqual(
      [
        "capture_lesson",
        "get_feedback",
        "link_knowledge",
        "list_feedback",
        "search_knowledge",
        "submit_feedback",
        "update_status",
      ].sort(),
    );
  });

  it("submit_feedback POSTs to /api/feedback with app key", async () => {
    const f = ok({ id: "fb1" });
    const r = await tools.submit_feedback(ctxWith(f), { system: "FPS", message: "x" });
    expect(r).toEqual({ id: "fb1" });
    const [url, opts] = f.mock.calls[0];
    expect(url).toBe("http://x/api/feedback");
    expect(opts.method).toBe("POST");
    expect(opts.headers["X-App-Key"]).toBe("fbk_live_k");
  });

  it("update_status PATCHes the right path", async () => {
    const f = ok({ ok: true });
    await tools.update_status(ctxWith(f), { id: "fb1", status: "triaged" });
    expect(f.mock.calls[0][0]).toBe("http://x/api/feedback/fb1");
    expect(f.mock.calls[0][1].method).toBe("PATCH");
  });

  it("throws on non-ok response", async () => {
    const f = vi.fn(async () => ({ ok: false, status: 500 }) as Response);
    await expect(tools.get_feedback(ctxWith(f), { id: "z" })).rejects.toThrow("500");
  });
});
