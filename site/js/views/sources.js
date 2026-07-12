// 源状态视图：当日各源抓取结果 + 周度健康巡检
import { api } from "../api.js";
import { esc, fmtTime } from "../format.js";

const STATUS_NAME = { ok: "正常", empty: "空返回", error: "失败",
                      skipped: "跳过", disabled: "已禁用" };

export async function mount(el, state) {
  const [doc, health] = await Promise.all([
    api.sourcesStatus(state.date), api.health(),
  ]);
  const runs = doc?.runs || {};
  const edition = runs.evening ? "evening" : "morning";
  const run = runs[edition];
  if (!run) {
    el.innerHTML = `<div class="empty">${esc(state.date)} 暂无源状态数据</div>`;
    return;
  }
  const rows = run.sources || [];
  const counts = rows.reduce((acc, r) => { acc[r.status] = (acc[r.status] || 0) + 1; return acc; }, {});

  el.innerHTML = `
    <h1 class="view-title">信息源状态</h1>
    <p class="view-sub">${esc(state.date)} ${edition === "morning" ? "早报" : "晚报"}班次
      · ${Object.entries(counts).map(([k, v]) => `${STATUS_NAME[k] || k} ${v}`).join(" · ")}
      ${health ? `· 上次全量巡检 ${fmtTime(health.run_at)}` : ""}</p>
    <div class="card" style="padding:6px 16px">
      <div class="table-wrap"><table class="data-table">
        <thead><tr><th>源</th><th>状态</th><th>新增</th><th>抓取</th>
          <th>耗时</th><th>连败</th><th>错误</th></tr></thead>
        <tbody>
          ${rows.map((r) => `<tr>
            <td><span class="status-dot status-${esc(r.status)}"></span>${esc(r.id)}</td>
            <td>${STATUS_NAME[r.status] || esc(r.status)}${r.http_status ? ` (${r.http_status})` : ""}</td>
            <td>${r.items_new ?? "—"}</td>
            <td>${r.items_fetched ?? "—"}</td>
            <td>${r.latency_ms != null ? r.latency_ms + "ms" : "—"}</td>
            <td>${r.consecutive_failures || ""}</td>
            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                title="${esc(r.error || "")}">${esc(r.error || "")}</td>
          </tr>`).join("")}
        </tbody>
      </table></div>
    </div>`;
}
