import { interpolate } from 'remotion';

export type XY = { x: number; y: number };
export type Rect = { x: number; y: number; w: number; h: number };
export type Box = { left: number; top: number; width: number; height: number };

export const toRect = (b: Box): Rect => ({ x: b.left, y: b.top, w: b.width, h: b.height });

export const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;

export const ease = {
  out: (t: number) => 1 - Math.pow(1 - t, 3),
  inOut: (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
};

const progress = (frame: number, start: number, duration: number) =>
  interpolate(frame, [start, start + Math.max(1, duration)], [0, 1], clamp);

/** Eased 0–1 progress over `duration` frames from `start`. */
export const easeOut = (frame: number, start: number, duration: number) => ease.out(progress(frame, start, duration));
export const easeInOut = (frame: number, start: number, duration: number) => ease.inOut(progress(frame, start, duration));

/** Exponential decay from 1 to about 0.05 over `length` frames, 0 outside. Good for shakes. */
export const decay = (frame: number, start: number, length: number) =>
  frame >= start && frame < start + length ? Math.exp(-(frame - start) / (length / 3)) : 0;
