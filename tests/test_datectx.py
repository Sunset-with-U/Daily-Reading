"""北京日期/班次逻辑 —— 关键：UTC 23:00 = 次日北京早报。"""
from datetime import datetime, timezone

from pipeline import datectx


def test_utc_2300_is_next_day_beijing_morning():
    # 2026-07-11 23:00 UTC = 北京 2026-07-12 07:00 → 早报，日期 07-12
    now = datetime(2026, 7, 11, 23, 0, tzinfo=timezone.utc)
    ctx = datectx.build(now)
    assert ctx.date_bj == "2026-07-12"
    assert ctx.edition == "morning"
    assert ctx.yyyymm == "202607"
    assert ctx.dd == "12"


def test_utc_1200_is_same_day_beijing_evening():
    # 2026-07-12 12:00 UTC = 北京 2026-07-12 20:00 → 晚报
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    ctx = datectx.build(now)
    assert ctx.date_bj == "2026-07-12"
    assert ctx.edition == "evening"


def test_edition_override():
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    ctx = datectx.build(now, edition_override="morning")
    assert ctx.edition == "morning"


def test_boundary_beijing_noon():
    # 北京 11:59 → morning；12:00 → evening
    assert datectx.build(datetime(2026, 7, 12, 3, 59, tzinfo=timezone.utc)).edition == "morning"
    assert datectx.build(datetime(2026, 7, 12, 4, 0, tzinfo=timezone.utc)).edition == "evening"
