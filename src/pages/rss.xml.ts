import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';
import { firstPublished } from '../lib/site';

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const summary = (text: string) => {
  const line = text.trim().split(/\n+/)[0] ?? '';
  return line.length > 200 ? `${line.slice(0, 200)}…` : line;
};

export async function GET({ site }: APIContext) {
  const link = (path: string) => new URL(path, site).href;

  const diary = (await getCollection('diary'))
    .filter((e) => e.data.public && e.data.status === 'published' && !e.data.sample)
    .flatMap((e) => {
      const at = firstPublished(e.data.platforms);
      if (!at) return [];
      return [{
        title: `${e.data.no} ${e.data.title}`,
        path: `diary/${e.id}/`,
        date: new Date(at),
        text: summary(e.data.retro) || e.data.pillar,
      }];
    });

  const cases = (await getCollection('brandlab'))
    .filter((e) => !e.data.sample)
    .map((e) => ({
      title: e.data.title,
      path: `brandlab/${e.id}/`,
      date: e.data.date,
      text: e.data.summary,
    }));

  const posts = (
    await Promise.all(
      (['guides', 'agents'] as const).map(async (col) =>
        (await getCollection(col))
          .filter((e) => !e.data.sample)
          .map((e) => ({ title: e.data.title, path: `${col}/${e.id}/`, date: e.data.date, text: e.data.summary })),
      ),
    )
  ).flat();

  const items = [...diary, ...cases, ...posts]
    .sort((a, b) => b.date.getTime() - a.date.getTime())
    .map(
      (i) => `    <item>
      <title>${esc(i.title)}</title>
      <link>${link(i.path)}</link>
      <guid isPermaLink="true">${link(i.path)}</guid>
      <pubDate>${i.date.toUTCString()}</pubDate>
      <description>${esc(i.text)}</description>
    </item>`,
    )
    .join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Shining</title>
    <link>${link('')}</link>
    <description>用代码和 AI 做动效、搭 Agent、做品牌增长的公开工作笔记。</description>
    <language>zh-CN</language>
${items}
  </channel>
</rss>
`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
}
