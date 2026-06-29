// FeedbackKB MCP tool implementations (Step 21a). Thin wrappers over the REST API
// (§3.4.1). Pure functions with injectable fetch so the tool<->REST mapping is
// unit-testable without an MCP runtime.

export interface ToolCtx {
  apiBase: string;
  apiKey: string;
  fetchImpl?: typeof fetch;
}

function headers(ctx: ToolCtx, json = false): Record<string, string> {
  const h: Record<string, string> = { "X-App-Key": ctx.apiKey };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

async function call(ctx: ToolCtx, method: string, path: string, body?: unknown) {
  const f = ctx.fetchImpl ?? fetch;
  const res = await f(`${ctx.apiBase}${path}`, {
    method,
    headers: headers(ctx, body !== undefined),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}`);
  return res.json();
}

// Image result sentinel — index.ts maps this to an MCP `image` content block so a
// vision-capable agent actually SEES the screenshot (not just a URL it can't open).
export interface ImageResult {
  __type: "image";
  mimeType: string;
  data: string; // base64
}

async function callBinary(ctx: ToolCtx, path: string): Promise<ImageResult> {
  const f = ctx.fetchImpl ?? fetch;
  const res = await f(`${ctx.apiBase}${path}`, { method: "GET", headers: headers(ctx) });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  const mimeType = res.headers.get("content-type") || "application/octet-stream";
  const buf = Buffer.from(await res.arrayBuffer());
  return { __type: "image", mimeType, data: buf.toString("base64") };
}

export const tools = {
  submit_feedback: (ctx: ToolCtx, a: { system: string; message: string; attachment_ids?: string[] }) =>
    call(ctx, "POST", "/api/feedback", a),

  list_feedback: (ctx: ToolCtx, a: { system?: string; status?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (a.system) q.set("system", a.system);
    if (a.status) q.set("status", a.status);
    if (a.limit) q.set("limit", String(a.limit));
    return call(ctx, "GET", `/api/feedback?${q.toString()}`);
  },

  get_feedback: (ctx: ToolCtx, a: { id: string }) => call(ctx, "GET", `/api/feedback/${a.id}`),

  // Fetch a submitted screenshot as image content (vision). Attachment ids come
  // from get_feedback's `attachments[]`. ACL enforced server-side by tenant.
  get_attachment_image: (ctx: ToolCtx, a: { attachment_id: string }) =>
    callBinary(ctx, `/api/feedback/attachment/${a.attachment_id}/content`),

  update_status: (ctx: ToolCtx, a: { id: string; status: string; comment?: string }) =>
    call(ctx, "PATCH", `/api/feedback/${a.id}`, { status: a.status, comment: a.comment }),

  search_knowledge: (ctx: ToolCtx, a: { query: string; system?: string }) => {
    const q = new URLSearchParams({ query: a.query });
    if (a.system) q.set("system", a.system);
    return call(ctx, "GET", `/api/knowledge/search?${q.toString()}`);
  },

  capture_lesson: (
    ctx: ToolCtx,
    a: { system: string; category: string; symptom: string; root_cause: string; fix: string; files?: string; prevent: string },
  ) => call(ctx, "POST", "/api/knowledge/capture", a),

  link_knowledge: (ctx: ToolCtx, a: { feedback_id: string; store_ref: string }) =>
    call(ctx, "POST", "/api/knowledge/link", a),
};

export type ToolName = keyof typeof tools;
export const TOOL_NAMES = Object.keys(tools) as ToolName[];
