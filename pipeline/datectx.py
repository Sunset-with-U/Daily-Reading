"""北京日期与班次（早报/晚报）逻辑。

规则：管线的所有"日期"都指北京时间日期。
- cron UTC 23:00 触发时，北京时间已是次日 07:00 → 早报，日期=北京当日
- cron UTC 12:00 触发时，北京时间为 20:00 → 晚报，日期=北京当日
- 手动运行按北京时钟就近归班：12 点前=早报，12 点后=晚报
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

BEIJING = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class DateContext:
    date_bj: str          # YYYY-MM-DD（北京日期）
    edition: str          # morning | evening
    run_at_utc: str       # ISO 8601
    yyyymm: str           # 人民日报等日期模板用
    dd: str


def build(now_utc: datetime | None = None, edition_override: str = "") -> DateContext:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    bj = now.astimezone(BEIJING)
    edition = edition_override or ("morning" if bj.hour < 12 else "evening")
    return DateContext(
        date_bj=bj.strftime("%Y-%m-%d"),
        edition=edition,
        run_at_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        yyyymm=bj.strftime("%Y%m"),
        dd=bj.strftime("%d"),
    )
