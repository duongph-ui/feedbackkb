// REST client (Step 17). Uploads attachments then submits feedback. Auth via
// app-host JWT (Bearer) or X-App-Key. fetch is injectable for tests.

export interface ApiConfig {
  apiBase: string;
  system: string;
  getJwt?: () => string | null; // app-host session token
  appKey?: string; // anonymous fallback
  fetchImpl?: typeof fetch;
}

export interface SubmitPayload {
  message: string;
  attachmentIds: string[];
  pageUrl?: string;
  context?: Record<string, unknown>;
  captchaToken?: string;
}

export class AuthExpiredError extends Error {}

export class FeedbackApi {
  constructor(private cfg: ApiConfig) {}

  private get fetch() {
    return this.cfg.fetchImpl ?? fetch;
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    const h: Record<string, string> = { ...extra };
    const jwt = this.cfg.getJwt?.();
    if (jwt) h["Authorization"] = `Bearer ${jwt}`;
    else if (this.cfg.appKey) h["X-App-Key"] = this.cfg.appKey;
    return h;
  }

  async uploadAttachment(blob: Blob): Promise<string> {
    const form = new FormData();
    form.append("file", blob, "screenshot.png");
    const res = await this.fetch(`${this.cfg.apiBase}/api/feedback/attachment`, {
      method: "POST",
      headers: this.headers(),
      body: form,
    });
    if (res.status === 401) throw new AuthExpiredError();
    if (!res.ok) throw new Error(`attachment upload failed: ${res.status}`);
    return (await res.json()).attachment_id as string;
  }

  async submitFeedback(p: SubmitPayload): Promise<{ id: string }> {
    const res = await this.fetch(`${this.cfg.apiBase}/api/feedback`, {
      method: "POST",
      headers: this.headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        system: this.cfg.system,
        message: p.message,
        attachment_ids: p.attachmentIds,
        page_url: p.pageUrl,
        context: p.context,
        captcha_token: p.captchaToken,
      }),
    });
    if (res.status === 401) throw new AuthExpiredError();
    if (res.status === 422) throw new Error("validation: message required");
    if (!res.ok) throw new Error(`submit failed: ${res.status}`);
    return res.json();
  }
}
