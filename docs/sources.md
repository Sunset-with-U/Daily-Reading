# 信息源清单

> 本文档由 `scripts/gen_sources_doc.py` 从 `config/sources.yaml` 自动生成，请勿手改。

共 **128** 个源（启用 122 个），其中 X 主题组覆盖 **104** 个精选账号。

## 接入方式分布

| 方式 | 数量 | 说明 |
|---|---:|---|
| RSS/Atom | 63 | `rss` |
| Google News 兜底 | 16 | `google_news` |
| HTML 爬虫 | 15 | `html_scrape` |
| 播客（iTunes 解析） | 13 | `podcast_itunes` |
| X（twitterapi.io，需密钥） | 9 | `twitter` |
| 自建 RSSHub | 8 | `rsshub` |
| 公开 JSON API | 3 | `json_api` |
| Telegram 公开频道 | 1 | `telegram` |

## 分类明细

### 实时快讯 / X 精选（12）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| 财联社·电报（`cls-telegraph`） | A·核心 | 早晚 | 自建 RSSHub | ✅ | 快讯电报；官方接口需签名，走 RSSHub /cls/telegraph 路由（文档 confirmed）不自行实现签名 |
| FinancialJuice 快讯（`financialjuice-tg`） | A·核心 | 早晚 | Telegram 公开频道 | ✅ | 与 @DeItaone 同源的实时市场快讯；X 免费替代层 |
| 华尔街见闻·7×24 快讯（`wallstreetcn-lives`） | A·核心 | 早晚 | 公开 JSON API | ✅ | 公开 JSON API（confirmed，RSSHub 同源）；7×24 快讯流 |
| X·人工智能（`x-ai`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 14 账号；AI/ML 前沿与应用 |
| X·中国研究（`x-china`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 20 账号；中国政治经济研究者账号 |
| X·加密衍生品（`x-crypto`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 15 账号；加密衍生品/链上核心账号 |
| X·全球经济学家（`x-economists`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 7 账号；顶级经济学家 |
| X·外汇利率宏观（`x-fx-macro`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 17 账号；外汇/利率/流动性框架账号 |
| X·贵金属大宗（`x-metals`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 10 账号；黄金/美元体系/大宗周期账号 |
| X·量化通用（`x-quant`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 4 账号；量化与市场结构 |
| X·实时快讯（`x-squawk`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 5 账号；盘中快讯账号（免费替代为 FinancialJuice Telegram） |
| X·美股期权与波动率（`x-vol-options`） | B·标准 | 早晚 | X（twitterapi.io，需密钥） | ✅ | 12 账号；vol/gamma/期权流派核心账号 |

### 全球财经媒体（16）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| 彭博·经济（`bloomberg-economics`） | A·核心 | 早晚 | RSS/Atom | ✅ | 官方分栏 RSS（confirmed）；标题层，正文付费墙 |
| 彭博·市场（`bloomberg-markets`） | A·核心 | 早晚 | RSS/Atom | ✅ | 官方分栏 RSS；标题+摘要，正文付费墙 |
| 经济学人（`economist-gnews`） | A·核心 | 早晚 | Google News 兜底 | ✅ | 官方 RSS 2024 年起实质停供（confirmed）→ Google News site: 兜底；标题层，链接为谷歌跳转 |
| 金融时报·Alphaville（`ft-alphaville`） | A·核心 | 早晚 | RSS/Atom | ✅ | ?format=rss（confirmed）；正文注册免费但 feed 仅预览，抓全文需登录态（暂不做） |
| 金融时报·首页（`ft-home`） | A·核心 | 早晚 | RSS/Atom | ✅ | 官方首页 feed（confirmed）；标题层，正文硬付费墙 |
| 金融时报·市场（`ft-markets`） | A·核心 | 早晚 | RSS/Atom | ✅ | 任意栏目 ?format=rss 模式（confirmed）；标题层 |
| 日经亚洲（`nikkei-asia`） | A·核心 | 早晚 | RSS/Atom | ✅ | 官方 feed（confirmed）；标题层，正文付费墙 |
| 路透社（`reuters-gnews`） | A·核心 | 早晚 | Google News 兜底 | ✅ | 官方 RSS 2020 年已关（confirmed）→ Google News site: 兜底；标题层 |
| 华尔街日报·市场（`wsj-markets`） | A·核心 | 早晚 | RSS/Atom | ✅ | 道琼斯官方 feed；标题层 |
| 华尔街日报·国际（`wsj-world`） | A·核心 | 早晚 | RSS/Atom | ✅ | 道琼斯官方 feed（confirmed）；标题层，含 Lingling Wei 中国线报道标题 |
| 彭博·观点（`bloomberg-opinion`） | B·标准 | 早晚 | RSS/Atom | ✅ | 官方 Opinion 分栏 RSS（confirmed）；标题层，含 Matt Levine 等专栏标题 |
| 彭博·科技（`bloomberg-technology`） | B·标准 | 早晚 | RSS/Atom | ✅ | 官方分栏 RSS（confirmed）；标题层 |
| 金融时报·中国（`ft-china`） | B·标准 | 早晚 | RSS/Atom | ✅ | ?format=rss 模式套用到 china 栏目（unverified，CI 探活）；标题层 |
| 金融时报·全球经济（`ft-global-economy`） | B·标准 | 早晚 | RSS/Atom | ✅ | ?format=rss 模式（likely）；标题层 |
| 南华早报·中国（`scmp-china`） | B·标准 | 早晚 | RSS/Atom | ✅ | 栏目 ID 4=China 系社区常引用值（likely，CI 验证）；预览层 |
| 南华早报·新闻（`scmp-news`） | B·标准 | 早晚 | RSS/Atom | ✅ | 官方栏目 feed，91=news（confirmed）；预览层，计量付费墙 |

