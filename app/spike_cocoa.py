"""Cocoa 共存性 spike（仅 macOS 真机手动运行，验证后可删）：

    python -m app.spike_cocoa

验证三件事共存：pywebview 窗口 + NSStatusItem 菜单栏 + 后台线程。
预期：出现一个窗口和菜单栏 "DR✓" 图标，图标标题每秒递增计数，
菜单里"退出"可正常退出。任何一步失败即说明 Cocoa 主线程模型被破坏。
"""
from __future__ import annotations

import itertools
import threading
import time

_refs = {}  # 强引用防 GC


def _install_status_item():
    from AppKit import NSStatusBar, NSVariableStatusItemLength

    item = NSStatusBar.systemStatusBar().statusItemWithLength_(
        NSVariableStatusItemLength)
    item.button().setTitle_("DR✓")
    _refs["item"] = item


def main() -> None:
    import webview
    from PyObjCTools import AppHelper

    window = webview.create_window(
        "Spike", html="<h1>Cocoa spike：窗口 + 菜单栏 + 后台线程</h1>",
        width=480, height=200)

    def on_ready():
        AppHelper.callAfter(_install_status_item)

        def counter():
            for i in itertools.count(1):
                time.sleep(1)
                title = f"DR {i}"
                AppHelper.callAfter(
                    lambda t=title: _refs["item"].button().setTitle_(t))

        threading.Thread(target=counter, daemon=True).start()

    webview.start(on_ready)


if __name__ == "__main__":
    main()
