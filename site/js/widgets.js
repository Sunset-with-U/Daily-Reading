// TradingView 免费嵌入组件工厂
// 注意：widget 不支持热切换主题 → 主题变化时由视图销毁并重建容器
import { currentTheme } from "./theme.js";

function inject(container, scriptSrc, config) {
  container.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "tradingview-widget-container";
  const slot = document.createElement("div");
  slot.className = "tradingview-widget-container__widget";
  wrap.appendChild(slot);
  const script = document.createElement("script");
  script.type = "text/javascript";
  script.src = scriptSrc;
  script.async = true;
  script.text = JSON.stringify(config);
  wrap.appendChild(script);
  container.appendChild(wrap);
}

const BASE = "https://s3.tradingview.com/external-embedding";

export const tv = {
  tickerTape(container, symbols) {
    inject(container, `${BASE}/embed-widget-ticker-tape.js`, {
      symbols, showSymbolLogo: false, isTransparent: true, displayMode: "adaptive",
      colorTheme: currentTheme(), locale: "zh_CN",
    });
  },
  advancedChart(container, symbol) {
    inject(container, `${BASE}/embed-widget-advanced-chart.js`, {
      autosize: true, symbol, interval: "D", timezone: "Asia/Shanghai",
      theme: currentTheme(), style: "1", locale: "zh_CN",
      allow_symbol_change: true, calendar: false, support_host: "https://www.tradingview.com",
    });
  },
  heatmap(container) {
    inject(container, `${BASE}/embed-widget-stock-heatmap.js`, {
      exchanges: [], dataSource: "SPX500", grouping: "sector",
      blockSize: "market_cap_basic", blockColor: "change", hasTopBar: false,
      isZoomEnabled: true, hasSymbolTooltip: true, isMonoSize: false,
      width: "100%", height: "100%", colorTheme: currentTheme(), locale: "zh_CN",
    });
  },
  econCalendar(container) {
    inject(container, `${BASE}/embed-widget-events.js`, {
      colorTheme: currentTheme(), isTransparent: true, width: "100%", height: "100%",
      locale: "zh_CN", importanceFilter: "0,1", countryFilter: "us,cn,eu,jp,gb",
    });
  },
  miniSymbol(container, symbol) {
    inject(container, `${BASE}/embed-widget-symbol-overview.js`, {
      symbols: [[symbol]], chartOnly: false, width: "100%", height: "100%",
      colorTheme: currentTheme(), locale: "zh_CN", autosize: true,
      showVolume: false, hideDateRanges: false, scalePosition: "right",
      scaleMode: "Normal", chartType: "area", dateRanges: ["1d|15", "1m|60", "3m|1D", "12m|1D"],
    });
  },
};