### 中文财经媒体（17）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| 财新网（`caixin`） | A·核心 | 早晚 | RSS/Atom | ✅ | 官方 Feedly 向 feed（confirmed 但更新稀疏）；标题层，付费墙严；备选 RSSHub caixin 路由/Telegram @caixin_web |
| 华尔街见闻·资讯（`wallstreetcn-global`） | A·核心 | 早晚 | 公开 JSON API | ✅ | 公开 JSON API（RSSHub 同源实现） |
| 21世纪经济报道（`21jingji-gnews`） | B·标准 | 早晚 | Google News 兜底 | ✅ | 无 RSS（unverified）→ Google News 兜底；监管动态快，标题层 |
| 36氪（`36kr`） | B·标准 | 早晚 | RSS/Atom | ✅ | 官方 feed，社区长期在用（unverified，CI 探活）；科技商业 |
| 财新国际（`caixin-global`） | B·标准 | 早晚 | Google News 兜底 | ✅ | 无官方 RSS（RSSHub issue |
| 观察者网（`guancha`） | B·标准 | 早晚 | 自建 RSSHub | ✅ | RSSHub /guancha/:category? 路由（文档 confirmed）；民族主义+发展主义视角，需识别框架立场 |
| 晚点 LatePost（`latepost`） | B·标准 | 早晚 | 自建 RSSHub | ✅ | RSSHub 晚点路由（unverified，CI 探活）；深度稿低频，部分付费 |
| 澎湃新闻（`thepaper-feedx`） | B·标准 | 早晚 | RSS/Atom | ✅ | 第三方全文聚合，Phase 2 补 RSSHub 主路由 |
| 澎湃新闻·RSSHub备用（`thepaper-rsshub`） | B·标准 | 早晚 | 自建 RSSHub | ⛔ 停用 | RSSHub 澎湃频道路由（文档 confirmed，频道 id 可换）；主路 feedx pilot 挂掉时启用 |
| 第一财经·英文（`yicai-global`） | B·标准 | 早晚 | Google News 兜底 | ✅ | 未发现 RSS（unverified）→ Google News 兜底；正文免费 |
| 第一财经（`yicai-latest`） | B·标准 | 早晚 | 自建 RSSHub | ✅ | RSSHub /yicai/latest 路由（文档 confirmed）；全文免费 |
| 半月谈（`banyuetan-gnews`） | C·尽力而为 | 早晚 | Google News 兜底 | ✅ | 新华社系基层刊物，站点无 feed（unverified）→ Google News 兜底；主阵地在微信，待 wechat2rss |
| 新京报（`bjnews-gnews`） | C·尽力而为 | 早晚 | Google News 兜底 | ✅ | 无稳定 RSS（unverified）→ Google News 兜底；时政与社会议题 |
| 财经杂志（`caijing-gnews`） | C·尽力而为 | 早晚 | Google News 兜底 | ✅ | 无 RSS（unverified）→ Google News 兜底 |
| 经济观察报（`eeo-gnews`） | C·尽力而为 | 早晚 | Google News 兜底 | ✅ | 周报节奏，无 RSS（unverified）→ Google News 兜底 |
| 虎嗅（`huxiu`） | C·尽力而为 | 早晚 | RSS/Atom | ✅ | 官方 rss/0.xml 历史存在（unverified，CI 探活）；失效则换 RSSHub /huxiu 路由 |
| 端传媒（`initium-gnews`） | C·尽力而为 | 早晚 | Google News 兜底 | ✅ | 付费墙，无公开 feed（unverified）→ Google News 标题层 |

