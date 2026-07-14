// 数据加载与缓存：data/index.json 是唯一入口，按日期懒加载
const cache = new Map();

async function getJSON(path) {
  if (cache.has(path)) return cache.get(path);
  try {
    const resp = await fetch(path, { cache: "no-cache" });
    if (!resp.ok) { cache.set(path, null); return null; }
    const data = await resp.json();
    cache.set(path, data);
    return data;
  } catch {
    cache.set(path, null);
    return null;
  }
}

export const api = {
  index: () => getJSON("data/index.json"),
  items: (date) => getJSON(`data/${date}/items.json`),
  report: (date) => getJSON(`data/${date}/report.json`),
  market: (date) => getJSON(`data/${date}/market.json`),
  sourcesStatus: (date) => getJSON(`data/${date}/sources_status.json`),
  health: () => getJSON("data/health/latest.json"),
  watchlistConf: () => getJSON("data/watchlist.json"),
};

// —— App 模式写通道（本地 loopback 服务）——
// Pages 静态托管下 /api 不存在：status() 返回 null，设置入口保持隐藏。
// token 来自窗口 URL ?t=（App 启动时注入），写接口凭它校验。
const appToken = new URLSearchParams(location.search).get("t") || "";

async function apiFetch(method, path, body) {
  const resp = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", "X-DR-Token": appToken },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await resp.json().catch(() => null);
  if (!resp.ok) throw new Error(data?.error || `HTTP ${resp.status}`);
  return data;
}

export const appApi = {
  status: async () => {
    try {
      const resp = await fetch("api/status", { cache: "no-cache" });
      return resp.ok ? await resp.json() : null;
    } catch { return null; }
  },
  settings: () => apiFetch("GET", "api/settings"),
  saveSettings: (patch) => apiFetch("PUT", "api/settings", patch),
  saveKey: (name, value) => apiFetch("PUT", "api/keys", { name, value }),
  deleteKey: (name) => apiFetch("DELETE", "api/keys", { name }),
  sources: () => apiFetch("GET", "api/sources"),
  saveSources: (overlay) => apiFetch("PUT", "api/sources", overlay),
  run: (edition) => apiFetch("POST", "api/run", edition ? { edition } : {}),
};
