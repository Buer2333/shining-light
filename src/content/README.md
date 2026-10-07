# src/content —— 内容表结构约定（导出脚本 ↔ 站点）

本目录由私有仓库的导出脚本（`site_export.py`）白名单写入，**不要手改**。表结构的代码真源是 `src/content.config.ts`（zod），本文件是给导出脚本看的说明；两边不一致时以 `content.config.ts` 为准，并同步改这里。

| 目录 | 集合 | 文件 | 页面 |
|---|---|---|---|
| `diary/` | 发布日记 | `{slug}.md` | `/diary/`、`/diary/{slug}/` |
| `brandlab/` | 品牌拆解库 | `{slug}.md` | `/brandlab/`、`/brandlab/{slug}/` |
| `works/` | 作品 | `{slug}.md` | `/works/`（锚点 `#{slug}`） |
| `resume/` | 简历设计路径 | 目前不导出 | `/resume/` 固定为「整理中」占位页 |
| `_samples/` | 合成示例 | 每个集合一条假数据 | 只在 `SITE_INCLUDE_SAMPLES=1` 时加载；CI 生产构建不设，示例不会进 `dist/` |

条目 id = front-matter 的 `slug`（没有则用文件名）。同一集合内 slug 必须唯一。

## diary（发布日记）

Front-matter 沿用私有仓库的发布日记模板，导出时：
- `public: false` 的条目**不导出**（站点也会再过滤一次）。
- `platforms.*.video`（本地视频路径）和 `version_tag` 应删掉；schema 允许缺省，页面不渲染它们。
- 尚未填写的字符串字段可以是 `""`，`url` / `published_at` 的 `""` 会被当成 null。

```yaml
no: NO.01                       # string，期号
slug: example                   # string
title: 标题                      # string
pillar: 品牌拆解                  # 品牌拆解 | 真实翻车 | 名词卡 | 业务落地 | 组织观察 | intro
status: published               # scheduled | published | withdrawn
platforms:                      # 两个键都可选
  xhs:    { title: "", url: "https://…" | "", published_at: "2026-10-07T21:00:00+08:00" | "" }
  douyin: { title: "", url: "",              published_at: "" }
samples:                        # 每次采样一条；没采到就不写
  - platform: xhs               # xhs | douyin
    sampled_at: "2026-10-08T23:30:00+08:00" # ISO 8601 带时区，加引号（不加引号 YAML 会转成 Date、丢掉原时区）
    hours_since_publish: 26.5   # number，实测小时数（sampled_at − published_at）
    source: tikhub              # tikhub | screenshot
    bucket: 24h                 # 24h | 72h | 7d | point —— 由导出脚本计算，见下
    views: 1234                 # 以下指标都是 number | null，缺省 = null，页面显示「未采」
    likes: null
    collects: null
    comments: null
    shares: null
    completion_rate: null       # 0–1 小数
    followers_gained: null
retro: ""                       # string
comments_notes: []              # string[]
public: true
```

**bucket 计算（导出脚本负责，站点不重算）**：
- `24h`：hours ∈ [18, 30]；`72h`：hours ∈ [60, 84]；`7d`：hours ∈ [144, 192]；其余为 `point`。
- 同一平台同一档位只能有一条；若有多条，导出脚本取离档位中心最近的一条，其余改为 `point`。
- 不插值、不用日快照倒推、不补 0。

页面展示：档位行显示「≈24h（实测 26.5h）」，没有对应档位样本的行显示「未采」；`point` 样本按小时排在后面，显示「实测 30.0h」。总览图横轴就是 `hours_since_publish` 实际值。

## brandlab（品牌拆解库）

```yaml
title: string
brand: string
category: string
tags: [string, ...]
date: 2026-10-07                # YYYY-MM-DD
summary: string                 # 一两句，列表页和搜索用
```
正文：markdown（只放学习层结论，不放内部数据）。

## works（作品）

```yaml
no: NO.01
title: string
slug: string
pillar: 同 diary
notes: string                   # 一句话说明
```
正文：markdown，写迭代过程。视频本体只链接到平台，不放文件。

## resume（简历设计路径）

首推只放占位页，不导出内容。时间线经单独审批后再定 schema；当前 schema 只接受 `title` + `status: placeholder`。

## 通用约束

- 所有字段会被发布闸扫描（品牌/公司词表、PII、精确业务数字、文件类型、图片元数据）。
- 示例条目带 `sample: true`；导出的真实条目不要写这个字段。
- 不要放 pdf / docx / 音视频文件；图片需先剥离 EXIF / XMP / PNG 文本块。
