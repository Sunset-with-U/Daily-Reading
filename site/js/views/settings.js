// 设置视图（仅 App 模式）：AI 引擎 / API 密钥 / 信息源 / 运行控制
import { appApi } from "../api.js";
import { esc } from "../format.js";

// 仅展示名；密钥环境变量名与 Batch 能力位由 /api/status 的 providers 元数据下发
const PROVIDERS = [
  { id: "anthropic", name: "Claude（Anthropic）" },
  { id: "openai", name: "ChatGPT（OpenAI）" },
  { id: "gemini", name: "Gemini（Google）" },
  { id: "deepseek", name: "DeepSeek" },
];
const SOURCE_KEYS = [
  { name: "TWITTERAPI_IO_KEY", label: "twitterapi.io（X/Twitter 全量拉取，可选）" },
  { name: "FRED_API_KEY", label: "FRED（宏观数据，免费注册）" },
];
const CATEGORY_ZH = {
  squawk: "实时快讯 / X", global_media: "全球财经媒体", cn_media: "中文财经媒体",
  cn_official: "中文官方与政策", central_bank: "央行与监管", academic: "学术研究",
  thinktank: "智库与中国研究", newsletter: "Newsletter", crypto: "加密与链上",
  podcast: "播客",
};

export async function mount(el, state) {
  let status, settings, sourcesDoc;
  try {
    [status, settings, sourcesDoc] = await Promise.all([
      appApi.status(), appApi.settings(), appApi.sources(),
    ]);
  } catch (err) {
    el.innerHTML = `<div class="empty">无法连接本地服务：${esc(err.message)}</div>`;
    return;
  }
  if (!status) {
    el.innerHTML = '<div class="empty">设置面板仅在桌面 App 中可用</div>';
    return;
  }

  const ai = settings.ai || {};
  const models = ai.models || {};
  const sched = settings.schedule || {};
  const provMeta = status.providers || {};
  const overlay = sourcesDoc.overlay || {};
  overlay.overrides = overlay.overrides || {};
  overlay.extra_sources = overlay.extra_sources || [];

  el.innerHTML = `
    <h1 class="view-title">设置</h1>
    <p class="view-sub">配置只保存在本机（密钥存入 macOS 钥匙串，其余写入用户配置目录）</p>

    <div class="card settings-card">
      <h2>AI 引擎</h2>
      <div class="form-row">
        <label>AI 供应商</label>
        <select id="set-provider">
          ${PROVIDERS.map((p) => `<option value="${p.id}" ${ai.provider === p.id ? "selected" : ""}>${p.name}</option>`).join("")}
        </select>
      </div>
      <div class="form-row">
        <label>调用方式</label>
        <select id="set-mode">
          <option value="realtime" ${ai.mode === "realtime" ? "selected" : ""}>实时（逐条即时可见）</option>
          <option value="batch" ${ai.mode !== "realtime" ? "selected" : ""}>省钱模式 Batch（5 折，等 30-75 分钟）</option>
        </select>
        <span class="form-hint" id="mode-hint"></span>
      </div>
      <div class="form-row"><label>逐条分析模型</label><input id="set-model-item" type="text"></div>
      <div class="form-row"><label>每日报告模型</label><input id="set-model-report" type="text"></div>
      <div class="form-row"><label>每日 AI 条数上限</label>
        <input id="set-cap" type="number" min="0" value="${ai.daily_item_cap ?? 600}">
        <span class="form-hint">成本护栏：每天最多送 AI 分析的条目数</span></div>
      <div class="form-actions">
        <button class="btn btn-primary" id="save-ai">保存 AI 设置</button>
        <span class="save-note" id="ai-note"></span>
      </div>
    </div>

    <div class="card settings-card">
      <h2>API 密钥</h2>
      <p class="form-hint">密钥保存进 macOS 钥匙串，界面永不回显明文。只需配置你选用的供应商。</p>
      ${[...PROVIDERS.filter((p) => provMeta[p.id])
          .map((p) => ({ name: provMeta[p.id].env, label: p.name })), ...SOURCE_KEYS]
        .map((k) => keyRow(k, status.keys)).join("")}
    </div>

    <div class="card settings-card">
      <h2>信息源</h2>
      <div class="form-row">
        <label>RSSHub 实例</label>
        <input id="set-rsshub" type="text" value="${esc((settings.fetch || {}).rsshub_base || "")}"
               placeholder="https://rsshub.app（财联社/财新等 8 个源需要）">
        <button class="btn" id="save-rsshub">保存</button>
        <span class="save-note" id="rsshub-note"></span>
      </div>
      <div class="form-row">
        <input id="src-filter" type="text" placeholder="筛选源名称 / id …" style="max-width:280px">
        <span class="form-hint">共 ${sourcesDoc.sources.length} 个源；取消勾选即停用，下轮运行生效</span>
      </div>
      <div id="src-list" class="src-list"></div>
      <h3>添加自定义源（RSS）</h3>
      <div class="form-row">
        <input id="new-src-name" type="text" placeholder="名称（如 我的博客）" style="max-width:180px">
        <input id="new-src-url" type="text" placeholder="RSS 地址 https://…/feed" style="flex:1">
        <button class="btn" id="add-src">添加</button>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" id="save-sources">保存信息源设置</button>
        <span class="save-note" id="src-note"></span>
      </div>
    </div>

    <div class="card settings-card">
      <h2>运行与定时</h2>
      <div class="form-row">
        <label>手动运行</label>
        <select id="run-edition">
          <option value="">自动判断班次</option>
          <option value="morning">早报</option>
          <option value="evening">晚报</option>
        </select>
        <button class="btn btn-primary" id="run-now">立即运行</button>
        <span class="save-note" id="run-note"></span>
      </div>
      <div class="form-row">
        <label>早报时间</label>
        <input id="set-hour-m" type="number" min="0" max="23" class="hour-input"
               value="${sched.morning_hour ?? 7}">
        <span class="form-hint">点（北京时间整点）</span>
      </div>
      <div class="form-row">
        <label>晚报时间</label>
        <input id="set-hour-e" type="number" min="0" max="23" class="hour-input"
               value="${sched.evening_hour ?? 20}">
        <span class="form-hint">点；两班请错开。到点自动抓取分析并推送通知，错过班次开机自动补</span>
      </div>
      <div class="form-actions">
        <button class="btn" id="save-sched">保存定时</button>
        <span class="save-note" id="sched-note"></span>
      </div>
      <p class="form-hint" id="sched-line"></p>
    </div>`;

  // —— AI 段 ——
  const modelInputs = () => {
    const p = el.querySelector("#set-provider").value;
    const m = models[p] || {};
    el.querySelector("#set-model-item").value = m.item || "";
    el.querySelector("#set-model-report").value = m.report || "";
    el.querySelector("#mode-hint").textContent =
      provMeta[p] && !provMeta[p].batch
        ? "该供应商暂不支持 Batch，省钱模式将自动按实时执行" : "";
  };
  modelInputs();
  el.querySelector("#set-provider").addEventListener("change", modelInputs);
  el.querySelector("#save-ai").addEventListener("click", async () => {
    const provider = el.querySelector("#set-provider").value;
    const patch = { ai: {
      provider,
      mode: el.querySelector("#set-mode").value,
      daily_item_cap: Number(el.querySelector("#set-cap").value) || 0,
      models: { [provider]: {
        item: el.querySelector("#set-model-item").value.trim(),
        report: el.querySelector("#set-model-report").value.trim(),
      } },
    } };
    await save(el.querySelector("#ai-note"), () => appApi.saveSettings(patch));
  });

  // —— 密钥段 ——
  el.querySelectorAll(".key-save").forEach((btn) => btn.addEventListener("click", async () => {
    const name = btn.dataset.key;
    const input = el.querySelector(`input[data-key-input="${name}"]`);
    if (!input.value.trim()) return;
    const note = el.querySelector(`.save-note[data-key-note="${name}"]`);
    await save(note, async () => {
      const st = await appApi.saveKey(name, input.value.trim());
      input.value = "";
      setKeyDot(el, name, st[name]);
    });
  }));
  el.querySelectorAll(".key-del").forEach((btn) => btn.addEventListener("click", async () => {
    const name = btn.dataset.key;
    const note = el.querySelector(`.save-note[data-key-note="${name}"]`);
    await save(note, async () => {
      const st = await appApi.deleteKey(name);
      setKeyDot(el, name, st[name]);
    }, "已删除");
  }));

  // —— 信息源段 ——
  const listEl = el.querySelector("#src-list");
  const renderSources = () => {
    const q = el.querySelector("#src-filter").value.trim().toLowerCase();
    const groups = {};
    for (const s of sourcesDoc.sources) {
      if (q && !(`${s.name_zh} ${s.id}`.toLowerCase().includes(q))) continue;
      (groups[s.category] = groups[s.category] || []).push(s);
    }
    listEl.innerHTML = Object.entries(groups).map(([cat, srcs]) => `
      <details class="src-group" ${q ? "open" : ""}>
        <summary>${esc(CATEGORY_ZH[cat] || cat)}（${srcs.filter((s) => effectiveEnabled(s)).length}/${srcs.length} 启用）</summary>
        ${srcs.map((s) => `
          <label class="src-row">
            <input type="checkbox" data-src="${esc(s.id)}" ${effectiveEnabled(s) ? "checked" : ""}>
            <span class="src-name">${esc(s.name_zh)}</span>
            <span class="src-meta">${esc(s.id)} · ${esc(s.method)}${s.notes ? " · " + esc(s.notes) : ""}</span>
          </label>`).join("")}
      </details>`).join("") || '<div class="empty">无匹配的源</div>';
    listEl.querySelectorAll("input[data-src]").forEach((cb) => cb.addEventListener("change", () => {
      const id = cb.dataset.src;
      overlay.overrides[id] = { ...(overlay.overrides[id] || {}), enabled: cb.checked };
    }));
  };
  const effectiveEnabled = (s) => {
    const o = overlay.overrides[s.id];
    return o && "enabled" in o ? o.enabled : s.enabled;
  };
  renderSources();
  el.querySelector("#src-filter").addEventListener("input", renderSources);

  el.querySelector("#add-src").addEventListener("click", () => {
    const name = el.querySelector("#new-src-name").value.trim();
    const url = el.querySelector("#new-src-url").value.trim();
    if (!name || !url) return;
    const id = "user-" + name.toLowerCase().replace(/[^a-z0-9一-鿿]+/g, "-").slice(0, 30);
    const entry = { id, name, name_zh: name, method: "rss", url,
                    category: "newsletter", tier: "C" };
    overlay.extra_sources.push(entry);
    sourcesDoc.sources.push({ ...entry, enabled: true, schedule: "both", notes: "自定义源" });
    el.querySelector("#new-src-name").value = el.querySelector("#new-src-url").value = "";
    renderSources();
  });

  el.querySelector("#save-sources").addEventListener("click", async () => {
    await save(el.querySelector("#src-note"), () => appApi.saveSources({
      overrides: overlay.overrides, extra_sources: overlay.extra_sources,
    }));
  });
  el.querySelector("#save-rsshub").addEventListener("click", async () => {
    await save(el.querySelector("#rsshub-note"), () => appApi.saveSettings({
      fetch: { rsshub_base: el.querySelector("#set-rsshub").value.trim() },
    }));
  });

  // —— 运行段 ——
  const schedLine = () => {
    const sc = status.scheduler || {};
    el.querySelector("#sched-line").textContent = sc.next_run
      ? `下次自动运行：${sc.next_run}${sc.running ? "（正在运行中…）" : ""}`
      : "自动定时将在 App 常驻后启用（北京 07:00 早报 / 20:00 晚报）";
  };
  schedLine();
  el.querySelector("#run-now").addEventListener("click", async () => {
    await save(el.querySelector("#run-note"), () =>
      appApi.run(el.querySelector("#run-edition").value), "已加入队列，完成后会收到通知");
  });
  el.querySelector("#save-sched").addEventListener("click", async () => {
    const clamp = (v, d) => { const n = Number(v); return Number.isInteger(n) && n >= 0 && n <= 23 ? n : d; };
    await save(el.querySelector("#sched-note"), () => appApi.saveSettings({
      schedule: {
        morning_hour: clamp(el.querySelector("#set-hour-m").value, 7),
        evening_hour: clamp(el.querySelector("#set-hour-e").value, 20),
      },
    }), "已保存，下一次检查即生效");
  });
}

