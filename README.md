# Daily-Reading · 每日金融研究 macOS 桌面应用

面向职业交易员与量化研究者的**桌面情报终端**：每天早晚两班（北京 07:00 早报 / 20:00 晚报）自动从 120+ 个高质量信息源抓取内容，用你自己的 AI（**Claude / ChatGPT / Gemini / DeepSeek 任选**）逐条打标签、评级、写摘要与影响推演，再生成一份深度中文市场报告与关注清单——全部在你的 MacBook 本机完成，数据不经过任何第三方服务器。

**下载即用，全部配置都在 App 内的设置面板完成**（就像 Claude 桌面版）：粘贴你自己的 API Key（存进 macOS 钥匙串）、勾选感兴趣的信息源、选实时或省钱模式，然后等每天两班报告自动送达（菜单栏常驻 + 系统通知）。

> 🚀 **三分钟上手**：照着 **[SETUP.md](SETUP.md)** 走——下载 `.dmg` → 拖进应用程序 → 右键打开 → 设置面板粘贴 API Key → 点「立即运行」。不需要编程经验，不需要配置 GitHub。

## 它每天为你做什么

1. **抓取**：120+ 源并发拉取——全球财经媒体、中文财经与官方政策（人民日报电子版全文、新闻联播文字版、政策文件库……）、央行与监管、学术（arXiv/NBER）、智库与中国研究、Newsletter、加密与链上、播客，以及可选的 X（Twitter）精选账号组（104 个账号，配好密钥即自动启用）。完整清单见 [docs/sources.md](docs/sources.md)，全部可在设置面板逐个启停或添加自定义 RSS。
2. **去重归档**：双键去重（源+guid 主键 / 标准化标题副键），跨源撞题保留——那本身就是市场信号。
3. **市场快照**：FRED 宏观序列、CFTC 持仓、CBOE 波动率期限结构、Deribit/OKX 加密衍生品、LBMA/COMEX/上金所贵金属与沪伦溢价、多源情绪指标、财经日历，外加自选清单的价格与技术指标（MA/RSI/ATR/52 周位置/已实现波动率），三级容错绝不因单个数据源挂掉而停摆。
4. **AI 逐条分析**（你选的模型）：每条产出中文摘要、重要性评级（S/A/B/C）、市场标签（宏观/美股/A股港股/债券利率/外汇/大宗/贵金属/加密……）；S/A 级条目额外给出影响评估与方向推演（利多/利空、涉及资产、时间尺度、置信度）。
5. **每日深度报告**：全球叙事、跨资产盘面、分市场深析、风险与日历、情绪面，以及**当日关注清单**（个股/ETF/期货/期权/外汇/加密，附方向观点与关键价位）。早报侧重隔夜欧美+亚盘展望，晚报侧重亚盘回顾+欧美盘前。
6. **窗口即看板**：报告、信息流（多维筛选+搜索）、关注清单、市场快照、历史归档、源状态、设置七个视图；Claude 配色、衬线中文标题、明暗双主题、红涨绿跌、TradingView 实时行情组件。

## 设置面板（一切配置的家）

App 内第七个视图「设置」，四个分区：

| 分区 | 你能做什么 |
|---|---|
| **AI 引擎** | 四家供应商任选；逐条分析/报告模型分别指定；实时（即时可见）或省钱 Batch（五折）模式；每日 AI 条数上限（成本护栏） |
| **API 密钥** | 粘贴各家 AI Key 与可选数据源 Key（twitterapi.io / FRED）——全部存 **macOS 钥匙串**，界面永不回显明文 |
| **信息源** | 120+ 源按分类逐个开关；一行添加自定义 RSS 源；配置 RSSHub 实例（财联社等 8 个源需要） |
| **运行** | 手动立即运行早报/晚报；查看下次自动运行时间 |

所有改动只写到本机 `~/Library/Application Support/Daily-Reading/`，出厂配置永不被破坏，改坏了删掉用户配置文件即恢复默认。

## 架构一览

```
Daily-Reading.app（全 Python，Briefcase 打包）
├─ 窗口（WKWebView）→ 本机 loopback 服务 → site/ 七视图界面
├─ 菜单栏常驻（关窗不退出）：打开看板 / 立即运行 / 退出
├─ 定时器：北京 07:00 / 20:00 自动跑，错过班次开机自动补，完成弹系统通知
└─ 管线：抓取 → 去重 → 市场快照 → AI 逐条分析 → 深度报告 → 本机落盘
```

隐私与安全：只绑 127.0.0.1 的本地服务 + 写接口令牌校验；密钥仅存钥匙串；抓取直连各源站与 AI 官方 API，无任何中间服务器。

## 目录结构（开发者视角）

```
config/          sources.yaml（出厂源注册表）· watchlist.yaml（自选清单）· settings.yaml（默认参数）
pipeline/        管线本体：fetch/（8 种抓取器）· parsers/（站点解析器）·
                 enrich/（市场数据）· analyze/（多供应商 AI 分析与报告）
app/             桌面壳：loopback 服务 · 钥匙串密钥 · 定时调度 · 菜单栏
site/            App 界面（纯静态无构建）：hash 路由七视图 + Claude 双主题
daily_reading/   Briefcase 打包入口 shim
scripts/         本地预览（preview.sh）· mock 数据 · 源文档生成
docs/            sources.md（信息源清单）· PACKAGING.md（打包与发布指南）
.github/workflows/   tests.yml（单测门禁）· release.yml（macOS 打包发布）
```

本地开发：

```bash
pip install -r requirements-app.txt
python -m pytest                # 103 个单测，全部离线 fixture
python -m app.server            # 浏览器开发模式：起本地服务 + 完整界面
python -m app.main              # 完整桌面壳（需 macOS）
python -m pipeline.cli run --mode test --skip-ai   # 手动跑一次管线（试点源）
```

打包与发布（`.dmg` 构建、签名公证、Mac App Store 清单）见 [docs/PACKAGING.md](docs/PACKAGING.md)。

## 成本参考

App 免费开源；唯一成本是你自己的 AI API 用量。以默认的 Claude + 省钱 Batch 模式、每日 600 条上限估算约 **$1.5–2/天**；可在设置面板降低条数上限、换更便宜的模型（如 DeepSeek）进一步压缩。可选的 twitterapi.io（X 全量拉取）约 $15–25/月，FRED 免费。

## 合规与免责声明

- 本机只存储每条内容 ≤500 字的工作摘录与 AI 分析，不存储、不展示文章全文；历史数据 180 天后自动瘦身。
- 行情组件由 [TradingView](https://www.tradingview.com/) 提供；贵金属基准价数据来自 LBMA/COMEX/上海黄金交易所公开渠道。
- 本项目全部输出（包括 AI 生成的评级、推演与关注清单）**仅供研究参考，不构成任何投资建议**。

## License

[MIT](LICENSE)
