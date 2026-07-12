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