### 中文官方与政策（17）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| 中央纪委·审查调查（`ccdi-shencha`） | A·核心 | 早晚 | 自建 RSSHub | ✅ | RSSHub 通用路由 /gov/ccdi/+路径（文档 confirmed，scdcn=审查调查）；反腐通报是体制风向核心信号 |
| 证监会·新闻发布（`csrc`） | A·核心 | 早晚 | HTML 爬虫 | ✅ | 静态 shtml 列表页（confirmed），常规 UA 可抓，全文可得 |
| 中国政府网·最新政策（`gov-cn-zhengce`） | A·核心 | 早晚 | 自建 RSSHub | ⛔ 停用 | CI 实测路由返回 503 route-is-empty（2026-07-12），改走 gov-cn-zhengceku 官方 JSON API；留此条目待 RSSHub 修复后再启用 |
| 国务院政策文件库（`gov-cn-zhengceku`） | A·核心 | 早晚 | 公开 JSON API | ✅ | 政策文件库前端背后 JSON 检索接口（unverified，具体参数待抓包，parser 用 JSON 拾荒器容错）；与 RSSHub zuixin 路由互补 |
| 中国人民银行·货币政策司（`pbc`） | A·核心 | 早晚 | HTML 爬虫 | ⛔ 停用 | 确认有 wzws JS 挑战 WAF（confirmed），requests 裸抓必败；待 Playwright/headless 方案（参考 PbcCrawler），数据面先用 akshare 兜底 |
| 求是（`qstheory-feedx`） | A·核心 | 早晚 | RSS/Atom | ✅ | 半月刊；FeedX 第三方全文源（likely，稳定性一般）；最高领导人重要文章首发地 |
| 人民日报（`rmrb-paper`） | A·核心 | 早报 | HTML 爬虫 | ✅ | 电子版按版面遍历，全文可得；每日凌晨更新 |
| 国家统计局·最新发布（`stats`） | A·核心 | 早晚 | HTML 爬虫 | ✅ | 新闻稿/解读列表页（confirmed）；数据本体走 akshare/easyquery，不在本管道 |
| 学习时报（`studytimes`） | A·核心 | 早报 | HTML 爬虫 | ✅ | 电子版周一/三/五出报（likely，URL 模板未验证）；干部教育核心刊物 |
| 新华网·财经（`xinhua-fortune`） | A·核心 | 早晚 | HTML 爬虫 | ✅ | 同上，财经频道列表页直抓（likely） |
| 新华网·时政（`xinhua-politics`） | A·核心 | 早晚 | HTML 爬虫 | ✅ | 中文站无可靠官方 RSS（likely）→ 频道列表页直抓，全文可得；重点看权威发布/新华时评 |
| 央视新闻联播·文字版（`xwlb`） | A·核心 | 晚报 | HTML 爬虫 | ✅ | 每日一页列当天条目（confirmed）；文字稿约 21 点齐全，晚报班次（北京20点）抓当日可能不全——已知坑 |
| 中央纪委·要闻（`ccdi-yaowen`） | B·标准 | 早晚 | 自建 RSSHub | ✅ | 同上通用路由，yaowenn 为站内要闻栏目路径（unverified，CI 探活） |
| 财政部·政务信息（`mof`） | B·标准 | 早晚 | HTML 爬虫 | ✅ | 政务信息列表页静态 HTML（likely）；附件多为 PDF——已知坑 |
| 发改委·政策发布（`ndrc`） | B·标准 | 早晚 | HTML 爬虫 | ✅ | 政策发布列表页（likely）；标准列表+详情两级抓取 |
| 求是网·网评（`qstheory-list`） | B·标准 | 早晚 | HTML 爬虫 | ✅ | 首页列表宽松匹配 /20260615/{hash}/c.html 型文章 URL（likely）；FeedX 挂掉时的兜底与日常网评来源 |
| 外汇局·新闻发布（`safe`） | B·标准 | 早晚 | HTML 爬虫 | ✅ | 列表页可抓（unverified）；同为金融监管系统站点，可能有与 pbc 同款 WAF——CI 先试 requests |

