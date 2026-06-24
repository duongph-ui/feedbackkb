import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FeedbackWidget } from "../FeedbackWidget";

describe("FeedbackWidget", () => {
  it("renders the floating button when closed", () => {
    render(<FeedbackWidget system="FPS" apiBase="http://x" appKey="k" />);
    expect(screen.getByTestId("fbk-fab")).toBeTruthy();
    expect(screen.getByTestId("fbk-fab").textContent).toContain("Phản hồi");
  });
});
