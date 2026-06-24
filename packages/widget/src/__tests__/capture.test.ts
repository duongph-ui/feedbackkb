import { describe, expect, it, vi } from "vitest";
import { captureScreenshot, isDenylisted } from "../capture";

describe("capture", () => {
  it("isDenylisted matches route prefixes", () => {
    expect(isDenylisted("/payroll/view", ["/payroll"])).toBe(true);
    expect(isDenylisted("/payment/create", ["/payroll"])).toBe(false);
  });

  it("skips capture on a denylisted route", async () => {
    const renderer = vi.fn();
    const blob = await captureScreenshot({
      path: "/payroll",
      denylistRoutes: ["/payroll"],
      renderer: renderer as never,
    });
    expect(blob).toBeNull();
    expect(renderer).not.toHaveBeenCalled();
  });

  it("masks denylisted elements during render, restores after", async () => {
    document.body.innerHTML = `<div class="salary">$9999</div>`;
    const el = document.querySelector<HTMLElement>(".salary")!;
    let visibilityDuringRender = "";
    const renderer = vi.fn(async () => {
      visibilityDuringRender = el.style.visibility;
      const c = document.createElement("canvas");
      return c;
    });
    await captureScreenshot({
      path: "/ok",
      maskSelectors: [".salary"],
      renderer: renderer as never,
    });
    expect(visibilityDuringRender).toBe("hidden"); // masked while rendering
    expect(el.style.visibility).toBe(""); // restored after
  });
});
