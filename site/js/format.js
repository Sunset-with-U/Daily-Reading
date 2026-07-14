// 展示格式化工具
export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function md(text) {
  if (!text) return "";
  try {
    // marked（UMD 全局）：GFM 表格支持；输出包一层滚动容器由调用方决定
    return window.marked.parse(String(text), { gfm: true, breaks: false });
  } catch {
    return `<p>${esc(text)}</p>`;
  }
}

export function fmtTime(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toLocaleString("zh-CN", {
      timeZone: "Asia/Shanghai", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }) + " 北京";
  } catch { return ""; }
}

export function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  return Math.abs(n) >= 10000
    ? n.toLocaleString("zh-CN", { maximumFractionDigits: 0 })
    : n.toLocaleString("zh-CN", { maximumFractionDigits: digits });
}

export function deltaHtml(pct) {
  if (pct === null || pct === undefined || Number.isNaN(Number(pct))) return "";
  const n = Number(pct);
  const cls = n > 0 ? "up" : n < 0 ? "down" : "";
  const sign = n > 0 ? "+" : "";
  return `<span class="tile-delta ${cls}">${sign}${n.toFixed(2)}%</span>`;
}

export const IMP_ORDER = { S: 0, A: 1, B: 2, C: 3 };

export function impBadge(imp) {
  return imp ? `<span class="badge imp-${esc(imp)}">${esc(imp)}</span>` : "";
}
