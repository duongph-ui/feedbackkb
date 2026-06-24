import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { initHook, initMcp, initRules, register, sync } from "../commands";

function tmp(): string {
  return mkdtempSync(join(tmpdir(), "fbk-cli-"));
}

describe("cli commands", () => {
  it("register POSTs to admin/register and returns app_key", async () => {
    const f = vi.fn(async () => ({ ok: true, json: async () => ({ app_key: "fbk_live_x" }) }) as Response);
    const r = await register("http://x", "jwt", { code: "FPS", name: "Pay" }, f as never);
    expect(r.app_key).toBe("fbk_live_x");
    expect(f.mock.calls[0][0]).toBe("http://x/api/admin/register");
  });

  it("init-mcp writes mcpServers.feedbackkb block", () => {
    const d = tmp();
    initMcp(d, "http://api", "fbk_live_k");
    const cfg = JSON.parse(readFileSync(join(d, ".mcp.json"), "utf8"));
    expect(cfg.mcpServers.feedbackkb.env.FEEDBACKKB_KEY).toBe("fbk_live_k");
  });

  it("init-hook adds a Stop hook idempotently", () => {
    const d = tmp();
    initHook(d);
    initHook(d); // second run must not duplicate
    const cfg = JSON.parse(readFileSync(join(d, ".claude", "settings.json"), "utf8"));
    expect(cfg.hooks.Stop.filter((h: { command: string }) => h.command.includes("capture-lesson"))).toHaveLength(1);
  });

  it("sync forwards each row with external_id (source=sync)", async () => {
    const f = vi.fn(async () => ({ ok: true, json: async () => ({ id: "x" }) }) as Response);
    const r = await sync(
      "http://x", "fbk_live_k",
      [{ external_id: "1", message: "a", external_system: "old" }],
      "FPS", f as never,
    );
    expect(r.sent).toBe(1);
    const body = JSON.parse(f.mock.calls[0][1].body as string);
    expect(body.source).toBe("sync");
    expect(body.external_id).toBe("1");
  });

  it("init-rules appends once (idempotent)", () => {
    const d = tmp();
    expect(initRules(d)).toBe(true);
    expect(initRules(d)).toBe(false); // already present
    const md = readFileSync(join(d, "CLAUDE.md"), "utf8");
    expect(md).toContain("search_knowledge");
    expect(md.match(/## FeedbackKB routing/g)).toHaveLength(1);
  });
});
