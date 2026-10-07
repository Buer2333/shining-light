export const PILLARS = ['品牌拆解', '真实翻车', '名词卡', '业务落地', '组织观察', 'intro'] as const;

export const PLATFORM_LABEL: Record<string, string> = { xhs: '小红书', douyin: '抖音' };
export const SOURCE_LABEL: Record<string, string> = { tikhub: '接口', screenshot: '截图录入' };
export const STATUS_LABEL: Record<string, string> = {
  scheduled: '待发布',
  published: '已发布',
  withdrawn: '已撤回',
};

export const BUCKETS = ['24h', '72h', '7d'] as const;
export const BUCKET_LABEL: Record<string, string> = { '24h': '≈24h', '72h': '≈72h', '7d': '≈7d' };

export const METRICS = [
  ['views', '播放'],
  ['likes', '点赞'],
  ['collects', '收藏'],
  ['comments', '评论'],
  ['shares', '分享'],
  ['completion_rate', '完播率'],
  ['followers_gained', '涨粉'],
] as const;

export const MISSING = '未采';

/** Internal link that respects the GitHub Pages base path. */
export const url = (path = '') => {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}/${path.replace(/^\//, '')}`;
};

export const hoursLabel = (h: number) => `实测 ${h.toFixed(1)}h`;

/** 「≈24h（实测 26.5h）」 for bucketed samples, 「实测 30.0h」 for plain points. */
export const sampleLabel = (bucket: string, h: number) =>
  bucket in BUCKET_LABEL ? `${BUCKET_LABEL[bucket]}（${hoursLabel(h)}）` : hoursLabel(h);

export const fmtMetric = (key: string, v: number | null | undefined) => {
  if (v === null || v === undefined) return MISSING;
  if (key === 'completion_rate') return `${(v * 100).toFixed(1)}%`;
  return v.toLocaleString('zh-CN');
};

export const fmtDate = (d: Date | string | null | undefined) => {
  if (!d) return '';
  // Strings keep their own offset (e.g. +08:00) — take the local date as written.
  return typeof d === 'string' ? d.slice(0, 10) : d.toISOString().slice(0, 10);
};

/** Earliest platform publish time, or null if not yet published anywhere. */
export const firstPublished = (platforms: Record<string, { published_at: string | null } | undefined>) => {
  const ts = Object.values(platforms)
    .map((p) => p?.published_at)
    .filter((x): x is string => !!x)
    .sort();
  return ts[0] ?? null;
};