### 央行与监管（3）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| 日本银行·最新发布（`boj-whatsnew`） | A·核心 | 早晚 | RSS/Atom | ✅ | 官方英文 feed（confirmed）；政策声明/展望报告 |
| 欧央行·新闻稿（`ecb-press`） | A·核心 | 早晚 | RSS/Atom | ✅ | 官方 feed（confirmed）；全文免费 |
| 美联储·新闻稿（`fed-press`） | A·核心 | 早晚 | RSS/Atom | ✅ | 全部新闻稿；声明/纪要全文免费 |

### 学术研究（10）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| arXiv·量化金融（`arxiv-qfin`） | A·核心 | 早报 | RSS/Atom | ✅ | 官方 RSS，工作日每日更新 |
| NBER 工作论文（`nber-wp`） | A·核心 | 早报 | RSS/Atom | ✅ | 主站对数据中心 IP 返回 403，back.nber.org 为官方后端镜像 |
| arXiv·机器学习（`arxiv-cslg`） | B·标准 | 早报 | RSS/Atom | ✅ | 官方 RSS（confirmed）；量大，仅取头部；AI/ML 前沿 |
| 英央行·Bank Underground（`bank-underground`） | B·标准 | 早报 | RSS/Atom | ✅ | 英格兰银行研究员博客（likely）；免费全文 |
| 国际清算银行·论文（`bis-papers`） | B·标准 | 早报 | RSS/Atom | ✅ | BIS 论文列表 feed（unverified，BIS 有官方 feed 索引）；研究质量最高的国际机构 |
| 美联储·FEDS Notes（`feds-notes`） | B·标准 | 早报 | RSS/Atom | ✅ | 联储研究短文 feed（unverified，feeds 索引页确认存在系列 feed） |
| 纽约联储·自由街经济（`liberty-street`） | B·标准 | 早报 | RSS/Atom | ✅ | 纽联储研究博客，WordPress /feed/（likely）；免费全文 |
| SSRN·金融经济学（`ssrn-fin`） | B·标准 | 早晚 | RSS/Atom | ⛔ 停用 | SSRN 按 network 的 RSS 现状不明（unverified）；待人工确认 feed URL 后启用 |
| VoxChina（`voxchina`） | B·标准 | 每周 | Google News 兜底 | ✅ | 低频学术评论；无稳定 feed → Google News 兜底 |
| VoxEU（CEPR）（`voxeu`） | B·标准 | 早报 | RSS/Atom | ✅ | CEPR 政策评论 feed（likely）；顶级经济学家专栏，免费全文 |

### 智库与中国研究（13）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| 中国金融四十人论坛（`cf40`） | A·核心 | 早晚 | HTML 爬虫 | ✅ | 无 RSS（confirmed）；文章 URL 规律 /article/1/{id}，首页列表抓取；政策风向最准的非官方信号源 |
| 彼得森国际经济研究所（`piie`） | A·核心 | 早报 | RSS/Atom | ✅ | 官方 feed（likely）；国际经济政策第一智库，免费全文 |
| 荣鼎咨询（`rhodium`） | A·核心 | 早报 | RSS/Atom | ✅ | WordPress /feed/（likely）；数据驱动中国经济研究，note 免费深度报告部分收费 |
| 布鲁金斯学会（`brookings`） | B·标准 | 早报 | RSS/Atom | ✅ | WordPress /feed/（likely）；量大，AI 分级消化 |
| 卡内基中国中心（`carnegie-china`） | B·标准 | 每周 | HTML 爬虫 | ✅ | 2024 改版后旧 RSS 失效（unverified）→ 列表页抓取 |
| 外交关系委员会（`cfr-gnews`） | B·标准 | 早报 | Google News 兜底 | ✅ | 官方分博客 feed 较散 → Google News 兜底 |
| 查塔姆研究所（`chatham-house-gnews`） | B·标准 | 每周 | Google News 兜底 | ✅ | 官方 RSS 索引页存在但路径未核实 → 先 Google News |
| ChinaFile 中参馆（`chinafile-gnews`） | B·标准 | 早报 | Google News 兜底 | ✅ | 官方 RSS 未核实 → Google News 兜底；免费全文站 |
| 中国领导层观察（Hoover）（`clm-hoover`） | B·标准 | 每周 | Google News 兜底 | ✅ | 季刊（confirmed 免费）；无稳定 feed → Google News 兜底 |
| 战略与国际研究中心（`csis`） | B·标准 | 早报 | RSS/Atom | ✅ | 官方 rss-feeds 索引页确认有分栏 feed（具体路径 unverified，CI 探活） |
| 国际货币基金组织（`imf-news`） | B·标准 | 早报 | RSS/Atom | ✅ | 官方 RSS 索引确认（confirmed）；WEO/GFSR/Article IV 动态 |
| 墨卡托中国研究所（`merics`） | B·标准 | 每周 | HTML 爬虫 | ✅ | 无 RSS（unverified）→ 列表页抓取；欧洲最大中国研究所 |
| The Wire China（`wirechina-gnews`） | B·标准 | 早报 | Google News 兜底 | ✅ | 正文付费墙（confirmed），Google News 标题层兜底 |

