// Bundler entry (Step 18) — import { FeedbackWidget } from "@clevai/feedbackkb-widget".
export { FeedbackWidget, type FeedbackWidgetProps } from "./FeedbackWidget";
export { WidgetController } from "./controller";
export { FeedbackApi, AuthExpiredError } from "./api";
export { captureScreenshot, isDenylisted } from "./capture";
export { AnnotationStack, flatten } from "./annotate";
export { FeedbackDashboard } from "./dashboard/FeedbackDashboard";
export { applyFilter, type FeedbackRow } from "./dashboard/filter";
