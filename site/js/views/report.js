// 今日报告视图：早/晚报切换 + 各章节 markdown 渲染 + 内嵌关注清单
import { api } from "../api.js";
import { esc, fmtTime, md } from "../format.js";

export async function mount(el, state) {
  const doc = await api.report(state.date);
  const editions = doc?.editions || {};
  const available = ["morning", "evening"].filter((e) => editions[e]);
  if (!available.length) {
    el.innerHTML = `<div class="empty">${esc(state.date)} 暂无报告
      <br><small>报告在每天北京时间 07:00 / 20:00 的管线运行后生成（需配置 ANTHROPIC_API_KEY）</small></div>`;
    return;
  }
  let edition = state.params.get("edition");
  if (!available.includes(edition)) edition = available[available.length - 1];
  render(el, state, editions, available, edition);
}

const E_NAME = { morning: "早报", evening: "晚报" };

function render(el, state, editions, available, edition) {
  const r = editions[edition];
  const tabs = available.map((e) =>
    `<button class="${e === edition ? "active" : ""}" data-ed="${e}">${E_NAME[e]}</button>`).join("");

  const sections = [
    ["要点速览", r.tldr_md],
    ["全球市场叙事", r.global_narrative_md],
    ["跨资产盘面", r.cross_asset_md],
  ];
  const marketSecs = (r.markets || [])
    .map((m) => `<section class="card report-section">
        <h2>${esc(m.market)}</h2><div class="md">${md(m.content_md)}</div></section>`).join("");
  const watch = (r.watchlist || []).map(watchCard).join("");
  const tail = [
    ["风险与日历", r.risks_calendar_md],
    ["情绪面画像", r.sentiment_md],
  ];

  el.innerHTML = `
    <div class="card report-hero">
      <div class="report-kicker">DAILY READING · ${esc(state.date)} ${E_NAME[edition]}</div>
      <h1 class="report-headline">${esc(r.headline || "")}</h1>
      <div class="report-meta">生成于 ${fmtTime(r.generated_at)} · 模型 ${esc(r.model || "")}
        · 输入 ${r.input_stats?.S ?? "?"}S / ${r.input_stats?.A ?? "?"}A / ${r.input_stats?.B ?? "?"}B</div>
    </div>
    <div class="edition-tabs">${tabs}</div>
    ${sections.map(([t, c]) => c ? `<section class="card report-section"><h2>${t}</h2>
      <div class="md">${md(c)}</div></section>` : "").join("")}
    ${marketSecs}
    ${watch ? `<section class="card report-section"><h2>今日重点关注</h2>
      <div class="watch-grid">${watch}</div></section>` : ""}
    ${tail.map(([t, c]) => c ? `<section class="card report-section"><h2>${t}</h2>
      <div class="md">${md(c)}</div></section>` : "").join("")}
    <p class="view-sub" style="margin-top:8px">
      文中 [编号] 对应当日 S/A 级信息条目，可在「信息流」页按重要性筛选回溯原文。AI 生成内容仅供研究参考，不构成投资建议。</p>`;

  el.querySelectorAll(".edition-tabs button").forEach((b) =>
    b.addEventListener("click", () => render(el, state, editions, available, b.dataset.ed)));
}

function watchCard(w) {
  return `<div class="card watch-card">
    <div class="watch-head">
      <span class="watch-symbol">${esc(w.symbol)}</span>
      <span class="watch-name">${esc(w.name_zh)}</span>
      <span class="badge dir dir-${esc(w.direction)} watch-type">${esc(w.direction)}</span>
      <span class="chip">${esc(w.type)}</span>
    </div>
    <div class="md">${md(w.view_md)}</div>
    ${w.key_levels ? `<div class="watch-levels"><b>关键位</b> ${esc(w.key_levels)}</div>` : ""}
  </div>`;
}
