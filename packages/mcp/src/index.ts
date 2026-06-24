#!/usr/bin/env node
// feedbackkb-mcp entry (Step 21a). Registers the 7 tools on an MCP stdio server.
// Config via env: FEEDBACKKB_API, FEEDBACKKB_KEY.

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { TOOL_NAMES, tools, type ToolCtx, type ToolName } from "./tools.js";

const ctx: ToolCtx = {
  apiBase: process.env.FEEDBACKKB_API ?? "http://localhost:8000",
  apiKey: process.env.FEEDBACKKB_KEY ?? "",
};

const server = new Server(
  { name: "feedbackkb-mcp", version: "0.0.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOL_NAMES.map((name) => ({
    name,
    description: `FeedbackKB: ${name}`,
    inputSchema: { type: "object", additionalProperties: true },
  })),
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const name = req.params.name as ToolName;
  const fn = tools[name];
  if (!fn) throw new Error(`unknown tool ${name}`);
  const result = await fn(ctx, (req.params.arguments ?? {}) as never);
  return { content: [{ type: "text", text: JSON.stringify(result) }] };
});

await server.connect(new StdioServerTransport());
