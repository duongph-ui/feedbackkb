import { describe, expect, it, vi } from "vitest";
import { WidgetController } from "../controller";
import { AuthExpiredError } from "../api";

function fakeApi() {
  const calls: string[] = [];
  return {
    calls,
    uploadAttachment: vi.fn(async () => {
      calls.push("upload");
      return "att-" + calls.filter((c) => c === "upload").length;
    }),
    submitFeedback: vi.fn(async () => {
      calls.push("submit");
      return { id: "fb1" };
    }),
  };
}

const blob = () => new Blob(["x"], { type: "image/png" });

describe("WidgetController", () => {
  it("captures BEFORE opening the panel", async () => {
    const order: string[] = [];
    const capture = vi.fn(async () => {
      order.push("capture");
      return blob();
    });
    const c = new WidgetController(fakeApi() as never, {}, capture);
    const openPromise = c.open().then(() => order.push("open"));
    await openPromise;
    expect(order).toEqual(["capture", "open"]);
    expect(c.status).toBe("open");
    expect(c.attachments).toHaveLength(1); // screenshot attached
  });

  it("is LOCAL-ONLY: no network on open/paste", async () => {
    const api = fakeApi();
    const c = new WidgetController(api as never, {}, async () => blob());
    await c.open();
    c.addImage(blob());
    expect(api.calls).toEqual([]); // nothing uploaded yet
    expect(c.attachments).toHaveLength(2);
  });

  it("cancel drops everything without uploading", async () => {
    const api = fakeApi();
    const c = new WidgetController(api as never, {}, async () => blob());
    await c.open();
    c.message = "hi";
    c.cancel();
    expect(api.calls).toEqual([]);
    expect(c.attachments).toHaveLength(0);
    expect(c.status).toBe("closed");
  });

  it("submit uploads each blob THEN posts feedback with ids", async () => {
    const api = fakeApi();
    const c = new WidgetController(api as never, {}, async () => blob());
    await c.open(); // 1 screenshot
    c.addImage(blob()); // +1 image
    c.message = "lỗi nút gửi";
    const res = await c.submit();
    expect(res.id).toBe("fb1");
    expect(api.calls).toEqual(["upload", "upload", "submit"]); // uploads before submit
    expect(api.submitFeedback).toHaveBeenCalledWith(
      expect.objectContaining({ attachmentIds: ["att-1", "att-2"] }),
    );
    expect(c.status).toBe("sent");
  });

  it("rejects empty message", async () => {
    const c = new WidgetController(fakeApi() as never, {}, async () => blob());
    await c.open();
    c.message = "   ";
    await expect(c.submit()).rejects.toThrow();
  });

  it("surfaces auth expiry", async () => {
    const api = fakeApi();
    api.uploadAttachment = vi.fn(async () => {
      throw new AuthExpiredError();
    });
    const c = new WidgetController(api as never, {}, async () => blob());
    await c.open();
    c.message = "x";
    await expect(c.submit()).rejects.toBeInstanceOf(AuthExpiredError);
    expect(c.status).toBe("auth_expired");
  });
});
