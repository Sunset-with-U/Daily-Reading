// 历史归档视图：日期列表 + 重要性统计，点击跳转当日报告
import { esc, impBadge } from "../format.js";

export async function mount(el, state) {
  const dates = state.index?.dates || [];
  if (!dates.length) {
    el.innerHTML = '<div class="empty">暂无历史数据</div>';
    return;
  }
  el.innerHTML = `
    <h1 class="view-title">历史归档</h1>
    <p class="view-sub">共 ${dates.length} 天数据 · 点击查看当日报告与信息流</p>
    <div class="archive-list">
      ${dates.map((d) => `
        <a class="card archive-row" href="#/report?date=${esc(d.date)}">
          <span class="archive-date">${esc(d.date)}</span>
          <span class="archive-stats">
            ${(d.editions || []).map((e) => `<span class="chip">${e === "morning" ? "早报" : "晚报"}</span>`).join("")}
            <span>${d.items} 条</span>
            ${Object.entries(d.by_importance || {})
              .sort()
              .map(([k, v]) => `${impBadge(k)} ${v}`).join(" ")}
          </span>
        </a>`).join("")}
    </div>`;
  // 点击后由 app.js 的 hashchange + params.date 处理日期切换
}
