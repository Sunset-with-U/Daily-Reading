"""系统通知。macOS 用 osascript（开发态与直发 .app 均可用）；其他平台打印。

Mac App Store 沙盒下 osascript 受限——上架前需切换 UNUserNotificationCenter
（含授权流程），见 docs/PACKAGING.md 的 MAS 清单。
"""
from __future__ import annotations

import subprocess
import sys


def notify(title: str, body: str) -> None:
    if sys.platform != "darwin":
        print(f"[notify] {title}: {body}")
        return
    try:
        script = f'display notification "{_esc(body)}" with title "{_esc(title)}"'
        subprocess.run(["osascript", "-e", script], check=False, timeout=10,
                       capture_output=True)
    except Exception:  # noqa: BLE001 — 通知失败不影响主流程
        pass


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
