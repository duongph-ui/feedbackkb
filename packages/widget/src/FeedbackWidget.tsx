// React widget (Step 14/17). Floating button -> panel with 1 textarea + auto
// screenshot preview + paste. Thin shell over WidgetController.

import { useCallback, useMemo, useRef, useState } from "react";
import { FeedbackApi, type ApiConfig } from "./api";
import { WidgetController } from "./controller";

export interface FeedbackWidgetProps {
  system: string;
  apiBase: string;
  getJwt?: () => string | null;
  appKey?: string;
  maskSelectors?: string[];
  denylistRoutes?: string[];
}

export function FeedbackWidget(props: FeedbackWidgetProps) {
  const apiCfg: ApiConfig = {
    apiBase: props.apiBase,
    system: props.system,
    getJwt: props.getJwt,
    appKey: props.appKey,
  };
  const ctrl = useMemo(
    () =>
      new WidgetController(new FeedbackApi(apiCfg), {
        maskSelectors: props.maskSelectors,
        denylistRoutes: props.denylistRoutes,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const [, force] = useState(0);
  const rerender = useCallback(() => force((n) => n + 1), []);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const openPanel = async () => {
    await ctrl.open(); // captures first, then opens
    rerender();
  };

  const onPaste = (e: React.ClipboardEvent) => {
    for (const item of Array.from(e.clipboardData.items)) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) ctrl.addImage(file);
      }
    }
    rerender();
  };

  const send = async () => {
    ctrl.message = taRef.current?.value ?? "";
    try {
      await ctrl.submit();
    } finally {
      rerender();
    }
  };

  if (ctrl.status === "closed") {
    return (
      <button data-testid="fbk-fab" onClick={openPanel}>
        💬 Phản hồi
      </button>
    );
  }
  if (ctrl.status === "sent") {
    return <div data-testid="fbk-thanks">✅ Đã ghi nhận!</div>;
  }
  return (
    <div data-testid="fbk-panel">
      <div data-testid="fbk-shot-count">{ctrl.attachments.length} ảnh đính kèm</div>
      <textarea
        ref={taRef}
        data-testid="fbk-msg"
        placeholder="Mô tả vấn đề / ý tưởng. Dán ảnh (Ctrl+V) trực tiếp."
        onPaste={onPaste}
        defaultValue={ctrl.message}
      />
      {ctrl.status === "auth_expired" && (
        <div data-testid="fbk-auth">Phiên hết hạn, đăng nhập lại</div>
      )}
      <button data-testid="fbk-cancel" onClick={() => { ctrl.cancel(); rerender(); }}>
        Bỏ
      </button>
      <button data-testid="fbk-send" onClick={send}>
        ✈ Gửi phản hồi
      </button>
    </div>
  );
}
