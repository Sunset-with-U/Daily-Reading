# SETUP · MacBook 安装与配置指南（新手友好版）

三分钟装好，全部配置都在 App 的**设置面板**里完成——不需要编程经验，不需要碰 GitHub。

## 第 1 步 · 下载安装（约 1 分钟）

1. 打开本仓库的 **[Releases](../../releases)** 页，下载最新的 `Daily Reading-x.x.x.dmg`；
   （如果 Releases 还没有版本，去 **Actions → release → 最近一次绿色运行 → Artifacts** 下载 `Daily-Reading-macOS`，解压得到 `.dmg`。）
2. 双击打开 `.dmg`，把 **Daily Reading** 拖进「应用程序」。
3. **第一次打开必须：右键图标 → 打开 → 再点「打开」**（开源应用没有付费开发者签名，macOS 会拦一下，只需这一次，以后正常双击）。

打开后你会看到菜单栏出现 **DR** 图标——App 常驻在这里，关掉窗口也不会退出。

## 第 2 步 · 申请一个 AI 的 API Key（约 5 分钟，四选一）

App 支持四家 AI，任选一家（也可以都配，随时切换）：

| 供应商 | 申请入口 | 说明 |
|---|---|---|
| **Claude**（推荐，默认） | [console.anthropic.com](https://console.anthropic.com/) → Billing 充值 → API Keys | 分析质量最佳；⚠️ 建议在 Billing 里设置月度消费上限 |
| ChatGPT（OpenAI） | [platform.openai.com](https://platform.openai.com/) | 同样支持省钱 Batch 模式 |
| Gemini（Google） | [aistudio.google.com](https://aistudio.google.com/) | 有免费额度可先试用 |
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com/) | 最便宜，中文能力好 |

复制生成的 Key（只完整显示一次，先粘到备忘录）。

## 第 3 步 · 在设置面板里完成配置（约 2 分钟）

打开 App 窗口 → 顶部导航最右边的「**设置**」：

1. **API 密钥**区：把第 2 步的 Key 粘进对应供应商的输入框 → 点「保存」→ 左侧圆点变绿。
   密钥存进 **macOS 钥匙串**，界面永不回显明文，卸载 App 也不会泄露。
2. **AI 引擎**区：选你配了 Key 的供应商；「调用方式」按需选——
   - **实时**：跑完一条看一条，约半小时出全量结果；
   - **省钱 Batch**（Claude/ChatGPT 支持）：五折价格，等 30–75 分钟。
3. **信息源**区（可选）：120+ 源已按推荐配置开好，你可以按分类展开逐个勾选，或在底部一行添加自己的 RSS 源。
   - 想要财联社电报等 8 个中文快讯源：在「RSSHub 实例」填 `https://rsshub.app`（公共实例）或你自建的地址。
   - 想要 X（Twitter）精选账号流：去 [twitterapi.io](https://twitterapi.io/) 拿个 Key 粘进来（约 $15–25/月，不配则自动用免费 Telegram 快讯层顶替）。
   - 想要宏观数据面板：[FRED](https://fredaccount.stlouisfed.org/apikeys) 免费注册一个 Key 粘进来。
4. **运行**区：点「**立即运行**」跑第一班——首次全量抓取约 3–10 分钟，AI 分析视模式再等一会儿，完成后弹系统通知。

## 日常使用

- **全自动**：北京时间 07:00（早报）/ 20:00（晚报）自动运行。白天没开机？晚上打开 App 会自动补跑最近的一班，不重复花钱。
- **七个视图**：今日报告 / 信息流（筛选+搜索）/ 关注清单 / 市场快照 / 历史归档 / 源状态 / 设置；右上角一键切换明暗主题。
- **菜单栏**：DR 图标 → 打开看板 / 立即运行早报 / 立即运行晚报 / 退出。

## 花费控制

设置面板「AI 引擎」区的**每日 AI 条数上限**（默认 600）是总闸——调到 300 费用即减半。换 DeepSeek 或调低上限，可以把成本压到每天几毛钱。各家控制台都能实时查看用量。

## 常见问题

**Q：打开提示"无法验证开发者"？**
A：右键图标 → 打开 → 再点「打开」（只需一次）。或终端执行：
`xattr -dr com.apple.quarantine "/Applications/Daily Reading.app"`

**Q：运行完了但条目没有 AI 分析？**
A：检查设置面板——所选供应商的密钥圆点是否绿色；「源状态」视图可确认抓取正常。没配 Key 时管线照常抓取归档，只是跳过 AI 环节，补配后下一班自动分析。

**Q：某个信息源一直失败？**
A：正常现象——上百个源总有几个在改版。单源失败不影响其他源；「源状态」视图能看到每个源的最近状态，你可以在设置里把长期失败的源关掉。

**Q：我的数据存在哪？**
A：全部在本机 `~/Library/Application Support/Daily-Reading/`——`data/` 是每日产出，`config/` 是你的个性化配置。删除该目录即完全重置（钥匙串里的 Key 需在「钥匙串访问」中单独删除）。

**Q：报告是投资建议吗？**
A：不是。全部内容仅供研究参考，交易决策请自行判断。
