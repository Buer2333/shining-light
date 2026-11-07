import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { clamp } from '../geom';

type SealProps = {
  text: string;
  /** Frame the stamp lands on. */
  at: number;
  px: number;
  color: string;
  rot?: number;
  pad?: number;
  bg?: string;
  fontFamily?: string;
};

/** A double-ruled stamp: lands oversized, settles in 9 frames, and leaves a ring of ink specks. */
export const Seal: React.FC<SealProps> = ({ text, at, px, color, rot = -6, pad = 14, bg = 'transparent', fontFamily = 'inherit' }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [at, at + 4, at + 9], [1.35, 0.96, 1], clamp);
  const opacity = interpolate(frame, [at, at + 2], [0, 1], clamp);
  return (
    <span style={{ position: 'relative', display: 'inline-block', opacity, transform: `scale(${scale}) rotate(${rot}deg)` }}>
      <span style={{ display: 'inline-block', padding: `2px ${pad}px`, border: `6px solid ${color}`, outline: `2px solid ${color}`, outlineOffset: 4, color, fontFamily, fontWeight: 700, fontSize: px, lineHeight: 1.15, whiteSpace: 'nowrap', background: bg }}>
        {text}
      </span>
      {[...Array(8)].map((_, i) => (
        <span key={i} style={{ position: 'absolute', width: 6 + (i % 3) * 3, height: 6 + (i % 3) * 3, borderRadius: '50%', background: color, opacity: frame >= at + 3 ? 0.5 : 0, left: `${(i * 37) % 100}%`, top: i % 2 ? -16 : 'calc(100% + 8px)' }} />
      ))}
    </span>
  );
};