### Newsletter 专栏（20）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| Chartbook（Adam Tooze）（`chartbook`） | A·核心 | 早晚 | RSS/Atom | ✅ | Substack 原生域（confirmed 模式）；宏观+经济史，多数免费全文 |
| ChinaTalk（`chinatalk`） | A·核心 | 早晚 | RSS/Atom | ✅ | Substack 自定义域（likely）；中美科技/AI/出口管制，含播客，免费+付费混合 |
| 边际革命（Tyler Cowen）（`marginal-revolution`） | A·核心 | 早晚 | RSS/Atom | ✅ | WordPress 全文 RSS（confirmed）；日更多帖，经济学界高信号博客 |
| Pekingnology（王子琛）（`pekingnology`） | A·核心 | 早晚 | RSS/Atom | ✅ | Substack（likely，备选 pekingnology.substack.com/feed）；免费全文，翻译中文政策文件 |
| Sinocism（Bill Bishop）（`sinocism`） | A·核心 | 早晚 | RSS/Atom | ✅ | Substack 自定义域 /feed（likely）；付费为主，feed 为预览；英文中国政治日报 No.1 |
| Apricitas（Joseph Politano）（`apricitas`） | B·标准 | 早晚 | RSS/Atom | ✅ | Substack（likely）；FRED/BLS 数据讲美国宏观，基本免费全文 |
| Astral Codex Ten（`astral-codex-ten`） | B·标准 | 早报 | RSS/Atom | ✅ | Substack（likely）；思维训练类，免费为主 |
| Bits about Money（Patrick McKenzie）（`bits-about-money`） | B·标准 | 早报 | RSS/Atom | ✅ | Ghost 站标准 /rss/（likely）；支付/银行/合规内部视角，免费全文 |
| Concoda（`concoda`） | B·标准 | 早报 | RSS/Atom | ✅ | Substack（likely）；美元/repo 市场微观结构 |
| Import AI（Jack Clark）（`import-ai`） | B·标准 | 早报 | RSS/Atom | ✅ | Substack（likely）；AI policy/safety 周报，免费全文 |
| Latent Space（swyx）（`latent-space`） | B·标准 | 早报 | RSS/Atom | ✅ | Substack（likely）；AI 工程实践，含播客，免费为主 |
| The Macro Compass（Alf Peccatiello）（`macro-compass`） | B·标准 | 早报 | RSS/Atom | ✅ | Substack 原生域（confirmed 活跃）；付费为主，feed 出预览 |
| Money Stuff（Matt Levine）（`money-stuff`） | B·标准 | 早晚 | RSS/Atom | ⛔ 停用 | 邮件免费但 Bloomberg 网页存档付费；NewsletterHunt 镜像 feed 待核实（unverified）——启用前先人工确认；标题层已由 bloomberg-opinion 覆盖 |
| Net Interest（Marc Rubinstein）（`net-interest`） | B·标准 | 早报 | RSS/Atom | ✅ | Substack（likely）；银行/资管深度，周更免费文全文 |
| Noahpinion（Noah Smith）（`noahpinion`） | B·标准 | 早晚 | RSS/Atom | ✅ | Substack 自定义域（likely）；应用经济学+东亚，免费文多 |
| One Useful Thing（Ethan Mollick）（`one-useful-thing`） | B·标准 | 早报 | RSS/Atom | ✅ | Substack（likely）；AI 应用，免费全文 |
| Sinification（`sinification`） | B·标准 | 早晚 | RSS/Atom | ✅ | Substack（likely）；翻译中国学者文章，免费全文 |
| Stratechery（Ben Thompson）（`stratechery`） | B·标准 | 早报 | RSS/Atom | ✅ | 公共 WordPress feed 含免费周文全文（likely）；付费日更需订阅者 Passport feed（可日后放 Secret） |
| The Diff（Byrne Hobart）（`the-diff`） | B·标准 | 早晚 | RSS/Atom | ✅ | Substack（likely）；付费为主 feed 出预览；金融×科技交叉分析 |
| Trivium China（`trivium-china`） | B·标准 | 早晚 | RSS/Atom | ⛔ 停用 | 免费产品仅邮件投递（confirmed）；此 feed 仅站上偶发文章。待邮箱+IMAP 方案再启用 |

