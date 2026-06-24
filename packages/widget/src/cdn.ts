// CDN entry (Step 18) — global FeedbackKB.init({system, apiBase}) for non-bundler apps.
import { createElement } from "react";
import { createRoot } from "react-dom/client";
import { FeedbackWidget, type FeedbackWidgetProps } from "./FeedbackWidget";

export const FeedbackKB = {
  init(props: FeedbackWidgetProps & { mountId?: string }) {
    const host = props.mountId
      ? document.getElementById(props.mountId)!
      : (() => {
          const d = document.createElement("div");
          d.id = "feedbackkb-root";
          document.body.appendChild(d);
          return d;
        })();
    createRoot(host).render(createElement(FeedbackWidget, props));
  },
};

// expose on window for <script> usage
if (typeof window !== "undefined") {
  (window as unknown as Record<string, unknown>).FeedbackKB = FeedbackKB;
}