function keyRow(k, keyStatus) {
  const set = !!keyStatus[k.name];
  return `
    <div class="form-row key-row">
      <span class="key-dot ${set ? "key-set" : ""}" data-key-dot="${k.name}"
            title="${set ? "已配置" : "未配置"}"></span>
      <label>${esc(k.label)}</label>
      <input type="password" placeholder="${set ? "已配置（输入新值可替换）" : "粘贴 API Key"}"
             data-key-input="${k.name}" autocomplete="off">
      <button class="btn key-save" data-key="${k.name}">保存</button>
      <button class="btn key-del" data-key="${k.name}" ${set ? "" : "disabled"}>删除</button>
      <span class="save-note" data-key-note="${k.name}"></span>
    </div>`;
}

function setKeyDot(el, name, isSet) {
  const dot = el.querySelector(`[data-key-dot="${name}"]`);
  dot.classList.toggle("key-set", !!isSet);
  dot.title = isSet ? "已配置" : "未配置";
  const del = el.querySelector(`.key-del[data-key="${name}"]`);
  if (del) del.disabled = !isSet;
}

async function save(noteEl, fn, okText = "已保存") {
  noteEl.textContent = "…";
  noteEl.classList.remove("save-err");
  try {
    await fn();
    noteEl.textContent = okText;
    setTimeout(() => { if (noteEl.textContent === okText) noteEl.textContent = ""; }, 3000);
  } catch (err) {
    noteEl.textContent = `失败：${err.message}`;
    noteEl.classList.add("save-err");
  }
}
