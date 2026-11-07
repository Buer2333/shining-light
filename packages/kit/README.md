# @shining-motion/kit

Small building blocks for code-driven motion in [Remotion](https://www.remotion.dev). Every piece is a pure function of the frame, so a render comes out the same each time.

| Export | What it does |
|---|---|
| `Dust` | A seeded field of faint specks, still or drifting |
| `GrayLines` | Placeholder text lines, with an optional line-by-line reveal |
| `Seal` | A stamp that lands, settles and leaves ink specks |
| `rectToQuad` | CSS `matrix3d` that puts a flat layer on a quad in perspective |
| `easeOut`, `easeInOut`, `decay`, `lerp`, `clamp` | Frame-based timing helpers |

This package is not on npm. Copy `src/`, or install it from a checkout as [`examples/hello-motion`](../../examples/hello-motion) does.

## License

MIT. Remotion itself has its own license, and some companies need a paid one: see [remotion.dev/license](https://www.remotion.dev/license).
