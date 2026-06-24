// Widget controller (Step 14-17). Framework-agnostic core so the open/capture/
// local-only/submit logic is unit-testable without React.
//
// Invariants enforced + tested:
//   - capture() runs BEFORE the panel opens (else the panel is in the screenshot)
//   - attachments stay LOCAL until submit() — no network on open/paste/cancel
//   - cancel() drops everything without uploading (privacy, §7.2/CL6)

import { captureScreenshot, type CaptureOptions } from "./capture";
import { AuthExpiredError, FeedbackApi, type SubmitPayload } from "./api";

export interface LocalAttachment {
  blob: Blob;
  kind: "screenshot" | "image";
  annotated: boolean;
}

export type WidgetStatus = "closed" | "open" | "sending" | "sent" | "auth_expired";

export class WidgetController {
  status: WidgetStatus = "closed";
  message = "";
  attachments: LocalAttachment[] = [];

  constructor(
    private api: FeedbackApi,
    private captureOpts: CaptureOptions = {},
    private capture: typeof captureScreenshot = captureScreenshot,
  ) {}

  // Capture FIRST (panel not yet shown), then open.
  async open(): Promise<void> {
    const blob = await this.capture(this.captureOpts);
    if (blob) {
      this.attachments.push({ blob, kind: "screenshot", annotated: false });
    }
    this.status = "open";
  }

  addImage(blob: Blob): void {
    this.attachments.push({ blob, kind: "image", annotated: false });
  }

  markAnnotated(index: number): void {
    if (this.attachments[index]) this.attachments[index].annotated = true;
  }

  removeAttachment(index: number): void {
    this.attachments.splice(index, 1);
  }

  // Cancel = drop local state, never upload.
  cancel(): void {
    this.attachments = [];
    this.message = "";
    this.status = "closed";
  }

  // Upload each blob, THEN submit feedback with the resulting ids.
  async submit(extra: Partial<SubmitPayload> = {}): Promise<{ id: string }> {
    if (!this.message.trim()) throw new Error("message required");
    this.status = "sending";
    try {
      const ids: string[] = [];
      for (const a of this.attachments) {
        ids.push(await this.api.uploadAttachment(a.blob));
      }
      const result = await this.api.submitFeedback({
        message: this.message,
        attachmentIds: ids,
        pageUrl: typeof location !== "undefined" ? location.href : undefined,
        context: this.collectContext(),
        ...extra,
      });
      this.status = "sent";
      return result;
    } catch (e) {
      if (e instanceof AuthExpiredError) this.status = "auth_expired";
      else this.status = "open";
      throw e;
    }
  }

  private collectContext(): Record<string, unknown> {
    return {
      app_version: (globalThis as Record<string, unknown>).__APP_VERSION__ ?? "unknown",
      browser: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
    };
  }
}
