# tools/

`site_gate.py` —— 发布闸（fail-closed），**还没放进来**。

- 真源在私有仓库，由维护者手动拷贝到这里（`tools/site_gate.py`），本仓库只放副本。
- CI（`.github/workflows/deploy.yml`）在构建后对 `dist/` 跑：
  `python3 tools/site_gate.py --dist dist`
- 只认明确通过：脚本缺失、异常、超时、必需配置缺失都判失败，部署不会执行。
- 必需配置 `SITE_GATE_PII_TERMS` 来自仓库 Actions secret，只在闸这一步的环境变量里出现，不写进仓库。

在 `site_gate.py` 放进来之前，CI 会在闸这一步失败、不部署——这是预期行为。