### 加密与链上（7）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| Arthur Hayes 博客（`arthur-hayes`） | A·核心 | 早报 | RSS/Atom | ✅ | Substack（confirmed 活跃）；宏观+加密长文，免费全文 |
| Glassnode·链上周报（`glassnode-insights`） | A·核心 | 早报 | RSS/Atom | ✅ | Ghost 博客 RSS（confirmed）；The Week On-chain 免费全文 |
| CoinDesk（`coindesk`） | B·标准 | 早晚 | RSS/Atom | ✅ |  |
| Deribit·期权研究（`deribit-insights`） | B·标准 | 早报 | RSS/Atom | ✅ | WordPress /feed/（likely）；被 Coinbase 收购后更新趋缓，观察 |
| Paradigm 研究（`paradigm-research`） | B·标准 | 早报 | RSS/Atom | ✅ |  |
| The Block（`theblock`） | B·标准 | 早晚 | RSS/Atom | ✅ | 官方 feed（confirmed）；新闻免费（feed 为摘要），Research 付费 |
| 吴说区块链（英文版）（`wu-blockchain`） | B·标准 | 早晚 | RSS/Atom | ✅ | Substack（likely，子域名待 CI 核实）；亚洲加密新闻密度高 |

### 播客（13）

| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |
|---|---|---|---|---|---|
| Odd Lots（Bloomberg）（`pod-odd-lots`） | A·核心 | 早报 | 播客（iTunes 解析） | ✅ | 官方 feed（confirmed）；全球宏观访谈第一 |
| Acquired（`pod-acquired`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | Transistor 官方 feed（likely）；商业案例深度 |
| Capital Allocators（Ted Seides）（`pod-capital-allocators`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | 顶级 LP/GP 访谈 |
| Flirting with Models（Corey Hoffstein）（`pod-flirting-models`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | 量化策略深访；季节性更新 |
| Forward Guidance（Blockworks）（`pod-forward-guidance`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | iTunes 搜索解析（宏观+加密交叉访谈） |
| 忽左忽右（`pod-huzuohuyou`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | JustPod 出品；历史+国际+人文 |
| Invest Like the Best（`pod-invest-like-best`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | Colossus 网络；顶级投资者访谈 |
| MacroVoices（`pod-macro-voices`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | iTunes ID（confirmed）→ Lookup 解析真实 feed |
| 商业就是这样（`pod-shangye-jiushi`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | 商业深度叙事 |
| 声东击西（`pod-shengdongjixi`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | Typlog 直连 feed（likely，失败则改 search:声东击西,cn） |
| Sinica（Kaiser Kuo）（`pod-sinica`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | 中国研究老牌播客；已迁 Substack |
| Top Traders Unplugged（`pod-top-traders`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | CTA/系统化交易访谈 |
| 张小珺·商业访谈录（`pod-zhangxiaojun`） | B·标准 | 早报 | 播客（iTunes 解析） | ✅ | AI 产业访谈密度高；主发小宇宙，Apple 同步 |

## 维护约定

- 新增/调整源只改 `config/sources.yaml`，然后重跑本脚本更新文档。
- `tier`：A=必读核心，B=标准监控，C=尽力而为（失败不告警）。
- 每周一的 `source-health` 工作流探活全部源（含停用源），连败 3 次以上的源会在
  「源健康周报」Issue 中被点名，建议停用或更换接入方式。
- X 主题组仅在配置了 `TWITTERAPI_IO_KEY` Secret 时启用，未配置时自动跳过。
