// Annotate overlay (Step 16 / CL6). Tool ops on a transparent layer above the
// screenshot; blur is flattened HARD into pixels (not a CSS filter) so the
// original data cannot be recovered. Undo pops the op stack.

import { toBlobSafe } from "./capture";

export type Tool = "rect" | "freehand" | "arrow" | "blur";

export interface AnnotationOp {
  tool: Tool;
  points: { x: number; y: number }[];
  color: string;
}

export const DEFAULT_COLOR = "#dc2626";

export class AnnotationStack {
  private ops: AnnotationOp[] = [];

  push(op: AnnotationOp): void {
    this.ops.push(op);
  }

  undo(): AnnotationOp | undefined {
    return this.ops.pop();
  }

  get length(): number {
    return this.ops.length;
  }

  hasBlur(): boolean {
    return this.ops.some((o) => o.tool === "blur");
  }

  list(): readonly AnnotationOp[] {
    return this.ops;
  }
}

// Flatten base image + ops into a single PNG blob. Blur regions are pixelated
// hard. Returns { blob, redacted } where redacted=true if any blur was applied.
export async function flatten(
  base: HTMLImageElement | HTMLCanvasElement,
  stack: AnnotationStack,
  width: number,
  height: number,
): Promise<{ blob: Blob; redacted: boolean }> {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.drawImage(base, 0, 0, width, height);
    for (const op of stack.list()) drawOp(ctx, op);
  }
  const blob = await toBlobSafe(canvas);
  return { blob, redacted: stack.hasBlur() };
}

function drawOp(ctx: CanvasRenderingContext2D, op: AnnotationOp): void {
  ctx.strokeStyle = op.color;
  ctx.lineWidth = 3;
  if (op.tool === "rect" && op.points.length >= 2) {
    const [a, b] = op.points;
    ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
  } else if (op.tool === "blur" && op.points.length >= 2) {
    // hard pixel mask (opaque fill) — destroys underlying data
    const [a, b] = op.points;
    ctx.fillStyle = "#334155";
    ctx.fillRect(a.x, a.y, b.x - a.x, b.y - a.y);
  } else if (op.points.length >= 2) {
    ctx.beginPath();
    ctx.moveTo(op.points[0].x, op.points[0].y);
    for (const p of op.points.slice(1)) ctx.lineTo(p.x, p.y);
    ctx.stroke();
  }
}

