# Daily-Reading · 每日金融研究看板

面向职业交易员与量化研究者的**全自动每日情报管线**：每天两班（北京 07:00 早报 / 20:00 晚报）从 120+ 个高质量信息源抓取内容，由 Claude 逐条打标签、评级、写摘要与影响推演，再生成一份深度中文市场报告与关注清单，最终发布成一个可随手翻阅的静态看板。

**零服务器、零数据库**——整套系统只靠 GitHub Actions（定时管线）+ GitHub Pages（静态看板）运行，唯一的持续成本是 Claude API（约 $35–50/月，全部走 Batch API 五折通道，护栏旋钮齐全）。

> 🚀 想自己部署一套？照着 **[SETUP.md](SETUP.md)** 一步步来，全程约 15 分钟，不需要编程经验。

## 它每天为你做什么

1. **抓取**：120+ 源并发拉取——全球财经媒体、中文财经与官方政策（人民日报电子版全文、新闻联播文字版、政策文件库……）、央行与监管、学术（arXiv/NBER）、智库与中国研究、Newsletter、加密与链上、播客，以及可选的 X（Twitter）精选账号组（104 个账号，配好密钥即自动启用）。完整清单见 [docs/sources.md](docs/sources.md)。
2. **去重归档**：双键去重（源+guid 主键 / 标准化标题副键），跨源撞题保留——那本身就是市场信号。
3. **市场快照**：FRED 宏观序列、CFTC 持仓、CBOE 波动率期限结构、Deribit/OKX 加密衍生品、LBMA/COMEX/上金所贵金属与沪伦溢价、多源情绪指标、财经日历，外加自选清单的价格与技术指标（MA/RSI/ATR/52 周位置/已实现波动率），三级容错绝不因单个数据源挂掉而停摆。
4. **AI 逐条分析**（Claude Haiku 4.5）：每条产出中文摘要、重要性评级（S/A/B/C）、市场标签（宏观/美股/A股港股/债券利率/外汇/大宗/贵金属/加密……）；S/A 级条目额外给出影响评估与方向推演（利多/利空、涉及资产、时间尺度、置信度）。
5. **每日深度报告**（Claude Opus 4.8）：全球叙事、跨资产盘面、分市场深析、风险与日历、情绪面，以及**当日关注清单**（个股/期货/期权/外汇，附观点与关键价位）。早报侧重隔夜欧美+亚盘展望，晚报侧重亚盘回顾+欧美盘前。
6. **看板发布**：报告、信息流（多维筛选+搜索）、关注清单、市场快照、历史归档、源状态六个视图；Claude 配色、衬线中文标题、明暗双主题、红涨绿跌、TradingView 实时行情组件。

## 架构一览

```
GitHub Actions（UTC 23:00 → 北京 07:00 早报；UTC 12:00 → 北京 20:00 晚报）
  ├─ RSSHub 服务容器（财联社电报、中纪委等签名/反爬源）
  ├─ Stage 0  回收上一轮未完成的 AI Batch（断点续传）
  ├─ Stage 1  fetch    120+ 源并发抓取，逐源隔离，单源失败不拖累全局
  ├─ Stage 2  dedupe   双键去重（状态随 git 持久化）
  ├─ Stage 3  enrich   市场数据快照（三级容错 fallback 链）
  ├─ Stage 4  analyze  Batch API + Haiku 逐条结构化分析（5 折）
  ├─ Stage 5  report   Batch API + Opus 4.8 深度报告（adaptive thinking）
  ├─ Stage 6  persist  data/YYYY-MM-DD/*.json 提交回仓库
  └─ Stage 7  deploy   GitHub Pages（site/ + data/ 纯静态，无构建）
```

全流程 **fail-open**：任何阶段失败都只记录状态并继续，看板优雅降级而非停更。每周一另有 `source-health` 工作流探活全部源并在 Issue 中生成「源健康周报」。

## 目录结构

```
config/          sources.yaml（源注册表）· watchlist.yaml（自选清单）· settings.yaml（成本护栏）
pipeline/        管线本体：fetch/（8 种抓取器）· parsers/（站点解析器）·
                 enrich/（市场数据）· analyze/（AI 分析与报告）
site/            纯静态看板（无构建步骤）：hash 路由六视图 + Claude 双主题
data/            仅由 CI 写入：每日 JSON + index + 运行状态
scripts/         本地预览（preview.sh）· mock 数据 · 源文档生成
docs/            sources.md——全部信息源清单（自动生成）
.github/workflows/   daily.yml（每日两班）· health.yml（每周源探活）
```

## 成本与护栏

| 项目 | 说明 | 约 |
|---|---|---|
| 逐条分析 | Haiku 4.5 × Batch 5 折，每日上限 `ai.daily_item_cap`（默认 600 条） | ~$0.9/天 |
| 每日报告 | Opus 4.8 × Batch 5 折 × 早晚两份 | ~$0.7/天 |
| 基础设施 | GitHub Actions + Pages（公开仓库免费额度内） | $0 |
| 可选：X 全量拉取 | twitterapi.io，配置密钥后自动启用 | ~$15–25/月 |

所有旋钮集中在 `config/settings.yaml`：单源条数上限、正文截断长度、每日 AI 条目上限、模型名（一键把报告降档到 Sonnet）等。

## 本地预览

```bash
pip install -r requirements.txt
python -m pytest              # 单测（全部离线 fixture，不出网）
bash scripts/preview.sh       # 起本地看板：有真实 data/ 用真实数据，否则自动生成 mock
```

## 合规与免责声明

- 仓库只存储每条内容 ≤500 字的工作摘录与 AI 分析，不存储、不展示文章全文；历史数据 180 天后自动瘦身。
- 行情组件由 [TradingView](https://www.tradingview.com/) 提供；贵金属基准价数据来自 LBMA/COMEX/上海黄金交易所公开渠道。
- 本项目全部输出（包括 AI 生成的评级、推演与关注清单）**仅供研究参考，不构成任何投资建议**。

## License

[MIT](LICENSE)
