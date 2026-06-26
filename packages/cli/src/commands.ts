// CLI command cores (Step 21b). File-mutating ops are pure + idempotent so they
// unit-test against a temp dir. `register`/`sync` hit the REST API (fetch
// injectable).

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const ROUTING_MARKER = "## FeedbackKB routing";

export async function register(
  apiBase: string,
  adminJwt: string,
  body: { code: string; name: string; repo?: string },
  fetchImpl: typeof fetch = fetch,
): Promise<{ app_key: string }> {
  const res = await fetchImpl(`${apiBase}/api/admin/register`, {
    method: "POST",
    headers: { Authorization: `Bearer ${adminJwt}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`register failed: ${res.status}`);
  return (await res.json()) as { app_key: string };
}

// Write/merge the mcpServers.feedbackkb block into .mcp.json (idempotent).
export function initMcp(dir: string, apiBase: string, appKey: string): void {
  const path = join(dir, ".mcp.json");
  const cfg = existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : {};
  cfg.mcpServers = cfg.mcpServers ?? {};
  cfg.mcpServers.feedbackkb = {
    command: "npx",
    args: ["feedbackkb-mcp"],
    env: { FEEDBACKKB_API: apiBase, FEEDBACKKB_KEY: appKey },
  };
  writeFileSync(path, JSON.stringify(cfg, null, 2));
}

// Wire BOTH knowledge-loop hooks into .claude/settings.json (idempotent).
//   UserPromptSubmit → hook-presearch : ép search_knowledge TRƯỚC khi fix.
//   Stop             → hook-capture   : ép /capture-fix SAU khi fix.
// Uses the standard Claude Code hook schema { Event: [{ hooks: [{type,command}] }] }.
const PRESEARCH_CMD = "npx feedbackkb hook-presearch";
const CAPTURE_CMD = "npx feedbackkb hook-capture";

type HookEntry = { type?: string; command?: string };
type HookGroup = { matcher?: string; hooks?: HookEntry[] };

function ensureHook(cfg: Record<string, unknown>, event: string, command: string): void {
  const hooks = (cfg.hooks ?? {}) as Record<string, HookGroup[]>;
  const groups = (hooks[event] ?? []) as HookGroup[];
  const present = groups.some((g) => (g.hooks ?? []).some((h) => h.command === command));
  if (!present) groups.push({ hooks: [{ type: "command", command }] });
  hooks[event] = groups;
  cfg.hooks = hooks;
}

export function initHook(dir: string): void {
  const path = join(dir, ".claude", "settings.json");
  const cfg = existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : {};
  // Migrate the old broken placeholder (`feedbackkb-capture-lesson`, no such bin).
  const legacyStop = (cfg.hooks?.Stop ?? []) as HookEntry[];
  if (Array.isArray(legacyStop) && legacyStop.some((h) => h.command === "feedbackkb-capture-lesson")) {
    cfg.hooks.Stop = legacyStop.filter((h) => h.command !== "feedbackkb-capture-lesson");
  }
  ensureHook(cfg, "UserPromptSubmit", PRESEARCH_CMD);
  ensureHook(cfg, "Stop", CAPTURE_CMD);
  mkdirSync(join(dir, ".claude"), { recursive: true });
  writeFileSync(path, JSON.stringify(cfg, null, 2));
}

// ── Hook cores (pure + testable; CLI subcommands read stdin and call these) ──

// Fix/bug intent in a user prompt (vi + en). Broad on purpose — a false positive
// only injects a reminder; a false negative silently skips the knowledge search.
const FIX_INTENT =
  /\b(bug|fix|fixed|fixing|error|crash|fail|failing|broken|exception|stack ?trace|traceback|regression|debug)\b|lỗi|sửa|sai|hỏng|chạy không|không chạy|báo lỗi|vỡ|fix lại/i;

// UserPromptSubmit core. Returns the directive to inject, or null to stay silent.
export function presearch(input: { prompt?: string }): string | null {
  const prompt = input.prompt ?? "";
  if (!FIX_INTENT.test(prompt)) return null;
  return [
    "## FeedbackKB — BẮT BUỘC trước khi sửa",
    "Prompt này có ý định fix/debug. TRƯỚC KHI sửa code, PHẢI gọi tool",
    '`search_knowledge("<triệu chứng lỗi>", system="<CODE hệ thống>")` để tra lesson cũ.',
    "Nếu có lesson liên quan → áp dụng. Nếu không có kết quả → nói rõ rồi tiếp tục.",
    "Không bỏ qua bước search này.",
  ].join("\n");
}

// Stop core. `gitStatus` = output of `git status --porcelain` (empty = clean tree).
// Returns a block decision once per fix, or null to allow the session to stop.
export function captureGate(
  input: { stop_hook_active?: boolean },
  gitStatus: string,
): { decision: "block"; reason: string } | null {
  if (input.stop_hook_active) return null; // already re-prompted once → avoid loop
  if (!gitStatus.trim()) return null; // no code change this session → nothing to capture
  return {
    decision: "block",
    reason:
      "Phiên này có thay đổi code. Nếu là fix thật → chạy /capture-fix để ghi lesson " +
      "(symptom/root cause/fix/file:line/prevention) vào knowledge trung tâm TRƯỚC khi kết thúc. " +
      "Nếu không phải fix (refactor/docs/format) → bỏ qua và kết thúc bình thường.",
  };
}

// Batch-sync feedback from an existing system (Step 36 / B2). Reads rows the
// caller supplies (from their view/export) and forwards each with external_id so
// re-runs are idempotent (UNIQUE(system, external_system, external_id)).
export async function sync(
  apiBase: string,
  appKey: string,
  rows: Array<{ external_id: string; message: string; external_system: string }>,
  system: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ sent: number }> {
  let sent = 0;
  for (const r of rows) {
    const res = await fetchImpl(`${apiBase}/api/feedback`, {
      method: "POST",
      headers: { "X-App-Key": appKey, "Content-Type": "application/json" },
      body: JSON.stringify({
        system,
        message: r.message,
        source: "sync",
        external_system: r.external_system,
        external_id: r.external_id,
      }),
    });
    if (res.ok) sent += 1;
  }
  return { sent };
}

// Append the F-17 routing rule to CLAUDE.md (idempotent — once only).
export function initRules(dir: string): boolean {
  const path = join(dir, "CLAUDE.md");
  const current = existsSync(path) ? readFileSync(path, "utf8") : "";
  if (current.includes(ROUTING_MARKER)) return false;
  const block = `\n${ROUTING_MARKER}\n\n- Before debugging, run \`search_knowledge\` for prior lessons.\n- After a real fix, run \`/capture-fix\` to record the lesson.\n`;
  writeFileSync(path, current + block);
  return true;
}
