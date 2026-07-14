"""macOS 菜单栏常驻图标（NSStatusItem，经 pyobjc 注入 pywebview 的 NSApp）。

必须在 Cocoa 主线程调用 install()——从 webview.start(func=...) 的工作线程
经 AppHelper.callAfter 调度过来。测试与 Linux CI 不 import 本模块。
"""
from __future__ import annotations

# 模块级强引用：NSStatusItem/delegate 被 GC 后图标会直接消失（pyobjc 常见坑）
_status_item = None
_delegate = None


def install(window, scheduler, app_state) -> None:
    from AppKit import (NSMenu, NSMenuItem, NSStatusBar,
                        NSVariableStatusItemLength)
    from Foundation import NSObject

    class _MenuActions(NSObject):
        def showWindow_(self, sender):  # noqa: N802
            window.show()

        def runMorning_(self, sender):  # noqa: N802
            app_state.run_edition = "morning"
            app_state.run_requested.set()

        def runEvening_(self, sender):  # noqa: N802
            app_state.run_edition = "evening"
            app_state.run_requested.set()

        def quitApp_(self, sender):  # noqa: N802
            scheduler.stop()
            window.destroy()

    global _status_item, _delegate
    _delegate = _MenuActions.alloc().init()
    _status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
        NSVariableStatusItemLength)
    _status_item.button().setTitle_("DR")

    menu = NSMenu.alloc().init()
    for title, action in (("打开看板", "showWindow:"),
                          ("立即运行早报", "runMorning:"),
                          ("立即运行晚报", "runEvening:")):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
        item.setTarget_(_delegate)
        menu.addItem_(item)
    menu.addItem_(NSMenuItem.separatorItem())
    quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "退出 Daily Reading", "quitApp:", "q")
    quit_item.setTarget_(_delegate)
    menu.addItem_(quit_item)
    _status_item.setMenu_(menu)
