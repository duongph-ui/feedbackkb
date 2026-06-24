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

// Add the Stop-hook into .claude/settings.json (idempotent).
export function initHook(dir: string): void {
  const path = join(dir, ".claude", "settings.json");
  const cfg = existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : {};
  cfg.hooks = cfg.hooks ?? {};
  const stop = (cfg.hooks.Stop ?? []) as Array<{ command?: string }>;
  if (!stop.some((h) => h.command?.includes("capture-lesson"))) {
    stop.push({ command: "feedbackkb-capture-lesson" });
  }
  cfg.hooks.Stop = stop;
  mkdirSync(join(dir, ".claude"), { recursive: true });
  writeFileSync(path, JSON.stringify(cfg, null, 2));
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
