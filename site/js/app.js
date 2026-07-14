// 外壳：hash 路由 + 日期状态 + 主题 + Ticker Tape
import { api, appApi } from "./api.js";
import { initTheme } from "./theme.js";
import { tv } from "./widgets.js";
import * as reportView from "./views/report.js";
import * as feedView from "./views/feed.js";
import * as watchlistView from "./views/watchlist.js";
import * as marketView from "./views/market.js";
import * as archiveView from "./views/archive.js";
import * as sourcesView from "./views/sources.js";
import * as settingsView from "./views/settings.js";

const VIEWS = {
  report: reportView, feed: feedView, watchlist: watchlistView,
  market: marketView, archive: archiveView, sources: sourcesView,
  settings: settingsView,
};

const state = {
  index: null,          // data/index.json
  dates: [],            // 可用日期（新→旧）
  date: null,           // 当前查看日期
  route: "report",
  params: new URLSearchParams(),
  watchlistConf: null,
};

function parseHash() {
  const hash = location.hash.replace(/^#\/?/, "") || "report";
  const [path, query = ""] = hash.split("?");
  state.route = VIEWS[path] ? path : "report";
  state.params = new URLSearchParams(query);
  const d = state.params.get("date");
  if (d && state.dates.includes(d)) state.date = d;
}

export function navigate(route, params = {}) {
  const qs = new URLSearchParams(params);
  if (state.date && state.date !== state.dates[0]) qs.set("date", state.date);
  const q = qs.toString();
  location.hash = `#/${route}${q ? "?" + q : ""}`;
}

function setDate(date) {
  state.date = date;
  render();
}

async function render() {
  parseHash();
  // 顶栏高亮与日期控件
  document.querySelectorAll("#nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.route === state.route));
  const idx = state.dates.indexOf(state.date);
  document.getElementById("date-label").textContent = state.date || "—";
  document.getElementById("date-prev").disabled = idx < 0 || idx >= state.dates.length - 1;
  document.getElementById("date-next").disabled = idx <= 0;

  const el = document.getElementById("view");
  el.innerHTML = '<div class="loading">正在加载 …</div>';
  try {
    await VIEWS[state.route].mount(el, state);
  } catch (err) {
    el.innerHTML = `<div class="empty">页面渲染失败：${err.message}</div>`;
    console.error(err);
  }
  window.scrollTo({ top: 0 });
}

function mountTicker() {
  const conf = state.watchlistConf;
  const el = document.getElementById("tickertape");
  if (!conf?.tickers?.length) { el.innerHTML = ""; return; }
  const symbols = conf.tickers
    .filter((t) => t.tv)
    .slice(0, 15)
    .map((t) => ({ proName: t.tv, title: t.name_zh }));
  tv.tickerTape(el, symbols);
}

async function boot() {
  initTheme(() => { mountTicker(); render(); });  // 主题切换 → 重建 widget + 重绘视图

  // 三个独立请求并行发起；App 模式探测成功则亮出设置入口（Pages 保持隐藏）
  [state.app, state.index, state.watchlistConf] = await Promise.all([
    appApi.status(), api.index(), api.watchlistConf(),
  ]);
  if (state.app) {
    document.querySelector('#nav a[data-route="settings"]').hidden = false;
  }
  state.dates = (state.index?.dates || []).map((d) => d.date);
  state.date = state.index?.latest_date || state.dates[0] || null;

  document.getElementById("date-prev").addEventListener("click", () => {
    const i = state.dates.indexOf(state.date);
    if (i < state.dates.length - 1) setDate(state.dates[i + 1]);
  });
  document.getElementById("date-next").addEventListener("click", () => {
    const i = state.dates.indexOf(state.date);
    if (i > 0) setDate(state.dates[i - 1]);
  });
  window.addEventListener("hashchange", render);

  mountTicker();
  if (!state.date) {
    if (state.app) {
      // App 首启无数据：直接带用户去设置页配置 Key 并手动跑第一班
      location.hash = "#/settings";
      render();
      return;
    }
    document.getElementById("view").innerHTML =
      '<div class="empty">暂无数据 —— 等待第一次管线运行完成后刷新本页</div>';
    return;
  }
  render();
}

boot();
