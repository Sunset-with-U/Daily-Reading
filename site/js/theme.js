// 明暗主题：localStorage 记忆 + 跟随系统；切换时广播事件（TradingView 需重建）
const KEY = "dr-theme";

export function currentTheme() {
  return document.documentElement.dataset.theme || "light";
}

export function initTheme(onChange) {
  const btn = document.getElementById("theme-toggle");
  const icon = (theme) => (theme === "dark" ? "☀" : "☾");  // 显示"切过去"的目标
  const apply = (theme) => {
    document.documentElement.dataset.theme = theme;
    btn.textContent = icon(theme);
    btn.title = theme === "dark" ? "切换到白天模式" : "切换到黑夜模式";
    onChange?.(theme);
  };
  btn.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    localStorage.setItem(KEY, next);
    apply(next);
  });
  // 未手动设置时跟随系统变化
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem(KEY)) apply(e.matches ? "dark" : "light");
  });
  btn.textContent = icon(currentTheme());
  btn.title = currentTheme() === "dark" ? "切换到白天模式" : "切换到黑夜模式";
}
