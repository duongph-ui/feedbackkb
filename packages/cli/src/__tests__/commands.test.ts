import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { captureGate, initHook, initMcp, initRules, presearch, register, sync } from "../commands";

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

  it("init-hook wires UserPromptSubmit + Stop idempotently (standard schema)", () => {
    const d = tmp();
    initHook(d);
    initHook(d); // second run must not duplicate
    const cfg = JSON.parse(readFileSync(join(d, ".claude", "settings.json"), "utf8"));
    const cmds = (groups: Array<{ hooks?: Array<{ command?: string }> }>) =>
      groups.flatMap((g) => (g.hooks ?? []).map((h) => h.command));
    expect(cmds(cfg.hooks.UserPromptSubmit).filter((c: string) => c.includes("hook-presearch"))).toHaveLength(1);
    expect(cmds(cfg.hooks.Stop).filter((c: string) => c.includes("hook-capture"))).toHaveLength(1);
  });

  it("init-hook migrates the old broken capture-lesson placeholder", () => {
    const d = tmp();
    mkdirSync(join(d, ".claude"), { recursive: true });
    writeFileSync(
      join(d, ".claude", "settings.json"),
      JSON.stringify({ hooks: { Stop: [{ command: "feedbackkb-capture-lesson" }] } }),
    );
    initHook(d);
    const cfg = JSON.parse(readFileSync(join(d, ".claude", "settings.json"), "utf8"));
    const stopCmds = (cfg.hooks.Stop as Array<{ command?: string; hooks?: Array<{ command?: string }> }>)
      .flatMap((g) => (g.hooks ? g.hooks.map((h) => h.command) : [g.command]));
    expect(stopCmds).not.toContain("feedbackkb-capture-lesson");
    expect(stopCmds.some((c) => c?.includes("hook-capture"))).toBe(true);
  });

  it("presearch injects directive on fix intent, silent otherwise", () => {
    expect(presearch({ prompt: "sửa lỗi báo lỗi 500 khi submit" })).toContain("search_knowledge");
    expect(presearch({ prompt: "fix the crash on login" })).toContain("search_knowledge");
    expect(presearch({ prompt: "thêm cột mới vào bảng report" })).toBeNull();
    expect(presearch({})).toBeNull();
  });

  it("captureGate blocks on dirty tree, allows when clean or already re-prompted", () => {
    expect(captureGate({}, " M src/a.ts\n")?.decision).toBe("block");
    expect(captureGate({}, "")).toBeNull();
    expect(captureGate({ stop_hook_active: true }, " M src/a.ts\n")).toBeNull();
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
