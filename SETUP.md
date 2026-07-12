# SETUP · 部署指南（新手友好版）

照着下面四步做，就能让这套系统每天自动为你工作。全程只需要浏览器，大约 15 分钟。

> 名词速览：**Secret** = 存在 GitHub 仓库里的加密密钥，工作流运行时才能读到，任何人（包括访客）都看不见；**Actions** = GitHub 提供的免费定时任务机器人；**Pages** = GitHub 提供的免费静态网站托管。

---

## 第 1 步 · 申请 Claude API Key（必须，约 5 分钟）

这是整套系统唯一需要花钱的部分（约 $35–50/月，可随时调低）。

1. 打开 [console.anthropic.com](https://console.anthropic.com/) 注册账号。
2. 左侧菜单 **Billing** → 充值（建议先充 $25 试运行）。
3. ⚠️ **强烈建议**：在 Billing 里设置 **月度消费上限**（如 $60），从根上杜绝意外账单。
4. 左侧菜单 **API Keys** → **Create Key**，名字随便起（如 `daily-reading`）。
5. 复制生成的 Key（以 `sk-ant-` 开头）。**它只完整显示这一次**，先粘到备忘录里。

## 第 2 步 · 申请 FRED API Key（必须，免费，约 3 分钟）

FRED 是圣路易斯联储的宏观数据库，看板的宏观数据面板靠它。

1. 打开 [fredaccount.stlouisfed.org/apikeys](https://fredaccount.stlouisfed.org/apikeys) 注册（免费）。
2. 点 **Request API Key**，用途随便填（如 personal research）。
3. 复制那串 32 位字符。

## 第 3 步 · 把密钥存进仓库 Secrets（约 3 分钟）

1. 打开你的仓库页面 → 顶部 **Settings**（⚙️ 设置）。
2. 左侧 **Secrets and variables** → **Actions** → 绿色按钮 **New repository secret**。
3. 依次添加（Name 必须一字不差，全大写）：

| Name | Secret 值 | 必须？ |
|---|---|---|
| `ANTHROPIC_API_KEY` | 第 1 步的 `sk-ant-...` | ✅ 必须 |
| `FRED_API_KEY` | 第 2 步的 32 位字符 | ✅ 必须 |
| `TWITTERAPI_IO_KEY` | [twitterapi.io](https://twitterapi.io/) 的 Key | 可选 |

> 关于可选的 X（Twitter）拉取：不配置时系统自动跳过 X 源，用免费的 Telegram 快讯层顶替，一切照常。哪天想开了，去 twitterapi.io 充值拿 Key 填进来即可，**不用改任何代码**，下一班自动生效（104 个精选账号，约 $15–25/月）。

## 第 4 步 · 启用 GitHub Pages（约 1 分钟）

1. 仓库 **Settings** → 左侧 **Pages**。
2. **Source** 下拉框选 **GitHub Actions**（不是 "Deploy from a branch"）。
3. 完成。下次管线运行后，看板就会出现在：
   `https://<你的用户名>.github.io/Daily-Reading/`

---

## 首次运行与日常节奏

- **自动**：合并到主分支后，管线每天自动跑两班——UTC 23:00（北京早上 7 点，早报）和 UTC 12:00（北京晚上 8 点，晚报），跑完约 20–90 分钟后看板更新。
- **手动**：仓库 **Actions** 标签页 → 左侧选 **daily-pipeline** → 右侧 **Run workflow**，参数全部留默认直接点绿色按钮即可。第一次建议手动跑一次验证全链路。
  - 小贴士：**Run workflow 按钮只在工作流文件进入主分支后才会出现**；开发分支阶段，往分支推任意提交也会触发一次测试运行。
- **每周一**：`source-health` 工作流自动探活全部信息源，并把结果写进一个叫「源健康周报」的 Issue，哪个源挂了、挂了几周、建议禁用谁，一目了然。

## 花费控制在哪里调

打开 `config/settings.yaml`（网页上直接点编辑就行）：

| 想省钱 | 改这里 |
|---|---|
| 少分析点条目 | `ai.daily_item_cap: 600` 调低（如 300） |
| 报告降档（约省一半报告费） | `ai.report_model` 改成 `claude-sonnet-5` |
| 缩短送给 AI 的正文 | `fetch.content_truncate_chars: 4000` 调低 |
| 每源少抓几条 | `fetch.max_items_per_source: 30` 调低 |

改完提交，下一班自动生效。Anthropic 控制台的 **Usage** 页可以随时核对实际花费。

## 常见问题

**Q：Actions 里 "部署 Pages" 一步红了？**
A：多半是第 4 步没做（Pages 的 Source 没选 GitHub Actions）。这一步失败不影响数据管线，配好后下一班自动恢复。

**Q：日志里出现「跳过：未配置 ANTHROPIC_API_KEY」？**
A：第 3 步的 Secret 名字打错了或没加。注意必须全大写、无空格。

**Q：某个信息源一直失败？**
A：正常现象——上百个源总有几个在改版或抽风。管线单源隔离，不影响其他源；周一的「源健康周报」会点名连续失败的源，可以在 `config/sources.yaml` 里把它 `enabled: false` 掉。

**Q：想加/减信息源、改自选清单？**
A：源在 `config/sources.yaml`，自选在 `config/watchlist.yaml`，都是带注释的纯文本，照着已有条目的格式增删即可。

**Q：报告是投资建议吗？**
A：不是。全部内容仅供研究参考，交易决策请自行判断。
