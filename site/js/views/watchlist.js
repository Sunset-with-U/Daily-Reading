// 关注清单视图：最新报告的 watchlist + TradingView mini 图
import { api } from "../api.js";
import { esc, md } from "../format.js";
import { tv } from "../widgets.js";

export async function mount(el, state) {
  const [doc, conf] = await Promise.all([api.report(state.date), api.watchlistConf()]);
  const editions = doc?.editions || {};
  const edition = editions.evening ? "evening" : editions.morning ? "morning" : null;
  const list = edition ? (editions[edition].watchlist || []) : [];
  if (!list.length) {
    el.innerHTML = `<div class="empty">${esc(state.date)} 暂无关注清单（随每日报告生成）</div>`;
    return;
  }
  // 报告 symbol → TradingView 符号：优先 watchlist.yaml 映射，其次直接用 symbol
  const tvMap = new Map();
  for (const t of conf?.tickers || []) {
    if (t.tv) {
      tvMap.set(String(t.id).toUpperCase(), t.tv);
      tvMap.set(String(t.name_zh), t.tv);
      tvMap.set(t.tv.split(":").pop().toUpperCase(), t.tv);
    }
  }
  el.innerHTML = `
    <h1 class="view-title">今日重点关注</h1>
    <p class="view-sub">${esc(state.date)} · ${edition === "morning" ? "早报" : "晚报"}给出
      ${list.length} 个标的 · 点击卡片图表可交互</p>
    <div class="watch-grid">${list.map((w, i) => card(w, i)).join("")}</div>`;

  list.forEach((w, i) => {
    const slot = el.querySelector(`#tv-mini-${i}`);
    if (!slot) return;
    const sym = tvMap.get(String(w.symbol).toUpperCase()) || guessTv(w);
    if (sym) tv.miniSymbol(slot, sym);
    else slot.remove();
  });
}

function card(w, i) {
  return `<div class="card watch-card">
    <div class="watch-head">
      <span class="watch-symbol">${esc(w.symbol)}</span>
      <span class="watch-name">${esc(w.name_zh)}</span>
      <span class="badge dir dir-${esc(w.direction)} watch-type">${esc(w.direction)}</span>
      <span class="chip">${esc(w.type)}</span>
    </div>
    <div id="tv-mini-${i}" class="tv-mini"></div>
    <div class="md">${md(w.view_md)}</div>
    ${w.key_levels ? `<div class="watch-levels"><b>关键位</b> ${esc(w.key_levels)}</div>` : ""}
  </div>`;
}

function guessTv(w) {
  const s = String(w.symbol).trim().toUpperCase();
  if (!s) return null;
  if (s.includes(":")) return s;                 // 已是 TV 格式
  if (w.type === "加密") return `COINBASE:${s.replace(/[-/]/g, "")}${s.endsWith("USD") ? "" : "USD"}`;
  if (w.type === "外汇" && /^[A-Z]{6}$/.test(s)) return `FX:${s}`;
  if (/^[A-Z.]{1,6}$/.test(s)) return s;         // 美股代码交给 TV 自动解析
  return null;
}
