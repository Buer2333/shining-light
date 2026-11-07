import React from 'react';

const hash = (i: number, k: number) => {
  const v = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453;
  return v - Math.floor(v);
};

type DustProps = {
  w: number;
  h: number;
  /** Number of specks. */
  n: number;
  seed?: number;
  /** Radius is 0.6 + random × rSpan. */
  rSpan?: number;
  /** Opacity is op[0] + random × op[1]. */
  op?: [number, number];
  colors?: [string, string];
  /** Pass the current frame to make the specks drift. Leave it out for a still field. */
  f?: number;
};

/** A field of faint specks for dark backgrounds. Same seed, same field, on every render. */
export const Dust: React.FC<DustProps> = ({ w, h, n, seed = 191, rSpan = 1.3, op = [0.06, 0.18], colors = ['#FFF7E9', '#6F80FF'], f }) => (
  <svg width={w} height={h} style={{ position: 'absolute', left: 0, top: 0 }}>
    {Array.from({ length: n }).map((_, i) => (
      <circle
        key={i}
        cx={hash(i, seed) * w + (f === undefined ? 0 : Math.sin(f / 40 + i) * 4)}
        cy={hash(i, seed + 1) * h + (f === undefined ? 0 : Math.cos(f / 50 + i) * 4)}
        r={0.6 + hash(i, seed + 2) * rSpan}
        fill={hash(i, seed + 3) < 0.5 ? colors[0] : colors[1]}
        opacity={op[0] + hash(i, seed + 4) * op[1]}
      />
    ))}
  </svg>
);
