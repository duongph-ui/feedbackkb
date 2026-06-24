#!/usr/bin/env node
// feedbackkb CLI (Step 21b).
import { Command } from "commander";
import { initHook, initMcp, initRules, register } from "./commands.js";

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
  console.log("added Stop-hook to .claude/settings.json");
});

program.command("init-rules").action(() => {
  const added = initRules(process.cwd());
  console.log(added ? "added FeedbackKB routing to CLAUDE.md" : "CLAUDE.md already has rules");
});

program.parseAsync();
