# shining-light

Shining 的公开工作笔记：拆大牌广告创意，照亮最要紧的那一处。

栏目：发布日记 · 品牌拆解库 · 作品 · 简历设计路径（整理中）。

## 开发

```sh
npm ci
npm run dev            # 本地预览
npm run build          # 生产构建（不含示例数据）
npm run build:samples  # 带 src/content/_samples/ 的合成示例构建，用来验证表结构和页面
```

内容由导出脚本白名单写入 `src/content/`，表结构约定见 `src/content/README.md`。
推送到 `main` 后由 GitHub Actions 构建，发布闸（`tools/site_gate.py`）通过才部署到 Pages。

字体：得意黑 Smiley Sans、JetBrains Mono，均为 SIL OFL 1.1。
