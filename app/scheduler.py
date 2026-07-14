"""本地定时：早晚两班自动运行（默认北京 07:00 / 20:00，面板可自定义）+ 错过补跑 + 手动触发。

核心判定 due_edition() 是纯函数（Linux 可全测）；循环线程只做编排。
补跑策略：只补"最近一个已到点"的班次——App 晚上才打开时直接跑晚报，
不再重复花一遍早报的 AI 成本（抓取本身是增量的，当日数据不缺）。
"""
from __future__ import annotations

import threading
import traceback
from datetime import datetime, timedelta

from pipeline import datectx
from pipeline.datectx import BEIJING
from pipeline.util import STATE_DIR, load_json, save_json

EDITION_TIMES = {"morning": 7, "evening": 20}  # 出厂默认（北京整点）
_STATE_FILE = STATE_DIR / "schedule_state.json"


def schedule_times(settings: dict) -> dict[str, int]:
    """settings.schedule.{morning,evening}_hour → 班次时间表（面板可自定义）。

    非法值（非整数/越界）逐项回退出厂默认——可写配置不得让定时器停摆。
    """
    sc = settings.get("schedule") or {}
    times = {}
    for edition, default in EDITION_TIMES.items():
        try:
            hour = int(sc.get(f"{edition}_hour", default))
            times[edition] = hour if 0 <= hour <= 23 else default
        except (TypeError, ValueError):
            times[edition] = default
    return times


def due_edition(now_bj: datetime, last_runs: dict[str, str],
                times: dict[str, int] | None = None) -> str | None:
    """返回当前应跑的班次（无则 None）。

    last_runs: {"morning": "YYYY-MM-DD", ...}——各班次最近一次运行的北京日期。
    times: 班次时间表（缺省出厂）。只考虑今天已到点的班次中最晚的一个；
    今天已跑过即不再跑（跨日不补昨）。
    """
    times = times or EDITION_TIMES
    today = now_bj.strftime("%Y-%m-%d")
    arrived = [e for e, h in times.items() if now_bj.hour >= h]
    if not arrived:
        return None
    latest = max(arrived, key=lambda e: times[e])
    return latest if last_runs.get(latest) != today else None


def next_run_at(now_bj: datetime, times: dict[str, int] | None = None) -> str:
    """下一个自动班次的北京时间（面板展示用）。"""
    times = times or EDITION_TIMES
    for hour in sorted(times.values()):
        if now_bj.hour < hour:
            return now_bj.replace(hour=hour, minute=0, second=0).strftime("%m-%d %H:%M 北京时间")
    nxt = (now_bj + timedelta(days=1)).replace(
        hour=min(times.values()), minute=0, second=0)
    return nxt.strftime("%m-%d %H:%M 北京时间")


class Scheduler:
    """循环线程：30s 一 tick；手动触发（server 的 Event）优先；Lock 串行管线。"""

    def __init__(self, app_state, notify_fn=None, tick_s: int = 30):
        self.app_state = app_state          # server.AppState（复用 run_requested/run_edition）
        self.notify = notify_fn or (lambda title, body: None)
        self.tick_s = tick_s
        self.lock = threading.Lock()
        self.running_edition: str | None = None
        self.last_result = ""
        self._stop = threading.Event()

    def status(self) -> dict:
        return {
            "next_run": next_run_at(datetime.now(BEIJING), self._times()),
            "running": self.running_edition,
            "last_result": self.last_result,
        }

    @staticmethod
    def _times() -> dict[str, int]:
        """当前生效的班次时间表：每次读盘 → 面板改完下一 tick 即生效，无需重启。"""
        from pipeline.cli import load_settings

        return schedule_times(load_settings())

    def loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:  # noqa: BLE001 — 调度线程永不退出
                traceback.print_exc()
            self.app_state.run_requested.wait(self.tick_s)

    def stop(self) -> None:
        self._stop.set()
        self.app_state.run_requested.set()  # 解除等待

    def _tick(self) -> None:
        if self.app_state.run_requested.is_set():
            self.app_state.run_requested.clear()
            edition = self.app_state.run_edition
            self.app_state.run_edition = None
            self._run(edition)
            return
        last_runs = load_json(_STATE_FILE, {}) or {}
        edition = due_edition(datetime.now(BEIJING), last_runs, self._times())
        if edition:
            self._run(edition)

    def _run(self, edition: str | None) -> None:
        if not self.lock.acquire(blocking=False):
            return  # 已有一次运行在进行
        self.running_edition = edition or "auto"
        try:
            from pipeline.cli import main as cli_main

            cli_main(["collect-pending"])
            args = ["run"]
            if edition:
                args += ["--edition", edition]
            cli_main(args)
            # 归班规则/北京日期复用 datectx（与管线同一权威）
            dctx = datectx.build()
            effective = edition or dctx.edition
            # 手动与自动一律记账：面板跑过早报后，定时器不再重复跑同一班次
            last_runs = load_json(_STATE_FILE, {}) or {}
            last_runs[effective] = dctx.date_bj
            save_json(_STATE_FILE, last_runs)
            label = "早报" if effective == "morning" else "晚报"
            self.last_result = f"{datetime.now(BEIJING).strftime('%H:%M')} {label}完成"
            self.notify("Daily Reading", f"{label}已更新，点击查看")
        except Exception as exc:  # noqa: BLE001 — 失败也要通知
            self.last_result = f"运行失败：{type(exc).__name__}"
            self.notify("Daily Reading", f"本次运行失败（{type(exc).__name__}），详见日志")
            traceback.print_exc()
        finally:
            self.running_edition = None
            self.lock.release()
