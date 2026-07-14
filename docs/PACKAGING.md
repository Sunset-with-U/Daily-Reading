# 打包与发布指南（macOS 桌面 App）

本项目的桌面形态用 [Briefcase](https://briefcase.readthedocs.io/) 打包为原生 `.app` / `.dmg`。
配置在仓库根 `pyproject.toml`；云端数据管线（`daily.yml` / `health.yml`）与打包互不相干。

## 一、本地开发运行（不打包）

```bash
pip install -r requirements-app.txt
python -m app.main          # 完整桌面壳（窗口 + 菜单栏 + 定时）
python -m app.server        # 只起本地服务，浏览器打开打印出的地址（开发设置面板用）
```

## 二、本地打包

在 macOS 上：

```bash
pip install briefcase
briefcase create macOS      # 拉模板 + 装依赖（首次较慢）
briefcase build macOS       # 生成 build/…/Daily Reading.app
briefcase package macOS --adhoc-sign   # 生成 dist/Daily Reading-<版本>.dmg
```

- Apple Silicon 机器打出 arm64 包，Intel 机器打出 x86_64 包（`universal_build`
  关闭是刻意的：pandas/numpy/lxml 不提供 universal2 轮子，通用构建必失败）。
- 改版本号：`pyproject.toml` 的 `version` 与 `app/server.py` 的
  `AppState.version` 两处同步。

## 三、CI 发布通道（release.yml）

| 触发方式 | 产物去向 |
|---|---|
| Actions 页面手动 **Run workflow** | Actions artifact（`Daily-Reading-macOS`）|
| 推送 `v*` 标签（如 `git tag v2.0.0 && git push origin v2.0.0`）| artifact + **draft Release** 挂 `.dmg`，检查后手动发布 |

runner 是 `macos-14`（Apple Silicon），产物为 arm64 `.dmg`。

## 四、无证书（ad-hoc 签名）安装说明

CI 与本地默认 `--adhoc-sign`，没有开发者证书也能分发，但 Gatekeeper 会拦截首次打开：

1. 打开 `.dmg`，把 **Daily Reading** 拖进「应用程序」；
2. **右键 → 打开 → 再点“打开”**（只需一次，之后正常双击）；
   或终端执行 `xattr -dr com.apple.quarantine "/Applications/Daily Reading.app"`。

## 五、接入 Developer ID 签名与公证（后续可选）

有了 Apple Developer 账号（$99/年）后：

1. 在 Keychain 里装好 **Developer ID Application** 证书；
2. 本地打包改用：
   ```bash
   briefcase package macOS -i "Developer ID Application: 你的名字 (TEAMID)"
   ```
   Briefcase 会自动走 `notarytool` 公证 + staple（需先
   `xcrun notarytool store-credentials`）；
3. CI 自动化：把证书 p12 与 App Store Connect API Key 存入仓库 secrets
   （`MACOS_CERT_P12` / `MACOS_CERT_PASSWORD` / `NOTARY_KEY_*`），在
   `release.yml` 打包步骤前导入 Keychain 并替换 `--adhoc-sign` 为 `-i "…"`。
   接入前 ad-hoc 通道保持可用。

## 六、Mac App Store 提交清单（潜在准备）

架构上已按沙盒友好设计（loopback 服务、Keychain、Application Support 路径），
真正提交时按此清单补齐：

- [ ] **证书**：Apple Distribution + Mac Installer Distribution；打包改
      `briefcase package macOS --app-store`（配套证书标识）
- [ ] **App Sandbox**：`pyproject.toml` 增加
      `entitlement."com.apple.security.app-sandbox" = true`
      （`network.client` / `network.server` 已备好）
- [ ] **通知**：`app/notify.py` 从 osascript 换 `UNUserNotificationCenter`
      （沙盒内 osascript 不可用；文件内已留 TODO）
- [ ] **隐私清单**：`PrivacyInfo.xcprivacy`（声明网络域名与 UserDefaults 等
      required-reason API；本 App 不采集用户数据）
- [ ] **Keychain**：沙盒下补 `keychain-access-groups` entitlement
- [ ] **远程内容说明**：审核备注中说明 TradingView 图表为远程嵌入内容、
      信息源为公开 RSS/API，AI 分析需用户自备 API Key
- [ ] **审核账号**：提供一个预置了测试 Key 的演示说明（审核员没有 AI Key
      时 App 也能正常浏览已有数据——fail-open 设计天然满足）

## 七、用户 MacBook 验收清单（首次安装）

按顺序验证，全部通过即视为发布可用：

- [ ] 下载 `.dmg` → 拖入「应用程序」→ 右键打开（见第四节）
- [ ] 首启自动创建 `~/Library/Application Support/Daily-Reading/{data,config,logs}`
- [ ] 菜单栏出现 **DR** 图标；关闭窗口后 App 仍常驻（菜单栏「打开看板」可唤回）
- [ ] 设置面板保存 `ANTHROPIC_API_KEY`：「钥匙串访问」搜索 *Daily-Reading*
      可见条目；界面密钥点变绿且永不回显明文
- [ ] 设置 → 手动运行（自动判断班次）：test 管线跑通，看板出现当日数据
- [ ] 到北京 07:00 / 20:00 自动运行；App 白天关着、晚上打开时自动补跑晚报
- [ ] 运行完成弹系统通知
- [ ] 浅色/深色主题切换正常；6 个数据视图 + 设置视图均可用
