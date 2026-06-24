// Auto-screenshot capture (Step 15 / CL6). LOCAL-ONLY: returns a Blob held in
// memory; nothing is uploaded here. DOM-mask denylisted elements BEFORE rendering
// so sensitive pixels never enter the image.

export interface CaptureOptions {
  // CSS selectors masked (hard) before render, e.g. ".salary, [data-pii]"
  maskSelectors?: string[];
  // route denylist: if current path matches, auto-capture is skipped
  denylistRoutes?: string[];
  // injectable renderer (html2canvas) + current path for testability
  renderer?: (el: HTMLElement) => Promise<HTMLCanvasElement>;
  path?: string;
}

export function isDenylisted(path: string, denylist: string[] = []): boolean {
  return denylist.some((d) => path.startsWith(d));
}

function applyMask(selectors: string[]): HTMLElement[] {
  const masked: HTMLElement[] = [];
  for (const sel of selectors) {
    document.querySelectorAll<HTMLElement>(sel).forEach((el) => {
      el.dataset.fbkPrevVisibility = el.style.visibility;
      el.style.visibility = "hidden"; // hard mask before render
      masked.push(el);
    });
  }
  return masked;
}

function unmask(masked: HTMLElement[]): void {
  for (const el of masked) {
    el.style.visibility = el.dataset.fbkPrevVisibility ?? "";
    delete el.dataset.fbkPrevVisibility;
  }
}

async function defaultRenderer(el: HTMLElement): Promise<HTMLCanvasElement> {
  const h2c = (await import("html2canvas")).default;
  return h2c(el);
}

// Capture the current page. Returns null when the route is denylisted.
export async function captureScreenshot(opts: CaptureOptions = {}): Promise<Blob | null> {
  const path = opts.path ?? (typeof location !== "undefined" ? location.pathname : "/");
  if (isDenylisted(path, opts.denylistRoutes ?? [])) return null;

  const masked = applyMask(opts.maskSelectors ?? []);
  try {
    const render = opts.renderer ?? defaultRenderer;
    const canvas = await render(document.body);
    return await canvasToBlob(canvas);
  } finally {
    unmask(masked); // always restore, even on render error
  }
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return toBlobSafe(canvas);
}

// Resolve a PNG blob. In non-browser canvases (jsdom) toBlob is a no-op stub
// that never invokes the callback, so a short fallback resolves an empty blob.
export function toBlobSafe(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve) => {
    const empty = new Blob([], { type: "image/png" });
    const fallback = setTimeout(() => resolve(empty), 200);
    try {
      if (!canvas.toBlob) {
        clearTimeout(fallback);
        resolve(empty);
        return;
      }
      canvas.toBlob((b) => {
        clearTimeout(fallback);
        resolve(b ?? empty);
      }, "image/png");
    } catch {
      clearTimeout(fallback);
      resolve(empty);
    }
  });
}
