#!/usr/bin/env node
// feedbackkb CLI (Step 21b).
import { readFileSync } from "node:fs";
import { execSync } from "node:child_process";
import { Command } from "commander";
import {
  captureGate, initHook, initMcp, initRules, presearch, register, sync,
} from "./commands.js";

// Read all of stdin (hook payload from Claude Code), parse JSON, tolerate empty.
async function readStdinJson(): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const c of process.stdin) chunks.push(c as Buffer);
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return {};
  }
}

const program = new Command();
program.name("feedbackkb").description("FeedbackKB setup CLI").version("0.0.0");

program
  .command("register")
  .requiredOption("--system <code>")
  .requiredOption("--name <name>")
  .option("--repo <url>")
  .option("--api <url>", "API base", process.env.FEEDBACKKB_API ?? "http://localhost:8000")
  .option("--jwt <token>", "admin JWT", process.env.FEEDBACKKB_ADMIN_JWT ?? "")
  .action(async (o) => {
    const r = await register(o.api, o.jwt, { code: o.system, name: o.name, repo: o.repo });
    console.log(`app_key (store in vault, shown once): ${r.app_key}`);
  });

program
  .command("init-mcp")
  .requiredOption("--key <appKey>")
  .option("--api <url>", "API base", process.env.FEEDBACKKB_API ?? "http://localhost:8000")
  .action((o) => {
    initMcp(process.cwd(), o.api, o.key);
    console.log("wrote .mcp.json");
  });

program.command("init-hook").action(() => {
  initHook(process.cwd());
  console.log("wired UserPromptSubmit (hook-presearch) + Stop (hook-capture) into .claude/settings.json");
});

// UserPromptSubmit hook: inject the "search_knowledge first" directive on fix intent.
program.command("hook-presearch").action(async () => {
  const directive = presearch(await readStdinJson());
  if (directive) process.stdout.write(directive);
  process.exit(0);
});

// Stop hook: block once to force /capture-fix when the session changed code.
program.command("hook-capture").action(async () => {
  const input = await readStdinJson();
  let status = "";
  try {
    status = execSync("git status --porcelain", { encoding: "utf8" });
  } catch {
    status = ""; // not a git repo → nothing to gate on
  }
  const decision = captureGate(input as { stop_hook_active?: boolean }, status);
  if (decision) process.stdout.write(JSON.stringify(decision));
  process.exit(0);
});

program.command("init-rules").action(() => {
  const added = initRules(process.cwd());
  console.log(added ? "added FeedbackKB routing to CLAUDE.md" : "CLAUDE.md already has rules");
});

program
  .command("sync")
  .description("batch-forward existing feedback rows (idempotent via external_id)")
  .requiredOption("--system <code>")
  .requiredOption("--key <appKey>")
  .requiredOption("--file <path>", "JSON array of { external_id, message, external_system }")
  .option("--api <url>", "API base", process.env.FEEDBACKKB_API ?? "http://localhost:8000")
  .action(async (o) => {
    const rows = JSON.parse(readFileSync(o.file, "utf8")) as Array<{
      external_id: string;
      message: string;
      external_system: string;
    }>;
    const r = await sync(o.api, o.key, rows, o.system);
    console.log(`synced ${r.sent}/${rows.length} (duplicates skipped server-side)`);
  });

program.parseAsync();
