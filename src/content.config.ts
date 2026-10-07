import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { PILLARS } from './lib/site';

// Synthetic samples under src/content/_samples/ are only loaded when
// SITE_INCLUDE_SAMPLES=1 (local dev / schema smoke test). Production builds
// (CI) never set it, so samples never reach dist/.
const INCLUDE_SAMPLES = process.env.SITE_INCLUDE_SAMPLES === '1';

// ext is a glob alternation such as '{md,json}' (exporter writes json for diary/works).
const patterns = (name: string, ext: string) => [
  `${name}/**/*.${ext}`,
  ...(INCLUDE_SAMPLES ? [`_samples/${name}/*.${ext}`] : []),
];

const idFromFile = ({ entry, data }: { entry: string; data: Record<string, unknown> }) =>
  typeof data.slug === 'string' && data.slug
    ? data.slug
    : entry.split('/').pop()!.replace(/\.(md|json)$/, '');

// "" (template default for unfilled fields) -> null
const emptyToNull = <T extends z.ZodTypeAny>(schema: T) =>
  z.preprocess((v) => (v === '' || v === undefined ? null : v), schema.nullable());

// YAML parses unquoted timestamps into Date (offset lost). Accept that, but
// exporters should quote the string so the original offset is kept.
const isoDateTime = z.preprocess(
  (v) => (v instanceof Date ? v.toISOString() : v),
  z.iso.datetime({ offset: true }),
);

const metric = z.number().nonnegative().nullable().default(null);

// The exporter nests the numbers under `metrics`; hoist them to the top level.
const flattenMetrics = (v: unknown) =>
  v && typeof v === 'object' && 'metrics' in v
    ? { ...(v as Record<string, unknown>).metrics as object, ...(v as object), metrics: undefined }
    : v;

const sample = z.preprocess(flattenMetrics, z.object({
  platform: z.enum(['xhs', 'douyin']),
  sampled_at: isoDateTime,
  hours_since_publish: z.number().nonnegative(),
  source: z.enum(['tikhub', 'screenshot']),
  // computed by the exporter: 24h ±6h / 72h ±12h / 7d ±24h, otherwise "point"
  bucket: z.enum(['24h', '72h', '7d', 'point']),
  views: metric,
  likes: metric,
  collects: metric,
  comments: metric,
  shares: metric,
  completion_rate: metric, // 0–1
  followers_gained: metric,
}));

const platformEntry = z.object({
  title: z.string().default(''),
  url: emptyToNull(z.url()),
  published_at: emptyToNull(isoDateTime),
  video: z.string().optional(), // exporter should drop; never rendered
});

const diary = defineCollection({
  loader: glob({ base: './src/content', pattern: patterns('diary', '{md,json}'), generateId: idFromFile }),
  schema: z.object({
    no: z.string(),
    slug: z.string(),
    title: z.string(),
    pillar: z.enum(PILLARS),
    status: z.enum(['scheduled', 'published', 'withdrawn']),
    version_tag: z.string().optional(),
    platforms: z.object({
      xhs: platformEntry.optional(),
      douyin: platformEntry.optional(),
    }),
    samples: z.array(sample).default([]),
    retro: z.string().default(''),
    comments_notes: z.array(z.string()).default([]),
    public: z.boolean().default(true),
    sample: z.boolean().default(false), // true only in src/content/_samples/
  }),
});

const brandlab = defineCollection({
  loader: glob({ base: './src/content', pattern: patterns('brandlab', 'md'), generateId: idFromFile }),
  schema: z.object({
    title: z.string(),
    brand: z.string(),
    category: z.string(),
    tags: z.array(z.string()).default([]),
    date: z.coerce.date(),
    summary: z.string(),
    sample: z.boolean().default(false),
  }),
});

const works = defineCollection({
  loader: glob({ base: './src/content', pattern: patterns('works', '{md,json}'), generateId: idFromFile }),
  schema: z.object({
    no: z.string(),
    title: z.string(),
    slug: z.string(),
    pillar: z.enum(PILLARS).optional(),
    notes: z.string().default(''),
    iterations: z
      .array(z.object({ tag: z.string(), date: z.string(), note: z.string() }))
      .default([]),
    sample: z.boolean().default(false),
  }),
});

// Placeholder only — the resume timeline ships in a later, separately approved push.
const resume = defineCollection({
  loader: glob({ base: './src/content', pattern: patterns('resume', 'md'), generateId: idFromFile }),
  schema: z.object({
    title: z.string(),
    status: z.literal('placeholder'),
    sample: z.boolean().default(false),
  }),
});

export const collections = { diary, brandlab, works, resume };
