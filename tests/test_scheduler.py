"""调度判定纯函数：正点/错过补跑最近班次/已跑不重复/跨日不补昨。"""
from datetime import datetime

from app.scheduler import BEIJING, due_edition, next_run_at


def _bj(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, day, hour, minute, tzinfo=BEIJING)


def test_before_first_edition_nothing_due():
    assert due_edition(_bj(13, 6, 59), {}) is None


def test_morning_due_at_seven():
    assert due_edition(_bj(13, 7), {}) == "morning"
    assert due_edition(_bj(13, 8, 30), {}) == "morning"


def test_morning_already_ran_today():
    assert due_edition(_bj(13, 8), {"morning": "2026-07-13"}) is None


def test_missed_morning_late_open_runs_evening_only():
    # 21:00 才开 App、全天没跑过 → 只补最近的晚报，不重复花早报的 AI 成本
    assert due_edition(_bj(13, 21), {}) == "evening"
    assert due_edition(_bj(13, 21), {"morning": "2026-07-13"}) == "evening"


def test_evening_already_ran():
    assert due_edition(_bj(13, 21), {"evening": "2026-07-13"}) is None


def test_yesterday_runs_do_not_count():
    # 昨天跑过 ≠ 今天跑过；但也不会去"补昨天"
    assert due_edition(_bj(13, 7, 5), {"morning": "2026-07-12"}) == "morning"
    assert due_edition(_bj(13, 6), {"morning": "2026-07-12",
                                    "evening": "2026-07-12"}) is None


def test_between_editions_evening_not_due_yet():
    assert due_edition(_bj(13, 19, 59), {"morning": "2026-07-13"}) is None


def test_next_run_at_labels():
    assert "07:00" in next_run_at(_bj(13, 3))
    assert "20:00" in next_run_at(_bj(13, 12))
    assert "07:00" in next_run_at(_bj(13, 22))  # 次日早班
