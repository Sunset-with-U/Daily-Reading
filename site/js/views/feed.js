// 信息流视图：多维筛选 + 搜索（筛选状态写入 hash，可分享）
import { api } from "../api.js";
import { IMP_ORDER, esc, fmtTime, impBadge } from "../format.js";

const MARKETS = ["宏观", "美股", "A股港股", "债券利率", "外汇", "大宗商品",
                 "贵金属", "加密货币", "科技AI", "地缘政治", "中国政策", "其他"];
const IMPS = ["S", "A", "B", "C"];
const TYPES = ["新闻", "评论", "研究", "数据", "播客", "政策文件"];
const PAGE = 100;

export async function mount(el, state) {
  const doc = await api.items(state.date);
  const items = (doc?.items || []).slice();
  if (!items.length) {
    el.innerHTML = `<div class="empty">${esc(state.date)} 暂无条目</div>`;
    return;
  }
  // 排序：重要性 → 发布时间倒序
  items.sort((a, b) => {
    const ia = IMP_ORDER[a.analysis?.importance] ?? 9;
    const ib = IMP_ORDER[b.analysis?.importance] ?? 9;
    if (ia !== ib) return ia - ib;
    return (b.published_at || "").localeCompare(a.published_at || "");
  });

  const f = {
    mkt: (state.params.get("mkt") || "").split(",").filter(Boolean),
    imp: (state.params.get("imp") || "").split(",").filter(Boolean),
    typ: (state.params.get("typ") || "").split(",").filter(Boolean),
    q: state.params.get("q") || "",
    limit: PAGE,
  };

  el.innerHTML = `
    <h1 class="view-title">信息流</h1>
    <p class="view-sub">${esc(state.date)} · 共 ${items.length} 条 · AI 已分析
      ${items.filter((i) => i.analysis?.status === "done").length} 条</p>
    <div class="card filterbar">
      <input class="search" type="search" placeholder="搜索标题 / 摘要 / 标签…" value="${esc(f.q)}">
      <div class="fgroup"><span class="fgroup-label">重要性</span>
        ${IMPS.map((v) => chip("imp", v, f.imp)).join("")}</div>
      <div class="fgroup"><span class="fgroup-label">市场</span>
        ${MARKETS.map((v) => chip("mkt", v, f.mkt)).join("")}</div>
      <div class="fgroup"><span class="fgroup-label">类型</span>
        ${TYPES.map((v) => chip("typ", v, f.typ)).join("")}</div>
    </div>
    <div class="feed-count"></div>
    <div id="feed-list"></div>`;

  const apply = () => {
    const filtered = items.filter((it) => {
      const a = it.analysis || {};
      if (f.imp.length && !f.imp.includes(a.importance)) return false;
      if (f.mkt.length && !(a.markets || []).some((m) => f.mkt.includes(m))) return false;
      if (f.typ.length && !f.typ.includes(a.content_type)) return false;
      if (f.q) {
        const hay = `${it.title} ${a.summary_zh || ""} ${(a.tags || []).join(" ")} ${it.source_name_zh || ""}`.toLowerCase();
        if (!hay.includes(f.q.toLowerCase())) return false;
      }
      return true;
    });
    el.querySelector(".feed-count").textContent =
      `筛选出 ${filtered.length} 条${filtered.length > f.limit ? `，显示前 ${f.limit} 条` : ""}`;
    const list = el.querySelector("#feed-list");
    list.innerHTML = filtered.slice(0, f.limit).map(itemCard).join("") +
      (filtered.length > f.limit ? `<button class="load-more">加载更多</button>` : "");
    list.querySelector(".load-more")?.addEventListener("click", () => { f.limit += PAGE; apply(); });
    list.querySelectorAll(".item-deep-toggle").forEach((btn) =>
      btn.addEventListener("click", () => {
        const deep = btn.nextElementSibling;
        deep.hidden = !deep.hidden;
        btn.textContent = deep.hidden ? "▸ 展开 AI 深度分析" : "▾ 收起 AI 深度分析";
      }));
    syncHash();
  };

  const syncHash = () => {
    const qs = new URLSearchParams();
    if (f.mkt.length) qs.set("mkt", f.mkt.join(","));
    if (f.imp.length) qs.set("imp", f.imp.join(","));
    if (f.typ.length) qs.set("typ", f.typ.join(","));
    if (f.q) qs.set("q", f.q);
    if (state.date !== state.dates[0]) qs.set("date", state.date);
    const q = qs.toString();
    history.replaceState(null, "", `#/feed${q ? "?" + q : ""}`);
  };

  el.querySelectorAll(".fchip").forEach((c) =>
    c.addEventListener("click", () => {
      const set = f[c.dataset.g];
      const i = set.indexOf(c.dataset.v);
      i >= 0 ? set.splice(i, 1) : set.push(c.dataset.v);
      c.classList.toggle("on");
      f.limit = PAGE;
      apply();
    }));
  let timer;
  el.querySelector(".search").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { f.q = e.target.value.trim(); f.limit = PAGE; apply(); }, 200);
  });
  apply();
}

function chip(group, value, active) {
  return `<button class="fchip ${active.includes(value) ? "on" : ""}"
    data-g="${group}" data-v="${esc(value)}">${esc(value)}</button>`;
}

function itemCard(it) {
  const a = it.analysis || {};
  const deep = a.deep;
  const impl = (deep?.implications || []).map((p) =>
    `<span class="chip">${esc(p.direction)} ${esc((p.assets || []).join("/"))}
      · ${esc(p.timeframe)} · 置信${esc(p.confidence)}</span>`).join("");
  return `<article class="card item-card">
    <div class="item-head">
      ${impBadge(a.importance)}
      <div style="min-width:0">
        <a class="item-title" href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a>
        <div class="item-meta">
          <span>${esc(it.source_name_zh || it.source_id)}</span>
          <span>${fmtTime(it.published_at || it.fetched_at)}</span>
          ${(a.markets || []).map((m) => `<span class="chip">${esc(m)}</span>`).join("")}
          ${a.content_type ? `<span class="chip">${esc(a.content_type)}</span>` : ""}
        </div>
        ${a.summary_zh ? `<p class="item-summary">${esc(a.summary_zh)}</p>` : ""}
        ${deep ? `<div class="item-deep">
            <button class="item-deep-toggle">▸ 展开 AI 深度分析</button>
            <div hidden>
              <p class="item-assess">${esc(deep.assessment_zh || "")}</p>
              <div class="impl-row">${impl}</div>
            </div>
          </div>` : ""}
      </div>
    </div>
  </article>`;
}
