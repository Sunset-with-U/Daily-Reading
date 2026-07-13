"""Daily-Reading.app 入口：装配顺序严格为
paths(env 注入) → keys 回填 → loopback 服务 → webview 窗口 →
[主线程] 菜单栏 → scheduler 线程。

Cocoa 约束：pywebview 独占主线程与 NSApp runloop；NSStatusItem 必须经
AppHelper.callAfter 回主线程构建；后台工作全部纯 Python 线程。
"""
from __future__ import annotations

import sys
import threading


def main() -> None:
    # 1) 路径 env 必须先于任何 pipeline import
    from app import keys, paths

    app_paths = paths.init_env()
    keys.backfill_env()

    # 2) loopback 服务
    from app.server import AppState, make_server

    state = AppState(app_paths)
    server = make_server(state, port=0)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # 3) 调度器（线程在窗口就绪后启动）
    from app.notify import notify
    from app.scheduler import Scheduler

    scheduler = Scheduler(state, notify_fn=notify)
    state.scheduler_status = scheduler.status

    # 4) 窗口 + 菜单栏
    import webview

    window = webview.create_window(
        "Daily Reading",
        f"http://127.0.0.1:{port}/?t={state.token}",
        width=1320, height=880, min_size=(900, 620),
    )

    def on_closing():
        window.hide()   # 关窗不退出：常驻菜单栏
        return False

    window.events.closing += on_closing

    def on_ready():
        threading.Thread(target=scheduler.loop, daemon=True).start()
        if sys.platform == "darwin":
            from PyObjCTools import AppHelper

            from app import menubar

            AppHelper.callAfter(menubar.install, window, scheduler, state)

    webview.start(on_ready)


if __name__ == "__main__":
    main()
