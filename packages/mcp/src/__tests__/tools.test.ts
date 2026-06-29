import { describe, expect, it, vi } from "vitest";
import { TOOL_NAMES, tools, type ToolCtx } from "../tools";

function ctxWith(impl: ReturnType<typeof vi.fn>): ToolCtx {
  return { apiBase: "http://x", apiKey: "fbk_live_k", fetchImpl: impl as never };
}

const ok = (body: unknown) =>
  vi.fn(async () => ({ ok: true, json: async () => body }) as Response);

describe("mcp tools", () => {
  it("exposes the 8 contract tools", () => {
    expect(TOOL_NAMES.sort()).toEqual(
      [
        "capture_lesson",
        "get_attachment_image",
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

  it("get_attachment_image returns base64 image content", async () => {
    const bytes = new Uint8Array([1, 2, 3, 4]);
    const f = vi.fn(async () => ({
      ok: true,
      headers: { get: (k: string) => (k.toLowerCase() === "content-type" ? "image/png" : null) },
      arrayBuffer: async () => bytes.buffer,
    }) as unknown as Response);
    const r = await tools.get_attachment_image(ctxWith(f), { attachment_id: "att1" });
    expect(f.mock.calls[0][0]).toBe("http://x/api/feedback/attachment/att1/content");
    expect(r).toEqual({ __type: "image", mimeType: "image/png", data: Buffer.from(bytes).toString("base64") });
  });
});
