type Point = [number, number];

const solve = (A: number[][], b: number[]) => {
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < n; c++) {
    let pivot = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[pivot][c])) pivot = r;
    [M[c], M[pivot]] = [M[pivot], M[c]];
    const d = M[c][c] || 1e-12;
    for (let k = c; k <= n; k++) M[c][k] /= d;
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c];
      if (f !== 0) for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
    }
  }
  return M.map((row) => row[n]);
};

/**
 * CSS matrix3d that maps the rectangle (0,0)–(w,h) onto any quad, so a flat 2D
 * layer can sit on a surface in perspective. Use with transform-origin: 0 0.
 * Corners run top-left, top-right, bottom-right, bottom-left.
 */
export const rectToQuad = (w: number, h: number, quad: Point[]): string => {
  const src: Point[] = [[0, 0], [w, 0], [w, h], [0, h]];
  const A: number[][] = [];
  const b: number[] = [];
  for (let i = 0; i < 4; i++) {
    const [x, y] = src[i];
    const [u, v] = quad[i];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]);
    b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]);
    b.push(v);
  }
  const [m0, m1, m2, m3, m4, m5, m6, m7] = solve(A, b);
  return `matrix3d(${[m0, m3, 0, m6, m1, m4, 0, m7, 0, 0, 1, 0, m2, m5, 0, 1].map((v) => v.toFixed(9)).join(',')})`;
};
