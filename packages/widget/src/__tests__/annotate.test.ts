import { describe, expect, it } from "vitest";
import { AnnotationStack, DEFAULT_COLOR, flatten } from "../annotate";

describe("annotate", () => {
  it("push/undo manages the op stack", () => {
    const s = new AnnotationStack();
    s.push({ tool: "rect", points: [{ x: 0, y: 0 }, { x: 10, y: 10 }], color: DEFAULT_COLOR });
    expect(s.length).toBe(1);
    s.undo();
    expect(s.length).toBe(0);
  });

  it("detects blur ops (redaction)", () => {
    const s = new AnnotationStack();
    expect(s.hasBlur()).toBe(false);
    s.push({ tool: "blur", points: [{ x: 0, y: 0 }, { x: 5, y: 5 }], color: DEFAULT_COLOR });
    expect(s.hasBlur()).toBe(true);
  });

  it("flatten returns a blob and flags redacted when blurred", async () => {
    const s = new AnnotationStack();
    s.push({ tool: "blur", points: [{ x: 0, y: 0 }, { x: 5, y: 5 }], color: DEFAULT_COLOR });
    const base = document.createElement("canvas");
    base.width = 20;
    base.height = 20;
    const { blob, redacted } = await flatten(base, s, 20, 20);
    expect(blob).toBeInstanceOf(Blob);
    expect(redacted).toBe(true);
  });
});
