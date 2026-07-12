// 市场快照视图：统计卡片（自有数据）+ TradingView 组件（实时）
import { api } from "../api.js";
import { deltaHtml, esc, fmtNum } from "../format.js";
import { tv } from "../widgets.js";

export async function mount(el, state) {
  const m = await api.market(state.date);
  const parts = [`<h1 class="view-title">市场快照</h1>
    <p class="view-sub">${esc(state.date)} · 管线数据于 ${esc(m?.run_at || "—")} 采集
      · 下方图表为 TradingView 实时数据</p>`];

  if (m?.quotes?.length) {
    parts.push(section("跨资产报价", `<div class="tile-grid">${m.quotes.map((q) => `
      <div class="card tile">
        <div class="tile-label">${esc(q.name_zh)}</div>
        <div class="tile-value">${fmtNum(q.price)}</div>
        ${deltaHtml(q.chg_pct)}
        <div class="tile-sub">${esc(q.source)}</div>
      </div>`).join("")}</div>`));
  }

  if (m?.rates) {
    parts.push(section("利率与流动性（FRED）", `<div class="tile-grid">${
      Object.entries(m.rates).map(([k, v]) => `
      <div class="card tile">
        <div class="tile-label">${esc(v.name_zh || k)}</div>
        <div class="tile-value">${fmtNum(v.value)}</div>
        ${v.prev != null ? deltaOf(v.value, v.prev) : ""}
        <div class="tile-sub">${esc(v.date || "")}</div>
      </div>`).join("")}</div>`));
  }

  if (m?.vol && Object.keys(m.vol).length) {
    const ts = m.vol.term_structure;
    parts.push(section("波动率结构", `<div class="tile-grid">
      ${tile("VIX", m.vol.vix)}${tile("VIX9D", m.vol.vix9d)}
      ${tile("VIX3M", m.vol.vix3m)}${tile("VVIX", m.vol.vvix)}
      ${tile("BTC DVOL", m.vol.dvol_btc)}${tile("ETH DVOL", m.vol.dvol_eth)}
      ${ts ? `<div class="card tile"><div class="tile-label">期限结构</div>
        <div class="tile-value" style="font-size:1rem">${ts.inverted ? "⚠ 近端倒挂" : "正常 Contango"}</div>
        <div class="tile-sub">9D/VIX ${ts.vix9d_vix} · VIX/3M ${ts.vix_vix3m}</div></div>` : ""}
    </div>`));
  }

  if (m?.sentiment && Object.keys(m.sentiment).length) {
    parts.push(section("情绪面", `<div class="tile-grid">
      ${meterTile("CNN 恐贪（美股）", m.sentiment.cnn_fg)}
      ${meterTile("加密恐贪", m.sentiment.crypto_fg)}
      ${m.sentiment.aaii ? `<div class="card tile"><div class="tile-label">AAII 散户调查</div>
        <div class="tile-value" style="font-size:1rem">多 ${m.sentiment.aaii.bullish}%</div>
        <div class="tile-sub">中性 ${m.sentiment.aaii.neutral}% · 空 ${m.sentiment.aaii.bearish}%</div></div>` : ""}
    </div>`));
  }

  if (m?.positioning && Object.keys(m.positioning).length) {
    const NAME = { gold: "黄金", silver: "白银", euro_fx: "欧元", jpy: "日元", es: "标普E-mini" };
    parts.push(section("CFTC 投机净持仓（COT 周报）", `<div class="card" style="padding:6px 16px">
      <div class="table-wrap"><table class="data-table">
        <thead><tr><th>市场</th><th>净持仓</th><th>周变化</th><th>报告日</th></tr></thead>
        <tbody>${Object.entries(m.positioning).map(([k, v]) => `
          <tr><td>${NAME[k] || k}</td><td>${fmtNum(v.noncomm_net, 0)}</td>
          <td>${v.wow_change != null ? (v.wow_change > 0 ? "+" : "") + fmtNum(v.wow_change, 0) : "—"}</td>
          <td>${esc(v.report_date)}</td></tr>`).join("")}</tbody>
      </table></div></div>`));
  }

  if (m?.gold && Object.keys(m.gold).length) {
    const g = m.gold;
    parts.push(section("黄金专题", `<div class="tile-grid">
      ${g.lbma_gold_pm ? tile("LBMA 金(PM)", g.lbma_gold_pm.usd, "$/oz " + g.lbma_gold_pm.date) : ""}
      ${g.lbma_silver ? tile("LBMA 银", g.lbma_silver.usd, "$/oz") : ""}
      ${g.sge ? tile("沪伦溢价", g.sge.premium_usd, `SGE ${g.sge.benchmark_cny_g} 元/克`) : ""}
      ${g.comex_gold ? tile("COMEX 注册库存", Math.round(g.comex_gold.registered_oz / 1000) + "k oz",
                            `合格 ${Math.round(g.comex_gold.eligible_oz / 1000)}k oz`) : ""}
    </div>`));
  }

  if (m?.crypto?.funding && Object.keys(m.crypto.funding).length) {
    parts.push(section("加密衍生品（OKX/Deribit）", `<div class="tile-grid">
      ${tile("BTC 资金费率", m.crypto.funding.btc + "%", "OKX 8h")}
      ${tile("ETH 资金费率", m.crypto.funding.eth + "%", "OKX 8h")}
      ${m.etf_flows ? tile("BTC ETF 净流", "$" + fmtNum(m.etf_flows.btc_etf_total_usd_m, 0) + "M",
                           m.etf_flows.date) : ""}
    </div>`));
  }

  if (m?.fed_path?.length) {
    parts.push(section("联邦基金期货隐含利率", `<div class="tile-grid">
      ${m.fed_path.map((p) => tile(p.month, p.implied_rate + "%", "ZQ 期货隐含")).join("")}
    </div>`));
  }

  if (m?.calendar?.length) {
    parts.push(section("未来财经日历（高/中影响）", `<div class="card" style="padding:6px 16px">
      <div class="table-wrap"><table class="data-table">
        <thead><tr><th>北京时间</th><th>地区</th><th>事件</th><th>预期</th><th>前值</th></tr></thead>
        <tbody>${m.calendar.slice(0, 25).map((c) => `
          <tr><td>${esc(c.date_bj)} ${esc(c.time_bj)}</td>
          <td><i class="impact-dot impact-${esc(c.impact)}"></i>${esc(c.country)}</td>
          <td>${esc(c.title)}</td><td>${esc(c.forecast || "—")}</td>
          <td>${esc(c.previous || "—")}</td></tr>`).join("")}</tbody>
      </table></div></div>`));
  }

  // TradingView 实时区
  parts.push(section("实时图表（TradingView）",
    `<div id="tv-chart" class="tv-widget"></div>
     <div id="tv-heatmap" class="tv-widget short"></div>
     <div id="tv-cal" class="tv-widget short"></div>`,
    "实时数据 · 可交互"));

  el.innerHTML = parts.join("");
  tv.advancedChart(el.querySelector("#tv-chart"), "SP:SPX");
  tv.heatmap(el.querySelector("#tv-heatmap"));
  tv.econCalendar(el.querySelector("#tv-cal"));
}

const section = (title, body, note = "") =>
  `<h2 class="section-h">${title}${note ? `<span class="note">${note}</span>` : ""}</h2>${body}`;

const tile = (label, value, sub = "") => value == null ? "" :
  `<div class="card tile"><div class="tile-label">${esc(label)}</div>
   <div class="tile-value">${typeof value === "number" ? fmtNum(value) : esc(String(value))}</div>
   ${sub ? `<div class="tile-sub">${esc(sub)}</div>` : ""}</div>`;

function meterTile(label, fg) {
  if (!fg) return "";
  return `<div class="card tile">
    <div class="tile-label">${esc(label)}</div>
    <div class="tile-value">${fmtNum(fg.value, 0)} <span style="font-size:.8rem;color:var(--muted)">${esc(fg.label || "")}</span></div>
    <div class="meter"><i style="width:${Math.min(100, Math.max(0, fg.value))}%"></i></div>
  </div>`;
}

function deltaOf(cur, prev) {
  if (prev == null || cur == null || !prev) return "";
  const diff = cur - prev;
  const cls = diff > 0 ? "up" : diff < 0 ? "down" : "";
  return `<span class="tile-delta ${cls}">${diff > 0 ? "+" : ""}${diff.toFixed(2)}</span>`;
}
